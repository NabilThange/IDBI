"""
Test Retrieval Quality on New Crawl4AI Index
Manual inspection of top-2 results for realistic queries.
"""

import pickle
from pathlib import Path
from typing import List, Dict
import numpy as np

from app.config import RAG_INDEX_DIR


def load_index():
    """Load BM25 index"""
    bm25_path = RAG_INDEX_DIR / "bm25_index.pkl"
    
    if not bm25_path.exists():
        print(f"❌ Index not found: {bm25_path}")
        print("   Run: python -m app.rag.ingest_crawl4ai")
        return None, None
    
    with open(bm25_path, 'rb') as f:
        data = pickle.load(f)
        return data['bm25'], data['chunks']


def search_bm25(query: str, bm25, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
    """Search using BM25"""
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    top_indices = np.argsort(scores)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            chunk = chunks[idx].copy()
            chunk['score'] = float(scores[idx])
            chunk['rank'] = len(results) + 1
            results.append(chunk)
    
    return results


def dedupe_by_url(results: List[Dict], max_unique: int = 2) -> List[Dict]:
    """Deduplicate results by URL, keeping top-scoring chunk per source"""
    seen_urls = set()
    deduped = []
    
    for result in results:
        url = result.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(result)
            if len(deduped) >= max_unique:
                break
    
    return deduped


def print_result(result: Dict, index: int):
    """Pretty print a single result"""
    print(f"\n{'='*70}")
    print(f"Result #{index}")
    print(f"{'='*70}")
    print(f"📄 Title: {result.get('title', 'N/A')}")
    print(f"🔗 URL: {result.get('url', 'N/A')}")
    print(f"📁 Category: {result.get('category', 'N/A')} | Type: {result.get('page_type', 'N/A')}")
    print(f"📍 Section: {result.get('section', 'N/A')}")
    print(f"⭐ Score: {result.get('score', 0):.4f}")
    print(f"🎯 Tokens: {result.get('tokens', 0)}")
    
    if result.get('cta_label') and result.get('cta_url'):
        print(f"🔘 CTA: \"{result['cta_label']}\" → {result['cta_url']}")
    else:
        print(f"🔘 CTA: None")
    
    print(f"\n📝 Text Preview (first 300 chars):")
    text = result.get('text', '')
    print(f"   {text[:300]}...")


def test_query(query: str, bm25, chunks):
    """Test a single query"""
    print(f"\n\n{'#'*70}")
    print(f"# QUERY: {query}")
    print(f"{'#'*70}")
    
    # Get top 5 results
    results = search_bm25(query, bm25, chunks, top_k=5)
    
    if not results:
        print("\n❌ No results found")
        return
    
    print(f"\n✅ Found {len(results)} results")
    
    # Show top 5
    print(f"\n{'─'*70}")
    print("TOP 5 RESULTS (before deduplication):")
    print(f"{'─'*70}")
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.get('category')}] {result.get('title', 'N/A')[:60]}")
        print(f"   URL: {result.get('url', 'N/A')}")
        print(f"   Score: {result.get('score', 0):.4f} | Section: {result.get('section', 'N/A')}")
        print(f"   CTA: {result.get('cta_label', 'None')}")
    
    # Dedupe by URL (top 2 unique sources)
    deduped = dedupe_by_url(results, max_unique=2)
    
    print(f"\n{'─'*70}")
    print("TOP 2 UNIQUE SOURCES (after URL deduplication):")
    print(f"{'─'*70}")
    
    for i, result in enumerate(deduped, 1):
        print_result(result, i)


def main():
    """Run test queries"""
    print("\n" + "="*70)
    print("🧪 RETRIEVAL QUALITY TEST")
    print("="*70)
    
    # Load index
    print("\n📦 Loading BM25 index...")
    bm25, chunks = load_index()
    
    if bm25 is None:
        return
    
    print(f"✅ Loaded {len(chunks)} chunks")
    
    # Test queries
    test_queries = [
        "FD interest rates",
        "how to apply for a personal loan",
        "NRI account FAQ",
        "fixed deposit for senior citizens",
        "home loan eligibility",
        "savings account types",
    ]
    
    for query in test_queries:
        test_query(query, bm25, chunks)
        input("\n\nPress Enter to continue to next query...")
    
    print("\n" + "="*70)
    print("✅ Test Complete!")
    print("="*70)


if __name__ == "__main__":
    main()
