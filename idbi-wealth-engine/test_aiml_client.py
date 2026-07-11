"""Small offline check for AIMLAPI tool-call batching."""

import time

from app.core.llm_client import LLMClient


class Function:
    def __init__(self, name):
        self.name, self.arguments = name, "{}"


class ToolCall:
    def __init__(self, call_id, name):
        self.id, self.function = call_id, Function(name)

    def model_dump(self, **_):
        return {"id": self.id, "type": "function", "function": {"name": self.function.name, "arguments": "{}"}}


class FakeCompletions:
    def __init__(self):
        self.calls = 0
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        self.calls += 1
        calls = [ToolCall("a", "one"), ToolCall("b", "two")] if self.calls == 1 else []
        message = type("Message", (), {"content": "done" if not calls else None, "tool_calls": calls})()
        choice = type("Choice", (), {"message": message, "finish_reason": "tool_calls" if calls else "stop"})()
        return type("Response", (), {"choices": [choice]})()


def demo():
    completions = FakeCompletions()
    client = LLMClient()
    client.client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    started = time.monotonic()
    result = client.chat_with_tools(
        [{"role": "user", "content": "test"}], [],
        {"one": lambda: (time.sleep(0.1), {"one": True})[1], "two": lambda: (time.sleep(0.1), {"two": True})[1]},
    )
    assert result["content"] == "done" and len(result["tool_calls_made"]) == 2
    assert completions.requests[0]["parallel_tool_calls"] is True
    assert time.monotonic() - started < 0.18, "tool calls did not run concurrently"


if __name__ == "__main__":
    demo()
    print("AIMLAPI parallel tool-call check passed")
