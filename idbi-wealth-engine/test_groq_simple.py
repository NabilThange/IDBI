"""
Minimal Groq API test - exactly matching your working example
"""
import os
from dotenv import load_dotenv

load_dotenv()

from groq import Groq

client = Groq()

completion = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "user",
            "content": "Say hello in one sentence"
        }
    ],
    temperature=1,
    max_tokens=50,
    top_p=1,
    stream=False
)

print("✅ SUCCESS! Groq API is working.")
print(f"\n🤖 AI Response: {completion.choices[0].message.content}")
print(f"\n📈 Usage:")
print(f"   - Prompt tokens: {completion.usage.prompt_tokens}")
print(f"   - Completion tokens: {completion.usage.completion_tokens}")
print(f"   - Total tokens: {completion.usage.total_tokens}")
