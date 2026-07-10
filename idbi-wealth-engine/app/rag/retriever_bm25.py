"""
BM25-Only Retriever (No Torch/Embeddings Required)
Keyword-based search for IDBI Knowledge Base
"""

import pickle
from pathlib import Path
from typing import List, Dict
import numpy as np

from app.config import RAG_INDEX_DIR, TOP_K_RETRIEVAL


class BM25Retriever:
    """BM25 keyword-based retriever without vector embeddings"""
    
    def __init__(self):
        """Initialize retriever"""
        self.bm25 = None
        self.chunks = []
        self.ranker = None  # FlashRank reranker
        self._initialized = False
    
    def _lazy_init(self) -> bool:
        """Lazy initialization to avoid loading at startup"""
        if self._initialized:
            return True
        
        try:
            # Load BM25 index
            bm25_path = RAG_INDEX_DIR / "bm25_index.pkl"
            if not bm25_path.exists():
                print(f"⚠️  BM25 index not found at {bm25_path}")
                print("   Run: python test_rag_simple.py to create index")
                return False
            
            with open(bm25_path, 'rb') as f:
                data = pickle.load(f)
                self.bm25 = data['bm25']
                self.chunks = data['chunks']
            
            # Init FlashRank reranker
            try:
                from flashrank import Ranker
                self.ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
                print("✅ FlashRank reranker loaded")
            except Exception as e:
                print(f"⚠️  FlashRank unavailable: {e}")
                self.ranker = None
            
            self._initialized = True
            print(f"✅ BM25 Retriever initialized with {len(self.chunks)} chunks")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing BM25 retriever: {e}")
            return False
    
    def search(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Dict]:
        """
        Search using BM25 + FlashRank reranking.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of matching chunks with full metadata
        """
        if not self._lazy_init():
            return []
        
        # BM25: get 3x candidates for reranking (ponytail: sparse pages need more candidates)
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        candidate_k = min(top_k * 3 if self.ranker else top_k, len(self.chunks))
        top_indices = np.argsort(scores)[::-1][:candidate_k]
        
        bm25_results = []
        for idx in top_indices:
            if scores[idx] > 0:
                chunk = self.chunks[idx].copy()  # Full chunk with all fields
                chunk['bm25_score'] = float(scores[idx])
                bm25_results.append(chunk)
        
        # FlashRank reranking if available
        if self.ranker and len(bm25_results) > 1:
            from flashrank import RerankRequest
            passages = [{"id": i, "text": r["text"]} for i, r in enumerate(bm25_results)]
            reranked = self.ranker.rerank(RerankRequest(query=query, passages=passages))
            results = []
            for item in reranked[:top_k]:
                chunk = bm25_results[item["id"]].copy()
                chunk['score'] = item['score']
                results.append(chunk)
        else:
            results = bm25_results[:top_k]
            for r in results:
                r['score'] = r.get('bm25_score', 0)
        
        return results
    
    def retrieve(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Dict]:
        """
        Main retrieval method (alias for search).
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            Retrieved chunks
        """
        return self.search(query, top_k)
    
    def is_initialized(self) -> bool:
        """Check if index is available"""
        return (RAG_INDEX_DIR / "bm25_index.pkl").exists()
    
    def format_context(self, results: List[Dict], max_chunks: int = 3) -> str:
        """
        Format retrieved results into context string for LLM.
        
        Args:
            results: Search results
            max_chunks: Maximum number of chunks to include
            
        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant information found in knowledge base."
        
        context_parts = []
        for i, result in enumerate(results[:max_chunks], 1):
            context_parts.append(
                f"[Source {i}: {result['source']} - {result['section']}]\n"
                f"{result['text']}\n"
            )
        
        return "\n---\n\n".join(context_parts)


# Global BM25 retriever instance
bm25_retriever = BM25Retriever()
