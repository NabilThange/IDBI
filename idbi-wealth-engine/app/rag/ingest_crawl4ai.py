"""
Ingestion Pipeline for Crawl4AI JSON Output
Replaces ingest_enhanced.py - processes 396 JSON files with rich metadata.

Key Differences from Old Pipeline:
- Input: JSON files with structured metadata (url, title, content, category, page_type, cta_label, cta_url)
- Chunking: Header-aware splitting on markdown structure, not naive fixed-size
- Metadata: Every chunk carries source page metadata for frontend pills/buttons
- Output: BM25 index + optional FlashRank reranking (no ChromaDB/embeddings in this pass)

Defensive filters (backstops for crawler-side issues):
- Maintenance-banner chunks: dropped silently, not indexed
- Generic-only CTAs on non-contact pages: cta_label/cta_url set to None
"""

import json
import pickle
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict, Counter

from app.config import RAG_INDEX_DIR


# Configuration
KB_RAW_DIR = Path(__file__).parent.parent / "kb_raw"
CHUNK_SIZE_MIN = 300  # tokens (approx 300-500 tokens per chunk)
CHUNK_SIZE_MAX = 500

# Maintenance-banner detection — backstop for any pages caught in outage windows
MAINTENANCE_PATTERNS = [
    re.compile(r"due to technical reasons, the site is not available", re.IGNORECASE),
    re.compile(r"sorry for the inconvenience caused", re.IGNORECASE),
]

# Generic sitewide CTA URLs that should NOT be surfaced on non-contact pages
GENERIC_CTA_URLS = {
    "apply-now.aspx",
    "contact-us.aspx",
    "customer-care-centre.aspx",
    "customer-care.aspx",
    "24-7-care.aspx",
}
CHUNK_OVERLAP = 50  # tokens overlap for context continuity


class Crawl4AIIngester:
    """Ingester for crawl4ai JSON output with rich metadata"""
    
    def __init__(self):
        """Initialize ingester"""
        self.chunks = []
        self.seen_hashes: Set[str] = set()
        self.stats = defaultdict(int)
    
    def compute_hash(self, text: str) -> str:
        """Compute content hash for deduplication"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (words * 1.3)"""
        return int(len(text.split()) * 1.3)
    
    def split_by_headers(self, content: str) -> List[tuple[str, str]]:
        """
        Split markdown content by headers (#, ##, ###).
        
        Args:
            content: Markdown content
            
        Returns:
            List of (header, content) tuples
        """
        # Split on markdown headers
        parts = re.split(r'\n(#{1,3}\s+.+?)\n', content)
        
        sections = []
        
        # Handle content before first header
        if parts and parts[0].strip():
            sections.append(("Introduction", parts[0].strip()))
        
        # Process header-content pairs
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                header = parts[i].strip().lstrip('#').strip()
                section_content = parts[i + 1].strip()
                
                if section_content:
                    sections.append((header, section_content))
        
        # If no headers found, treat whole content as one section
        if not sections and content.strip():
            sections.append(("Main Content", content.strip()))
        
        return sections
    
    def split_long_text(
        self,
        text: str,
        max_tokens: int = CHUNK_SIZE_MAX,
        overlap_tokens: int = CHUNK_OVERLAP
    ) -> List[str]:
        """
        Split long text at sentence boundaries with overlap.
        
        Args:
            text: Text to split
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Tokens to overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append(" ".join(current_chunk))
                
                # Keep last few sentences for overlap
                overlap_sentences = []
                overlap_tokens = 0
                for s in reversed(current_chunk):
                    s_tokens = self.estimate_tokens(s)
                    if overlap_tokens + s_tokens < overlap_tokens:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_tokens = overlap_tokens
            
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks if chunks else [text]
    
    def chunk_page(self, page_data: Dict) -> List[Dict]:
        """
        Chunk a single page with header-aware splitting and metadata preservation.
        
        Args:
            page_data: Page JSON data
            
        Returns:
            List of chunks with metadata
        """
        content = page_data.get("content", "").strip()
        
        if not content:
            self.stats["empty_content"] += 1
            return []
        
        # Backstop: drop pages that are maintenance-window captures with no real content
        if any(p.search(content) for p in MAINTENANCE_PATTERNS):
            # Only drop if the maintenance text is the primary content (very short)
            if len(content) < 500:
                self.stats["maintenance_dropped"] += 1
                return []
        
        # Backstop: suppress generic-only CTAs on non-contact pages
        page_type = page_data.get("page_type", "general")
        cta_label = page_data.get("cta_label")
        cta_url = page_data.get("cta_url") or ""
        if page_type != "contact" and any(g in cta_url.lower() for g in GENERIC_CTA_URLS):
            # Only suppress if we have no specific CTA at all
            # (If cta_url is generic AND label is Contact Us, it was a nav/footer match — drop it)
            if cta_label and cta_label.lower() in ("contact us", "apply now"):
                cta_label = None
                cta_url = None
                self.stats["generic_cta_suppressed"] += 1
        
        # Extract metadata (will be attached to every chunk)
        metadata = {
            "url": page_data.get("url", ""),
            "title": page_data.get("title", ""),
            "category": page_data.get("category", "general"),
            "page_type": page_type,
            "cta_label": cta_label,
            "cta_url": cta_url or None,
        }
        
        # Split by headers first
        sections = self.split_by_headers(content)
        
        chunks = []
        
        for header, section_content in sections:
            section_tokens = self.estimate_tokens(section_content)
            
            # If section is small enough, keep as single chunk
            if section_tokens <= CHUNK_SIZE_MAX:
                chunk_text = f"## {header}\n\n{section_content}" if header != "Main Content" else section_content
                
                chunk = {
                    "text": chunk_text,
                    "section": header,
                    "tokens": section_tokens,
                    **metadata  # Unpack metadata into chunk
                }
                chunks.append(chunk)
                self.stats["chunks_created"] += 1
            
            else:
                # Split long section with overlap
                sub_chunks = self.split_long_text(section_content, CHUNK_SIZE_MAX, CHUNK_OVERLAP)
                
                for i, sub_chunk in enumerate(sub_chunks):
                    section_label = f"{header} (part {i+1})" if len(sub_chunks) > 1 else header
                    chunk_text = f"## {section_label}\n\n{sub_chunk}"
                    
                    chunk = {
                        "text": chunk_text,
                        "section": section_label,
                        "tokens": self.estimate_tokens(sub_chunk),
                        **metadata
                    }
                    chunks.append(chunk)
                    self.stats["chunks_created"] += 1
                    self.stats["long_sections_split"] += 1
        
        return chunks
    
    def deduplicate_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Remove exact duplicate chunks by content hash.
        
        Args:
            chunks: List of chunks
            
        Returns:
            Deduplicated chunks
        """
        unique_chunks = []
        seen_hashes = set()
        
        for chunk in chunks:
            content_hash = self.compute_hash(chunk["text"])
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_chunks.append(chunk)
            else:
                self.stats["duplicates_removed"] += 1
        
        return unique_chunks
    
    def load_and_process_all(self) -> List[Dict]:
        """
        Main processing pipeline: load JSON → chunk → deduplicate → attach metadata.
        
        Returns:
            Processed chunks with full metadata
        """
        print("\n" + "="*70)
        print("🚀 Crawl4AI Knowledge Base Ingestion")
        print("="*70)
        
        # Find all JSON files
        json_files = list(KB_RAW_DIR.glob("*.json"))
        # Exclude manifest
        json_files = [f for f in json_files if f.name != "crawl_manifest.json"]
        
        print(f"\n📚 Found {len(json_files)} JSON files in {KB_RAW_DIR}")
        
        if not json_files:
            print("❌ No JSON files found. Run crawler first:")
            print("   python -m app.crawler.crawl4ai_client")
            return []
        
        # Stage 1: Load and chunk
        print("\n📝 Stage 1: Loading and chunking pages...")
        all_chunks = []
        failed_files = []
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    page_data = json.load(f)
                
                chunks = self.chunk_page(page_data)
                all_chunks.extend(chunks)
                self.stats["pages_processed"] += 1
                
            except Exception as e:
                print(f"   ⚠️  Error processing {json_file.name}: {e}")
                failed_files.append(json_file.name)
                self.stats["pages_failed"] += 1
        
        print(f"   Processed: {self.stats['pages_processed']} pages")
        print(f"   Created: {self.stats['chunks_created']} chunks")
        if self.stats.get('empty_content'):
            print(f"   Skipped (empty content): {self.stats['empty_content']} pages")
        if self.stats.get('maintenance_dropped'):
            print(f"   Skipped (maintenance-only): {self.stats['maintenance_dropped']} pages  [backstop]")
        if self.stats.get('generic_cta_suppressed'):
            print(f"   Generic CTAs suppressed: {self.stats['generic_cta_suppressed']} pages  [backstop]")
        if failed_files:
            print(f"   Failed: {len(failed_files)} files")
        
        # Stage 2: Deduplication
        print("\n🔄 Stage 2: Deduplication...")
        unique_chunks = self.deduplicate_chunks(all_chunks)
        print(f"   ✅ Unique chunks: {len(unique_chunks)}")
        print(f"   🗑️  Duplicates removed: {self.stats['duplicates_removed']}")
        
        # Stage 3: Statistics
        print("\n📊 Stage 3: Statistics...")
        self.print_statistics(unique_chunks)
        
        return unique_chunks
    
    def print_statistics(self, chunks: List[Dict]):
        """Print detailed statistics about processed chunks"""
        category_counts = Counter(c["category"] for c in chunks)
        chunks_with_cta = [c for c in chunks if c.get('cta_url')]
        cta_label_counts = Counter(c.get('cta_label') for c in chunks_with_cta)
        
        print(f"\n   Total chunks: {len(chunks)}")
        print(f"   Chunks with CTAs: {len(chunks_with_cta)} ({len(chunks_with_cta)/len(chunks)*100:.1f}%)")
        print(f"\n   CTA label distribution:")
        for label, count in cta_label_counts.most_common(10):
            print(f"      - {label}: {count} ({count/len(chunks)*100:.1f}%)")
        print(f"\n   Top categories:")
        for cat, count in category_counts.most_common(10):
            print(f"      - {cat}: {count} chunks")
        
        page_type_counts = Counter(c["page_type"] for c in chunks)
        print(f"\n   Top page types:")
        for ptype, count in page_type_counts.most_common(10):
            print(f"      - {ptype}: {count} chunks")
        
        tokens = [c["tokens"] for c in chunks]
        print(f"\n   Token distribution:")
        print(f"      - Min: {min(tokens)} tokens")
        print(f"      - Max: {max(tokens)} tokens")
        print(f"      - Avg: {sum(tokens) / len(tokens):.0f} tokens")
    
    def build_bm25_index(self, chunks: List[Dict]):
        """Build and save BM25 index"""
        if not chunks:
            print("\n⚠️  No chunks to index")
            return
        
        print(f"\n🔍 Building BM25 index for {len(chunks)} chunks...")
        
        try:
            from rank_bm25 import BM25Okapi
            
            # Tokenize
            texts = [chunk["text"] for chunk in chunks]
            tokenized = [doc.lower().split() for doc in texts]
            
            # Build BM25
            bm25 = BM25Okapi(tokenized)
            
            # Save
            RAG_INDEX_DIR.mkdir(parents=True, exist_ok=True)
            bm25_path = RAG_INDEX_DIR / "bm25_index.pkl"
            
            # Backup old index if it exists
            if bm25_path.exists():
                backup_path = RAG_INDEX_DIR / "bm25_index.pkl.old"
                print(f"   📦 Backing up old index to {backup_path.name}")
                bm25_path.rename(backup_path)
            
            with open(bm25_path, 'wb') as f:
                pickle.dump({'bm25': bm25, 'chunks': chunks}, f)
            
            print(f"   ✅ BM25 index saved: {bm25_path}")
            print(f"   📁 Index size: {bm25_path.stat().st_size / 1024 / 1024:.2f} MB")
            
        except Exception as e:
            print(f"   ❌ Error building BM25: {e}")
            raise
    
    def run(self):
        """Run complete ingestion pipeline"""
        chunks = self.load_and_process_all()
        
        if not chunks:
            print("\n❌ No chunks generated. Ingestion failed.")
            return
        
        self.build_bm25_index(chunks)
        
        print("\n" + "="*70)
        print("✅ Ingestion Complete!")
        print("="*70)
        print(f"📦 Total chunks indexed: {len(chunks)}")
        print(f"📁 Index location: {RAG_INDEX_DIR}")
        print(f"\n💡 Next steps:")
        print("   1. Test retrieval: python -m app.rag.test_retrieval")
        print("   2. Wire into chat: Update chat.py to use metadata-rich responses")
        print()


def run_crawl4ai_ingestion():
    """Main entry point"""
    ingester = Crawl4AIIngester()
    ingester.run()


if __name__ == "__main__":
    run_crawl4ai_ingestion()
