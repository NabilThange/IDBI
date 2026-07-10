"""Check what NRI pages exist in crawl data"""
import json

# Load manifest
with open('app/kb_raw/crawl_manifest.json', 'r') as f:
    manifest = json.load(f)

# Find NRI pages
nri_pages = [p for p in manifest['crawled_pages'] if 'nri' in p['url'].lower()]

print(f"NRI pages in manifest: {len(nri_pages)}\n")

for i, page in enumerate(nri_pages, 1):
    print(f"{i}. {page['url']}")
    print(f"   Category: {page['category']} | Type: {page['page_type']}")
    print()
