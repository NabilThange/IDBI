"""
Batch ingestion for all 468 documents
Processes in batches to avoid memory issues
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.rag.ingest_enhanced import EnhancedIngester

def run_batched_ingestion(batch_size=100):
    """Process all files in batches"""
    ingester = EnhancedIngester()
    
    print("\n" + "="*70)
    print("🚀 Batched Knowledge Base Ingestion (ALL 468 Documents)")
    print("="*70)
    
    # Find all files
    from app.config import KB_DIR
    md_files = list(KB_DIR.glob("*.md"))
    print(f"\n📚 Found {len(md_files)} markdown files")
    
    # Filter junk
    print("\n🔍 Stage 1: Filtering junk/low-value files...")
    valid_files = []
    filtered_out = 0
    
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if ingester.is_junk_file(md_file.name, content):
                filtered_out += 1
            else:
                valid_files.append((md_file, content))
        except Exception as e:
            filtered_out += 1
    
    print(f"   ✅ Kept: {len(valid_files)} files")
    print(f"   🗑️  Filtered: {filtered_out} files")
    
    # Process in batches
    print(f"\n📝 Stage 2: Processing {len(valid_files)} files in batches of {batch_size}...")
    all_chunks = []
    
    for batch_start in range(0, len(valid_files), batch_size):
        batch_end = min(batch_start + batch_size, len(valid_files))
        batch = valid_files[batch_start:batch_end]
        
        print(f"\n   Batch {batch_start//batch_size + 1}: Processing files {batch_start+1}-{batch_end}...")
        
        for md_file, content in batch:
            filename = md_file.name
            category = ingester.extract_category(filename, content)
            cleaned = ingester.clean_markdown(content)
            chunks = ingester.chunk_with_max_length(cleaned, filename, category)
            all_chunks.extend(chunks)
        
        print(f"      ✓ Batch complete: {len(all_chunks)} total chunks so far")
    
    print(f"\n   ✅ Created {len(all_chunks)} chunks from {len(valid_files)} files")
    
    # Deduplicate
    print("\n🔄 Stage 3: Deduplication...")
    unique_chunks = ingester.deduplicate_exact(all_chunks)
    
    # Statistics
    print("\n📊 Stage 4: Final Statistics...")
    from collections import defaultdict
    category_counts = defaultdict(int)
    for chunk in unique_chunks:
        category_counts[chunk['category']] += 1
    
    print(f"\n   Total unique chunks: {len(unique_chunks)}")
    print(f"   Top categories:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"      - {cat}: {count} chunks")
    
    # Build BM25
    ingester.build_bm25_index(unique_chunks)
    
    print("\n" + "="*70)
    print("✅ Complete Ingestion Finished!")
    print("="*70)
    print(f"📦 Total indexed: {len(unique_chunks)} unique chunks")
    print(f"📁 From: {len(valid_files)} valid files (out of {len(md_files)} total)")
    print()


if __name__ == "__main__":
    run_batched_ingestion(batch_size=100)
