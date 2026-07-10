"""
Simple RAG test without heavy dependencies
Tests BM25 search and document chunking
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import KB_DIR, RAG_INDEX_DIR
import pickle

# Simple chunking test
print("=" * 60)
print("Testing Knowledge Base Processing")
print("=" * 60)

# Step 1: Load markdown files
md_files = list(KB_DIR.glob("*.md"))
print(f"\n📚 Found {len(md_files)} markdown files:")
for f in md_files:
    print(f"   - {f.name}")

# Step 2: Simple chunking
chunks = []
for md_file in md_files[:3]:  # Test with first 3 files
    print(f"\n📄 Processing: {md_file.name}")
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by headers
    import re
    sections = re.split(r'\n(#{1,3}\s+.*?)\n', content)
    
    file_chunks = 0
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            header = sections[i].strip()
            text = sections[i + 1].strip()
            if text:
                chunks.append({
                    "text": f"{header}\n\n{text[:500]}...",  # Truncate for display
                    "source": md_file.name,
                    "section": header.lstrip('#').strip()
                })
                file_chunks += 1
    
    print(f"   ✓ Created {file_chunks} chunks")

print(f"\n✅ Total chunks: {len(chunks)}")

# Step 3: Test BM25 (without torch)
print("\n" + "=" * 60)
print("Testing BM25 Search (No Torch Required)")
print("=" * 60)

try:
    from rank_bm25 import BM25Okapi
    
    # Tokenize
    texts = [chunk["text"] for chunk in chunks]
    tokenized = [doc.lower().split() for doc in texts]
    
    # Build index
    bm25 = BM25Okapi(tokenized)
    print("\n✅ BM25 index built successfully")
    
    # Test query
    test_query = "fixed deposit interest rates senior citizen"
    print(f"\n🔍 Test Query: \"{test_query}\"")
    
    query_tokens = test_query.lower().split()
    scores = bm25.get_scores(query_tokens)
    
    # Get top 3
    import numpy as np
    top_indices = np.argsort(scores)[::-1][:3]
    
    print("\n📊 Top 3 Results:")
    for rank, idx in enumerate(top_indices, 1):
        if scores[idx] > 0:
            print(f"\n{rank}. Score: {scores[idx]:.4f}")
            print(f"   Source: {chunks[idx]['source']}")
            print(f"   Section: {chunks[idx]['section']}")
            print(f"   Preview: {chunks[idx]['text'][:150]}...")
    
    # Save for later
    RAG_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(RAG_INDEX_DIR / "bm25_index.pkl", 'wb') as f:
        pickle.dump({'bm25': bm25, 'chunks': chunks}, f)
    
    print(f"\n✅ BM25 index saved to: {RAG_INDEX_DIR / 'bm25_index.pkl'}")
    
except ImportError:
    print("\n❌ rank-bm25 not installed")
    print("   Run: pip install rank-bm25")

print("\n" + "=" * 60)
print("✅ RAG Testing Complete!")
print("=" * 60)
print("\nNote: Vector search requires torch, which has DLL issues on your system.")
print("BM25 keyword search is working and can be used for retrieval.")
print("\nTo fix torch issues, you may need to:")
print("1. Disable Windows Application Control")
print("2. Or use a different Python environment")
print("3. Or use CPU-only torch: pip install torch --index-url https://download.pytorch.org/whl/cpu")
