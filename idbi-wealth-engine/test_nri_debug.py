"""
Debug NRI query to see BM25 vs FlashRank results
"""

from app.rag.retriever_bm25 import bm25_retriever
import numpy as np

def test_queries():
    queries = [
        "NRI account FAQ",
        "NRI account",
        "NRE NRO account",
        "Non-Resident Indian account"
    ]
    
    for query in queries:
        print(f"\n{'='*70}")
        print(f"Query: {query}")
        print('='*70)
        
        # Initialize retriever
        if not bm25_retriever._lazy_init():
            print("Failed to init retriever")
            continue
        
        # Get BM25 scores (before reranking)
        tokenized_query = query.lower().split()
        bm25_scores = bm25_retriever.bm25.get_scores(tokenized_query)
        top_bm25_indices = np.argsort(bm25_scores)[::-1][:10]
        
        print("\n🔍 Top 10 BM25 Results (before reranking):")
        print("-" * 70)
        for rank, idx in enumerate(top_bm25_indices, 1):
            if bm25_scores[idx] > 0:
                chunk = bm25_retriever.chunks[idx]
                url = chunk.get("url", "")
                category = chunk.get("category", "")
                title = chunk.get("title", "")
                
                # Highlight NRI pages
                is_nri = any(x in url.lower() for x in ["nre", "nro", "fcnr"])
                marker = "🎯 NRI" if is_nri else ""
                
                print(f"{rank}. [{category}] {marker}")
                print(f"   {url.split('/')[-1]}")
                print(f"   BM25: {bm25_scores[idx]:.4f}")
        
        # Now get reranked results
        print("\n✨ Top 5 FlashRank Results (after reranking):")
        print("-" * 70)
        results = bm25_retriever.search(query, top_k=5)
        
        for i, r in enumerate(results, 1):
            url = r.get("url", "")
            category = r.get("category", "")
            score = r.get("score", 0)
            
            is_nri = any(x in url.lower() for x in ["nre", "nro", "fcnr"])
            marker = "🎯 NRI" if is_nri else ""
            
            print(f"{i}. [{category}] {marker}")
            print(f"   {url.split('/')[-1]}")
            print(f"   FlashRank: {score:.4f}")

if __name__ == "__main__":
    test_queries()
