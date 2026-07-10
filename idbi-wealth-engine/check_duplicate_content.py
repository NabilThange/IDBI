"""Check if missing NRI pages have duplicate content"""
import json
import hashlib
from pathlib import Path

def compute_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

# Check the 3 missing pages
missing_pages = [
    'apply-now-nri-aspx',
    'nri-banking-aspx',
    'nri-newsletter-aspx'
]

print("Checking content of missing NRI pages:\n")

for page_base in missing_pages:
    files = list(Path('app/kb_raw').glob(f"{page_base}_*.json"))
    if files:
        with open(files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        content = data.get('content', '')
        content_hash = compute_hash(content)
        
        print(f"{page_base}:")
        print(f"  Length: {len(content)} chars")
        print(f"  Hash: {content_hash}")
        print(f"  Content: {content[:150]}...")
        print()
