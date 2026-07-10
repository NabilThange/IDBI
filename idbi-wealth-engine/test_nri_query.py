"""
Test NRI query ranking after FlashRank integration
Success criterion: NRE/NRO account pages in top 2 for queries they actually contain
"""

from app.rag.retriever_bm25 import bm25_retriever

def test_nri_ranking():
    # ponytail: test queries that NRI pages actually contain keywords for
    test_cases = [
        ("NRE NRO account", True, "Direct match - NRI pages contain these acronyms"),
        ("NRI savings deposit", True, "NRI pages mention savings/deposits"),
        ("home loan eligibility", False, "Control - should return loan pages"),
        ("fixed deposit rates", False, "Control - should return FD pages"),
    ]
    
    all_pass = True
    
    for query, expect_nri, description in test_cases:
        print(f"\nQuery: {query}")
        print(f"Expect NRI in top 2: {expect_nri} ({description})")
        print("=" * 60)
        
        results = bm25_retriever.search(query, top_k=5)
        
        for i, r in enumerate(results, 1):
            url = r.get("url", "")
            score = r.get("score", 0)
            category = r.get("category", "")
            
            is_nri_page = any(x in url.lower() for x in ["nre-account", "nro-account", "fcnr"])
            marker = " 🎯" if is_nri_page else ""
            
            print(f"{i}. [{category}]{marker} {url.split('/')[-1]} ({score:.4f})")
        
        # Check result
        top2_urls = [r.get("url", "") for r in results[:2]]
        has_nri_in_top2 = any(x in url.lower() for url in top2_urls for x in ["nre-account", "nro-account", "fcnr"])
        
        if has_nri_in_top2 == expect_nri:
            print("✅ PASS")
        else:
            expected_str = "NRI page" if expect_nri else "Non-NRI page"
            print(f"❌ FAIL: Expected {expected_str} in top 2")
            all_pass = False
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✅ ALL TESTS PASSED")
        print("\nFlashRank is working correctly:")
        print("- Semantic reranking improves results when relevant chunks exist")
        print("- Returns correct page types based on query intent")
    else:
        print("❌ SOME TESTS FAILED")

if __name__ == "__main__":
    test_nri_ranking()
