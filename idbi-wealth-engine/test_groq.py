"""
Quick test script to verify Groq API connection.
Run this after setting up your .env file with GROQ_API_KEY.
"""

import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import GROQ_API_KEY, GROQ_MODEL

try:
    from groq import Groq
    
    if not GROQ_API_KEY:
        print("❌ ERROR: GROQ_API_KEY not found in .env file")
        print("\n📝 Instructions:")
        print("1. Copy .env.example to .env")
        print("2. Get your API key from https://console.groq.com/keys")
        print("3. Add it to .env file: GROQ_API_KEY=your_key_here")
        sys.exit(1)
    
    print("🔍 Testing Groq API connection...")
    print(f"📊 Model: {GROQ_MODEL}")
    print(f"🔑 API Key: {GROQ_API_KEY[:10]}...{GROQ_API_KEY[-4:]}")
    print()
    
    # Initialize Groq client (simplified - let it pick up API key from env)
    client = Groq()
    
    # Test API call with a simple prompt
    print("💬 Sending test prompt...")
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful financial advisor for IDBI Bank."
            },
            {
                "role": "user",
                "content": "Say 'Hello! I am your AI wealth advisor.' in one short sentence."
            }
        ],
        temperature=0.7,
        max_tokens=50,
        top_p=1,
        stream=False
    )
    
    # Extract response
    ai_message = response.choices[0].message.content
    
    print("✅ SUCCESS! Groq API is working.")
    print(f"\n🤖 AI Response: {ai_message}")
    print(f"\n📈 Usage:")
    print(f"   - Prompt tokens: {response.usage.prompt_tokens}")
    print(f"   - Completion tokens: {response.usage.completion_tokens}")
    print(f"   - Total tokens: {response.usage.total_tokens}")
    print(f"\n⚡ Groq is ready for Phase 2!")
    
except ImportError:
    print("❌ ERROR: groq package not installed")
    print("\n📦 Install dependencies:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
    print("\n🔍 Troubleshooting:")
    print("1. Verify your GROQ_API_KEY is correct")
    print("2. Check your internet connection")
    print("3. Visit https://console.groq.com/ to verify your account")
    sys.exit(1)
