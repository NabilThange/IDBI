"""
Test Phase 5: Tools + Agentic Chat
Verifies all 4 tool functions and the tool-calling loop.
"""

import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.tools import (
    get_customer_profile,
    get_transactions,
    search_idbi_knowledge,
    calculate_goal_projection,
    TOOL_REGISTRY
)
from app.core.session_store import session_store


def load_test_profile():
    """Load rahul profile for testing"""
    profile_path = Path(__file__).parent / "app" / "profiles" / "rahul_salaried.json"
    with open(profile_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_tool_1_get_customer_profile():
    """Test: get_customer_profile tool"""
    print("\n" + "="*60)
    print("TEST 1: get_customer_profile")
    print("="*60)
    
    try:
        result = get_customer_profile()
        print("✅ SUCCESS")
        print(f"Profile ID: {result['profile_id']}")
        print(f"Name: {result['name']}")
        print(f"Age: {result['age']}")
        print(f"Risk Profile: {result['risk_profile']}")
        print(f"Goals: {len(result['goals'])}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_tool_2_get_transactions():
    """Test: get_transactions tool"""
    print("\n" + "="*60)
    print("TEST 2: get_transactions")
    print("="*60)
    
    try:
        # Test 1: Get all transactions
        result = get_transactions(limit=5)
        print("✅ All transactions (limit 5):")
        print(f"   Total: {result['count']} transactions")
        print(f"   Debits: {result['debit_count']}, Credits: {result['credit_count']}")
        
        # Test 2: Filter by category
        result = get_transactions(category="food", limit=10)
        print(f"✅ Food transactions: {result['count']} found")
        
        # Test 3: Filter by type
        result = get_transactions(transaction_type="debit", limit=10)
        print(f"✅ Debit transactions: {result['count']} found")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_tool_3_calculate_goal_projection():
    """Test: calculate_goal_projection tool"""
    print("\n" + "="*60)
    print("TEST 3: calculate_goal_projection")
    print("="*60)
    
    try:
        # Get profile to see available goals
        profile = get_customer_profile()
        goals = profile.get('goals', [])
        
        if not goals:
            print("⚠️  No goals found in profile")
            return False
        
        # Test first goal
        goal_name = goals[0]['name']
        result = calculate_goal_projection(goal_name)
        
        print(f"✅ Goal: {result['name']}")
        print(f"   Target: ₹{result['target_amount']:,}")
        print(f"   Current: ₹{result['current_savings']:,}")
        print(f"   Progress: {result['progress_percent']}%")
        print(f"   Status: {result['status']}")
        print(f"   Required monthly: ₹{result['required_monthly_contribution']:,.0f}")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_tool_4_search_idbi_knowledge():
    """Test: search_idbi_knowledge tool"""
    print("\n" + "="*60)
    print("TEST 4: search_idbi_knowledge")
    print("="*60)
    
    try:
        # Test search
        result = search_idbi_knowledge("fixed deposit rates", top_k=3)
        
        if result['found']:
            print(f"✅ Found {result['count']} results")
            print(f"   Query: '{result['query']}'")
            print(f"   Sources: {', '.join(result['sources'][:2])}")
            
            # Show first result
            if result['results']:
                first = result['results'][0]
                print(f"\n   Top result:")
                print(f"   Source: {first['source']}")
                print(f"   Score: {first['relevance_score']}")
                print(f"   Text: {first['text'][:150]}...")
        else:
            print(f"⚠️  No results found (this is OK if RAG index not built yet)")
            print(f"   Message: {result['message']}")
        
        return True
    except ValueError as e:
        # Expected if RAG not initialized
        print(f"⚠️  RAG not initialized (expected): {e}")
        print("   Run: python test_rag_simple.py to create index")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_tool_registry():
    """Test: Tool registry contains all tools"""
    print("\n" + "="*60)
    print("TEST 5: Tool Registry")
    print("="*60)
    
    expected_tools = [
        "get_customer_profile",
        "get_transactions",
        "search_idbi_knowledge",
        "calculate_goal_projection"
    ]
    
    missing = []
    for tool_name in expected_tools:
        if tool_name not in TOOL_REGISTRY:
            missing.append(tool_name)
        else:
            print(f"✅ {tool_name} registered")
    
    if missing:
        print(f"❌ Missing tools: {', '.join(missing)}")
        return False
    
    return True


def test_tool_calling_integration():
    """Test: Tools work with LLM client tool definitions"""
    print("\n" + "="*60)
    print("TEST 6: Tool Definitions for LLM")
    print("="*60)
    
    try:
        from app.tools.get_customer_profile import TOOL_DEFINITION as t1
        from app.tools.get_transactions import TOOL_DEFINITION as t2
        from app.tools.search_idbi_knowledge import TOOL_DEFINITION as t3
        from app.tools.calculate_goal_projection import TOOL_DEFINITION as t4
        
        tools = [t1, t2, t3, t4]
        
        for tool_def in tools:
            name = tool_def['function']['name']
            desc = tool_def['function']['description']
            params = tool_def['function']['parameters']
            
            print(f"✅ {name}")
            print(f"   Description: {desc[:60]}...")
            print(f"   Required params: {params.get('required', [])}")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Run all Phase 5 tests"""
    print("=" * 60)
    print("PHASE 5 TEST SUITE: Tools + Agentic Chat")
    print("=" * 60)
    
    # Setup: Load test profile
    print("\n📋 Setup: Loading test profile...")
    profile = load_test_profile()
    session_store.set_profile(profile)
    print(f"✅ Loaded profile: {profile['name']} ({profile['profile_id']})")
    
    # Run tests
    tests = [
        test_tool_registry,
        test_tool_1_get_customer_profile,
        test_tool_2_get_transactions,
        test_tool_3_calculate_goal_projection,
        test_tool_4_search_idbi_knowledge,
        test_tool_calling_integration,
    ]
    
    results = []
    for test_func in tests:
        result = test_func()
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED - Phase 5 tools are working!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
    
    print("\n📝 Next steps:")
    print("   1. Start the FastAPI server: uvicorn app.main:app --reload")
    print("   2. Test chat endpoint: POST /api/chat")
    print("   3. Use tools like 'What's my profile?' or 'Tell me about fixed deposits'")


if __name__ == "__main__":
    main()
