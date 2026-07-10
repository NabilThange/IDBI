"""Check NRI chunk content in BM25 index"""
import pickle

with open('app/rag/index/bm25_index.pkl', 'rb') as f:
    data = pickle.load(f)

chunks = data['chunks']

# Find NRI chunks
nri_chunks = [c for c in chunks if any(x in c.get('url', '') for x in ['nre-account', 'nro-account'])]

print(f"Total NRI account chunks: {len(nri_chunks)}\n")

for i, chunk in enumerate(nri_chunks[:8], 1):
    url = chunk.get('url', '')
    text = chunk.get('text', '')
    section = chunk.get('section', '')
    
    print(f"{i}. {url.split('/')[-1]}")
    print(f"   Section: {section}")
    print(f"   Text length: {len(text)} chars")
    print(f"   First 150 chars: {text[:150]}")
    print()
