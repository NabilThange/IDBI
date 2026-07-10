"""Debug why 3 NRI pages are missing from index"""
import json
import pickle
from pathlib import Path

# Load index
with open('app/rag/index/bm25_index.pkl', 'rb') as f:
    data = pickle.load(f)
    chunks = data['chunks']

# Get all unique URLs in index
index_urls = set(c['url'] for c in chunks)

# Check NRI pages
nri_files = [
    ('apply-now-nri-aspx', 'https://www.idbi.bank.in/apply-now-nri.aspx'),
    ('nri-banking-aspx', 'https://www.idbi.bank.in/nri-banking.aspx'),
    ('nri-interest-rates-aspx', 'https://www.idbi.bank.in/nri-interest-rates.aspx'),
    ('nri-newsletter-aspx', 'https://www.idbi.bank.in/nri-newsletter.aspx'),
]

print("="*70)
print("NRI PAGE INDEX PRESENCE CHECK")
print("="*70)

for filename_base, expected_url in nri_files:
    matching_files = list(Path('app/kb_raw').glob(f"{filename_base}_*.json"))
    
    if not matching_files:
        print(f"\n❌ {filename_base}: File not found in kb_raw")
        continue
    
    filepath = matching_files[0]
    
    with open(filepath, 'r', encoding='utf-8') as f:
        page_data = json.load(f)
    
    url = page_data.get('url')
    content = page_data.get('content', '')
    category = page_data.get('category')
    
    in_index = url in index_urls
    
    print(f"\n{filename_base}:")
    print(f"  URL: {url}")
    print(f"  Category: {category}")
    print(f"  Content length: {len(content)} chars")
    print(f"  Content empty: {len(content.strip()) == 0}")
    print(f"  In index: {'✅ YES' if in_index else '❌ NO'}")
    
    if not in_index and content.strip():
        print(f"  ⚠️  Has content but missing from index!")
    
    if not in_index and not content.strip():
        print(f"  📝 Missing because content is empty")

print("\n" + "="*70)
