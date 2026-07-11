"""
Tool: Search IDBI Knowledge Base
Searches IDBI product knowledge using RAG retrieval.
"""

import json
import time
import datetime
from typing import Dict, Any, List

from app.rag.retriever_bm25 import bm25_retriever

def get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# Tool definition for Groq
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_idbi_knowledge",
        "description": "Search IDBI Bank's knowledge base for information about products, services, policies, interest rates, and features. Use this when you need official bank information to answer customer questions about IDBI offerings.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query describing what information you need (e.g., 'fixed deposit rates for senior citizens', 'home loan eligibility', 'savings account types')"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of relevant documents to retrieve (default: 5, max: 10)"
                }
            },
            "required": ["query"]
        }
    }
}


def search_idbi_knowledge(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Search IDBI knowledge base using BM25 retrieval.
    
    Args:
        query: Search query string
        top_k: Number of results to return (default: 5, max: 10)
        
    Returns:
        Dictionary containing search results and sources
        
    Raises:
        ValueError: If RAG index is not initialized
    """
    if not bm25_retriever.is_initialized():
        raise ValueError(
            "IDBI knowledge base is not available. "
            "Please run the ingestion script to create the search index."
        )
    
    # Clamp top_k between 1 and 10
    top_k = min(max(1, top_k), 10)
    
    # Perform search
    print(f"[{get_timestamp()}] [RAG] BM25 Retrieve started for query: \"{query}\"")
    rag_start = time.time()
    results = bm25_retriever.retrieve(query, top_k=top_k)
    rag_duration = time.time() - rag_start
    print(f"[{get_timestamp()}] [RAG] BM25 Retrieve completed in {rag_duration:.3f}s (found {len(results)} chunks)")
    
    if not results:
        return {
            "found": False,
            "message": f"No relevant information found for query: '{query}'",
            "answer_context": "",
            "sources": [],
            "action": None
        }
    
    # Dedupe by URL, keep highest-scored chunk per page
    seen_urls = {}
    for r in results:
        url = r.get("url", "")
        if url and (url not in seen_urls or r.get("score", 0) > seen_urls[url].get("score", 0)):
            seen_urls[url] = r
    
    # Format sources for frontend pills (top 2 unique URLs)
    sources = [
        {
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "category": r.get("category", "general")
        }
        for r in list(seen_urls.values())[:2]
    ]
    
    # Extract best CTA (skip generic "Contact Us")
    action = None
    for r in results:
        label = r.get("cta_label")
        url = r.get("cta_url")
        if label and url and label != "Contact Us":  # ponytail: suppress generic CTAs
            action = {"label": label, "url": url}
            break

    if not action and sources:
        action = {"label": "View on IDBI Bank", "url": sources[0]["url"]}
    
    # Format results for LLM consumption
    formatted_results = []
    for i, result in enumerate(results, 1):
        formatted_results.append({
            "rank": i,
            "text": result.get("text", ""),
            "source": result.get("source", "unknown"),
            "section": result.get("section", ""),
            "relevance_score": round(result.get("score", 0.0), 4)
        })
    
    return {
        "found": True,
        "query": query,
        "results": formatted_results,
        "count": len(formatted_results),
        "sources": sources,
        "action": action,
        "message": f"Found {len(formatted_results)} relevant documents from IDBI knowledge base"
    }
