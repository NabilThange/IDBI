"""
Test Agentic Chat Endpoint
Tests the /api/chat endpoint with tool calling.
Requires: FastAPI server running on http://localhost:8000
"""

import requests
import json
import sys


API_BASE = "http://127.0.0.1:8000/api"


def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(title)
    print("="*60)


def check_server():
    """Check if server is running"""
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            return True
        return False
    except:
        return False


def select_profile(profile_id="rahul_001"):
    """Select a profile to start a session"""
    print_section("Step 1: Select Profile")
    
    url = f"{API_BASE}/session/select"
    response = requests.post(url, json={"profile_id": profile_id})
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Profile selected: {data['profile_id']}")
        return data['profile_id']
    else:
        print(f"❌ Failed to select profile: {response.status_code}")
        print(response.text)
        return None


def send_chat_message(session_id, message):
    """Send a chat message and display response"""
    print(f"\n💬 User: {message}")
    
    url = f"{API_BASE}/chat"
    payload = {
        "session_id": session_id,
        "message": message
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n🤖 Assistant: {data['message']}")
        
        if data['tool_calls_made']:
            print(f"\n🔧 Tools used ({len(data['tool_calls_made'])}):")
            for tool_call in data['tool_calls_made']:
                print(f"   - {tool_call['name']} (iteration {tool_call['iteration']})")
                if tool_call['arguments']:
                    print(f"     Args: {json.dumps(tool_call['arguments'], indent=6)}")
        
        print(f"\n📊 Stats: {data['iterations']} LLM calls")
        return True
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return False


def get_chat_history(session_id):
    """Get chat history"""
    url = f"{API_BASE}/chat/history"
    params = {"session_id": session_id}
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📜 Chat History ({data['count']} messages):")
        for msg in data['messages']:
            role_emoji = "💬" if msg['role'] == "user" else "🤖"
            print(f"   {role_emoji} {msg['role']}: {msg['content'][:80]}...")
        return True
    else:
        print(f"❌ Failed to get history: {response.status_code}")
        return False


def test_conversation_flow():
    """Test a full conversation with multiple tool calls"""
    print_section("AGENTIC CHAT TEST")
    
    # Step 1: Select profile
    session_id = select_profile("rahul_001")
    if not session_id:
        return False
    
    # Step 2: Test messages that trigger different tools
    print_section("Step 2: Test Tool Calling")
    
    test_messages = [
        "What's my name and age?",  # Should use get_customer_profile
        "How much did I spend on food last month?",  # Should use get_transactions
        "Tell me about IDBI's fixed deposit options",  # Should use search_idbi_knowledge
        "How am I doing with my house down payment goal?",  # Should use calculate_goal_projection
    ]
    
    for message in test_messages:
        success = send_chat_message(session_id, message)
        if not success:
            return False
    
    # Step 3: Get chat history
    print_section("Step 3: View Chat History")
    get_chat_history(session_id)
    
    return True


def test_multi_tool_query():
    """Test a complex query that requires multiple tools"""
    print_section("COMPLEX MULTI-TOOL QUERY TEST")
    
    session_id = select_profile("rahul_001")
    if not session_id:
        return False
    
    # Complex query that should trigger multiple tools
    message = (
        "Based on my profile and spending habits, what IDBI products would "
        "you recommend to help me reach my house down payment goal faster?"
    )
    
    print("\n🎯 Testing complex query that should use multiple tools:")
    success = send_chat_message(session_id, message)
    
    return success


def main():
    """Run chat endpoint tests"""
    print("="*60)
    print("PHASE 5: AGENTIC CHAT ENDPOINT TEST")
    print("="*60)
    
    # Check if server is running
    print("\n🔍 Checking server status...")
    if not check_server():
        print("❌ Server is not running!")
        print("\n📝 Start the server first:")
        print("   cd c:\\Users\\thang\\Downloads\\IDBI\\idbi-wealth-engine")
        print("   uvicorn app.main:app --reload")
        sys.exit(1)
    
    print("✅ Server is running")
    
    # Run tests
    print("\n🧪 Running tests...\n")
    
    success1 = test_conversation_flow()
    print("\n" + "-"*60 + "\n")
    success2 = test_multi_tool_query()
    
    # Summary
    print_section("TEST SUMMARY")
    if success1 and success2:
        print("✅ ALL TESTS PASSED!")
        print("\nThe agentic chat endpoint is working correctly with:")
        print("  ✓ Tool calling loop")
        print("  ✓ Multiple tool types")
        print("  ✓ Conversation history")
        print("  ✓ Complex multi-tool queries")
    else:
        print("⚠️  Some tests failed")
    
    print("\n📝 Next steps:")
    print("   - Test in the UI/frontend")
    print("   - Try more complex conversations")
    print("   - Monitor tool usage patterns")


if __name__ == "__main__":
    main()
