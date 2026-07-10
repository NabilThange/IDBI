"""
Hybrid Retriever for IDBI Knowledge Base
Combines BM25 (keyword) and vector search with reranking.
"""

import pickle
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

from app.config import RAG_INDEX_DIR, TOP_K_RETRIEVAL, RERANK_TOP_N


class HybridRetriever:
    """Hybrid search combining BM25 and vector search with reranking"""
    
    def __init__(self):
        """Initialize retriever with vector store and BM25 index"""
        self.chroma_client = None
        self.collection = None
        self.bm25 = None
        self.chunks = []
        self.embedding_model = None
        self._initialized = False
    
    def _lazy_init(self):
        """Lazy initialization to avoid loading heavy models at startup"""
        if self._initialized:
            return True
        
        try:
            # Initialize Chroma
            chroma_path = RAG_INDEX_DIR / "chroma"
            if not chroma_path.exists():
                print(f"⚠️  Vector store not found at {chroma_path}")
                print("   Run ingestion first: python -m app.rag.ingest")
                return False
            
            self.chroma_client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.chroma_client.get_collection("idbi_knowledge")
            
            # Load BM25 index
            bm25_path = RAG_INDEX_DIR / "bm25_index.pkl"
            if not bm25_path.exists():
                print(f"⚠️  BM25 index not found at {bm25_path}")
                return False
            
            with open(bm25_path, 'rb') as f:
                data = pickle.load(f)
                self.bm25 = data['bm25']
                self.chunks = data['chunks']
            
            # Load embedding model (only when needed)
            from sentence_transformers import SentenceTransformer
            from app.config import EMBEDDING_MODEL
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Error initializing retriever: {e}")
            return False
    
    def search_bm25(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Dict]:
        """
        BM25 keyword search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of matching chunks with scores
        """
        if not self._lazy_init():
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k indices
        import numpy as np
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include if there's a match
                results.append({
                    "text": self.chunks[idx]["text"],
                    "source": self.chunks[idx]["source"],
                    "section": self.chunks[idx]["section"],
                    "score": float(scores[idx]),
                    "method": "bm25"
                })
        
        return results
    
    def search_vector(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Dict]:
        """
        Vector similarity search.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of matching chunks with scores
        """
        if not self._lazy_init():
            return []
        
        # Embed query
        query_embedding = self.embedding_model.encode([query])[0].tolist()
        
        # Search in Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "text": results['documents'][0][i],
                "source": results['metadatas'][0][i]['source'],
                "section": results['metadatas'][0][i]['section'],
                "score": 1 - results['distances'][0][i],  # Convert distance to similarity
                "method": "vector"
            })
        
        return formatted_results
    
    def reciprocal_rank_fusion(
        self,
        bm25_results: List[Dict],
        vector_results: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """
        Combine BM25 and vector results using Reciprocal Rank Fusion.
        
        Args:
            bm25_results: Results from BM25 search
            vector_results: Results from vector search
            k: Constant for RRF (default 60)
            
        Returns:
            Fused and ranked results
        """
        # Create a map of chunk text to scores
        fusion_scores = {}
        chunk_data = {}
        
        # Process BM25 results
        for rank, result in enumerate(bm25_results, start=1):
            text = result["text"]
            score = 1 / (k + rank)
            fusion_scores[text] = fusion_scores.get(text, 0) + score
            if text not in chunk_data:
                chunk_data[text] = result
        
        # Process vector results
        for rank, result in enumerate(vector_results, start=1):
            text = result["text"]
            score = 1 / (k + rank)
            fusion_scores[text] = fusion_scores.get(text, 0) + score
            if text not in chunk_data:
                chunk_data[text] = result
        
        # Sort by fused scores
        sorted_texts = sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build final results
        fused_results = []
        for text, score in sorted_texts:
            result = chunk_data[text].copy()
            result["score"] = score
            result["method"] = "fusion"
            fused_results.append(result)
        
        return fused_results
    
    def rerank(self, query: str, results: List[Dict], top_n: int = RERANK_TOP_N) -> List[Dict]:
        """
        Rerank results using FlashRank (CPU-optimized cross-encoder).
        
        Args:
            query: Original search query
            results: Results to rerank
            top_n: Number of top results to return after reranking
            
        Returns:
            Reranked results
        """
        if not results:
            return results
        
        try:
            from flashrank import Ranker, RerankRequest
            
            # Initialize ranker (lightweight, CPU-friendly)
            ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
            
            # Prepare passages for reranking
            passages = [
                {
                    "id": i,
                    "text": result["text"],
                    "meta": {
                        "source": result["source"],
                        "section": result["section"]
                    }
                }
                for i, result in enumerate(results)
            ]
            
            # Rerank
            rerank_request = RerankRequest(query=query, passages=passages)
            reranked = ranker.rerank(rerank_request)
            
            # Format results
            reranked_results = []
            for item in reranked[:top_n]:
                original_result = results[item['id']]
                reranked_results.append({
                    "text": item['text'],
                    "source": original_result["source"],
                    "section": original_result["section"],
                    "score": item['score'],
                    "method": "reranked"
                })
            
            return reranked_results
            
        except Exception as e:
            print(f"⚠️  Reranking failed: {e}. Returning fusion results.")
            return results[:top_n]
    
    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K_RETRIEVAL,
        rerank: bool = True,
        rerank_top_n: int = RERANK_TOP_N
    ) -> List[Dict]:
        """
        Main retrieval method: hybrid search with optional reranking.
        
        Args:
            query: Search query
            top_k: Number of results from each method before fusion
            rerank: Whether to apply reranking
            rerank_top_n: Number of results after reranking
            
        Returns:
            Retrieved and optionally reranked chunks
        """
        if not self._lazy_init():
            # Return empty if indexes don't exist
            return []
        
        # Step 1: BM25 search
        bm25_results = self.search_bm25(query, top_k)
        
        # Step 2: Vector search
        vector_results = self.search_vector(query, top_k)
        
        # Step 3: Fusion
        fused_results = self.reciprocal_rank_fusion(bm25_results, vector_results)
        
        # Step 4: Reranking (optional)
        if rerank and len(fused_results) > 0:
            final_results = self.rerank(query, fused_results, rerank_top_n)
        else:
            final_results = fused_results[:rerank_top_n]
        
        return final_results
    
    def is_initialized(self) -> bool:
        """Check if indexes are available"""
        chroma_exists = (RAG_INDEX_DIR / "chroma").exists()
        bm25_exists = (RAG_INDEX_DIR / "bm25_index.pkl").exists()
        return chroma_exists and bm25_exists


# Global retriever instance
retriever = HybridRetriever()
