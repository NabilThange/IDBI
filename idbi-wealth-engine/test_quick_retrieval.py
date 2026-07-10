"""Quick retrieval test"""
from app.rag.test_retrieval import load_index, search_bm25, dedupe_by_url

# Load
bm25, chunks = load_index()

# Test queries
queries = [
    "FD interest rates",
    "how to apply for a personal loan",
    "NRI account FAQ"
]

for query in queries:
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print('='*70)
    
    results = search_bm25(query, bm25, chunks, 5)
    deduped = dedupe_by_url(results, 2)
    
    print(f"\nTop 2 unique sources:")
    for i, r in enumerate(deduped, 1):
        print(f"\n{i}. {r.get('title', 'N/A')[:60]}")
        print(f"   URL: {r.get('url')}")
        print(f"   Category: {r.get('category')} | Type: {r.get('page_type')}")
        print(f"   Score: {r.get('score', 0):.2f}")
        print(f"   CTA: {r.get('cta_label', 'None')} → {r.get('cta_url', 'N/A')}")
        print(f"   Text preview: {r.get('text', '')[:200]}...")
