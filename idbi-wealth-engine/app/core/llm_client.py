"""
Groq LLM Client Wrapper
Provides a clean interface for interacting with Groq's LLM API.
Supports tool calling for agentic behavior.
"""

import json
import time
import datetime
from typing import List, Dict, Any, Optional, Callable
from groq import Groq

def get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

from app.config import GROQ_API_KEY, GROQ_MODEL, MAX_TOKENS, TEMPERATURE


class LLMClient:
    """Wrapper for Groq LLM API"""
    
    def __init__(self):
        """Initialize Groq client"""
        self.client = Groq()  # Will pick up GROQ_API_KEY from environment
        self.model = GROQ_MODEL
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
        **kwargs
    ) -> str:
        """
        Send a chat completion request to Groq.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If API call fails
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                stream=False,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            raise
    
    def chat_with_system(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS
    ) -> str:
        """
        Convenience method for simple system + user message chat.
        
        Args:
            system_prompt: System instruction
            user_message: User's message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        return self.chat(messages, temperature, max_tokens)
    
    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_registry: Dict[str, Callable],
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Agentic chat with tool calling loop.
        
        The LLM can call tools multiple times until it has enough information
        to provide a final answer.
        
        Args:
            messages: Conversation history (role/content dicts)
            tools: List of tool definitions in Groq format
            tool_registry: Dict mapping tool names to callable functions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            max_iterations: Maximum number of LLM calls (prevent infinite loops)
            
        Returns:
            Dictionary with:
                - content: Final text response
                - tool_calls_made: List of tools that were executed
                - iterations: Number of LLM calls made
                
        Raises:
            Exception: If API call fails or max iterations exceeded
        """
        conversation = list(messages)  # Copy to avoid mutating input
        tool_calls_made = []
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Call LLM with tools
                print(f"[{get_timestamp()}] [LLM] Calling Groq API (Iteration {iteration})")
                llm_start = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=conversation,
                    tools=tools,
                    tool_choice="auto",  # Let model decide when to use tools
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                llm_duration = time.time() - llm_start
                assistant_message = response.choices[0].message
                finish_reason = response.choices[0].finish_reason
                print(f"[{get_timestamp()}] [LLM] Groq API response received in {llm_duration:.3f}s (finish_reason: {finish_reason})")
                
                # Add assistant's response to conversation
                conversation.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls else None
                })
                
                # Check if LLM wants to call tools
                if finish_reason == "tool_calls" and assistant_message.tool_calls:
                    # Execute each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args_str = tool_call.function.arguments
                        tool_call_id = tool_call.id
                        
                        # Parse arguments
                        try:
                            tool_args = json.loads(tool_args_str)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        # Execute tool
                        print(f"[{get_timestamp()}] [TOOL] Requesting tool: \"{tool_name}\" with args: {tool_args}")
                        try:
                            if tool_name not in tool_registry:
                                tool_result = {
                                    "error": f"Tool '{tool_name}' not found in registry"
                                }
                            else:
                                tool_function = tool_registry[tool_name]
                                print(f"[{get_timestamp()}] [TOOL] Executing tool: \"{tool_name}\"")
                                tool_start = time.time()
                                tool_result = tool_function(**tool_args)
                                tool_duration = time.time() - tool_start
                                print(f"[{get_timestamp()}] [TOOL] Tool \"{tool_name}\" completed in {tool_duration:.3f}s")
                            
                            # Record successful call with result
                            # ponytail: convert numpy types to native Python for JSON serialization
                            serializable_result = json.loads(json.dumps(tool_result, default=str))
                            tool_calls_made.append({
                                "name": tool_name,
                                "arguments": tool_args,
                                "result": serializable_result,
                                "iteration": iteration
                            })
                            
                        except Exception as e:
                            tool_result = {
                                "error": f"Tool execution failed: {str(e)}"
                            }
                        
                        # Add tool result to conversation
                        conversation.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps(tool_result, default=str)
                        })
                    
                    # Continue loop to get next LLM response
                    continue
                
                # No more tool calls - we have final answer
                return {
                    "content": assistant_message.content or "",
                    "tool_calls_made": tool_calls_made,
                    "iterations": iteration,
                    "finish_reason": finish_reason
                }
                
            except Exception as e:
                print(f"Error in tool calling loop (iteration {iteration}): {e}")
                raise
        
        # Max iterations exceeded
        raise Exception(
            f"Maximum iterations ({max_iterations}) exceeded in tool calling loop. "
            f"The conversation may be stuck in a loop."
        )
    
    def get_usage_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE
        }


# Global LLM client instance
llm_client = LLMClient()
