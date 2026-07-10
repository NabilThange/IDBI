"""Test if nri-banking.aspx creates chunks"""
import json
from pathlib import Path
from app.rag.ingest_crawl4ai import Crawl4AIIngester

# Load nri-banking page
files = list(Path('app/kb_raw').glob('nri-banking-aspx_*.json'))
with open(files[0], 'r', encoding='utf-8') as f:
    page_data = json.load(f)

print(f"Page: {page_data['url']}")
print(f"Content length: {len(page_data['content'])} chars")
print(f"Category: {page_data['category']}")
print()

# Try to chunk it
ingester = Crawl4AIIngester()
chunks = ingester.chunk_page(page_data)

print(f"Chunks created: {len(chunks)}")

for i, chunk in enumerate(chunks, 1):
    print(f"\n{i}. Section: {chunk['section']}")
    print(f"   Text length: {len(chunk['text'])} chars")
    print(f"   Tokens: {chunk['tokens']}")
    print(f"   Category: {chunk['category']}")
    print(f"   Preview: {chunk['text'][:100]}...")
