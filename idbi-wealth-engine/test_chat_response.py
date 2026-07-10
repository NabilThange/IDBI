"""Test what /api/chat returns for credit card query"""
import requests
import json

# Start session first
print("Starting session...")
session_resp = requests.post('http://localhost:8000/api/session/start', json={'profile_id': 'rahul_001'})
print(f"Session: {session_resp.status_code}\n")

# Test chat
response = requests.post('http://localhost:8000/api/chat', json={
    'message': 'what type of credit card should i get? i am a middle class man',
    'session_id': 'rahul_001'
})

data = response.json()
print(f"Status: {response.status_code}")
print(f"\nTop-level fields:")
print(f"  sources: {data.get('sources')}")
print(f"  action: {data.get('action')}")
print(f"  tool_calls: {len(data.get('tool_calls_made', []))}")

print("\n" + "="*60)
print("TOOL RESULTS:")
print("="*60)
for tc in data.get('tool_calls_made', []):
    if tc.get('name') == 'search_idbi_knowledge':
        print(f"\nTool: {tc['name']}")
        print(f"Has 'result': {'result' in tc}")
        if 'result' in tc:
            result = tc['result']
            print(f"Result type: {type(result)}")
            print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'NOT A DICT'}")
            if isinstance(result, dict):
                print(f"  sources: {result.get('sources')}")
                print(f"  action: {result.get('action')}")
