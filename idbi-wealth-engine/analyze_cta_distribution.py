"""Analyze CTA distribution across all chunks"""
import pickle
from pathlib import Path
from collections import Counter

# Load index
index_path = Path("app/rag/index/bm25_index.pkl")
with open(index_path, 'rb') as f:
    data = pickle.load(f)
    chunks = data['chunks']

print(f"Total chunks: {len(chunks)}")

# Count chunks with CTAs
chunks_with_cta = [c for c in chunks if c.get('cta_label')]
print(f"Chunks with CTA: {len(chunks_with_cta)} ({len(chunks_with_cta)/len(chunks)*100:.1f}%)")

# Distribution of CTA labels
cta_labels = Counter(c.get('cta_label') for c in chunks if c.get('cta_label'))

print(f"\n{'='*70}")
print("CTA LABEL DISTRIBUTION")
print('='*70)

for label, count in cta_labels.most_common():
    pct = count / len(chunks) * 100
    print(f"{label:30s} : {count:3d} chunks ({pct:5.1f}%)")

print(f"\n{'='*70}")
print("UNIQUE CTA LABELS")
print('='*70)
print(f"Total unique CTA labels: {len(cta_labels)}")

# Show some examples of each type
print(f"\n{'='*70}")
print("SAMPLE PAGES FOR EACH CTA TYPE")
print('='*70)

for label in list(cta_labels.keys())[:5]:  # Top 5 CTA labels
    print(f"\n🔘 CTA: \"{label}\"")
    examples = [c for c in chunks if c.get('cta_label') == label][:3]
    for ex in examples:
        print(f"   • {ex.get('title', 'N/A')[:60]}")
        print(f"     URL: {ex.get('url', 'N/A')}")
        print(f"     Category: {ex.get('category')} | Type: {ex.get('page_type')}")
