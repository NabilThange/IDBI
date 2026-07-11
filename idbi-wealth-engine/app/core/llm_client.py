"""AI/ML API client for OpenAI-compatible chat and tool calling."""

import datetime
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List

from openai import OpenAI

from app.config import AIMLAPI_API_KEY, AIMLAPI_MODEL, MAX_TOKENS, TEMPERATURE


def get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class LLMClient:
    """Wrapper for AIMLAPI's OpenAI-compatible chat API."""

    def __init__(self):
        self.client = OpenAI(api_key=AIMLAPI_API_KEY or "missing", base_url="https://api.aimlapi.com/v1")
        self.model = AIMLAPI_MODEL

    def chat(
        self, messages: List[Dict[str, str]], temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS, **kwargs
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature,
                max_tokens=max_tokens, top_p=1, stream=False, **kwargs
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"Error calling AIMLAPI: {e}")
            raise

    def chat_with_system(
        self, system_prompt: str, user_message: str, temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS
    ) -> str:
        return self.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ], temperature, max_tokens)

    @staticmethod
    def _run_tool(tool_call: Any, tool_registry: Dict[str, Callable]) -> tuple:
        tool_name = tool_call.function.name
        try:
            tool_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            tool_args = {}

        try:
            result = tool_registry[tool_name](**tool_args) if tool_name in tool_registry else {
                "error": f"Tool '{tool_name}' not found in registry"
            }
        except Exception as e:
            result = {"error": f"Tool execution failed: {str(e)}"}
        return tool_call.id, tool_name, tool_args, result

    def chat_with_tools(
        self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
        tool_registry: Dict[str, Callable], temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS, max_iterations: int = 10
    ) -> Dict[str, Any]:
        """Run the tool loop, executing each model-requested batch concurrently."""
        conversation = list(messages)
        tool_calls_made = []

        for iteration in range(1, max_iterations + 1):
            print(f"[{get_timestamp()}] [LLM] Calling AIMLAPI (iteration {iteration})")
            started = time.time()
            response = self.client.chat.completions.create(
                model=self.model, messages=conversation, tools=tools, tool_choice="auto",
                parallel_tool_calls=True, temperature=temperature, max_tokens=max_tokens, stream=False
            )
            assistant = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            print(f"[{get_timestamp()}] [LLM] AIMLAPI completed in {time.time() - started:.3f}s ({finish_reason})")

            conversation.append({
                "role": "assistant", "content": assistant.content or "",
                "tool_calls": [call.model_dump(exclude_none=True) for call in assistant.tool_calls or []],
            })

            if not assistant.tool_calls:
                return {
                    "content": assistant.content or "", "tool_calls_made": tool_calls_made,
                    "iterations": iteration, "finish_reason": finish_reason,
                }

            results = {}
            with ThreadPoolExecutor(max_workers=len(assistant.tool_calls)) as executor:
                futures = [executor.submit(self._run_tool, call, tool_registry) for call in assistant.tool_calls]
                for future in as_completed(futures):
                    tool_call_id, name, arguments, result = future.result()
                    results[tool_call_id] = (name, arguments, result)

            for call in assistant.tool_calls:
                name, arguments, result = results[call.id]
                serializable_result = json.loads(json.dumps(result, default=str))
                tool_calls_made.append({
                    "name": name, "arguments": arguments, "result": serializable_result,
                    "iteration": iteration,
                })
                conversation.append({
                    "role": "tool", "tool_call_id": call.id,
                    "content": json.dumps(serializable_result),
                })

        raise Exception(f"Maximum iterations ({max_iterations}) exceeded in tool calling loop.")

    def get_usage_info(self) -> Dict[str, Any]:
        return {"provider": "AIMLAPI", "model": self.model, "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE}


llm_client = LLMClient()
