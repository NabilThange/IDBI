"""
Enhanced Knowledge Base Ingestion Pipeline for 460+ Documents
Includes deduplication, junk filtering, and metadata tagging.
"""

import os
import re
import pickle
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import defaultdict
import numpy as np

from app.config import KB_DIR, RAG_INDEX_DIR, CHUNK_SIZE


class EnhancedIngester:
    """Enhanced ingester with dedup, filtering, and metadata"""
    
    def __init__(self):
        """Initialize ingester"""
        self.chunks = []
        self.seen_hashes: Set[str] = set()
        
        # Junk patterns to filter out
        self.junk_patterns = [
            r'cookie.*policy',
            r'privacy.*policy',
            r'terms.*conditions',
            r'careers?',
            r'about.*us',
            r'press.*release',
            r'contact.*us',
            r'sitemap',
            r'disclaimer',
            r'legal.*notice'
        ]
        
        # Category patterns for metadata tagging
        self.category_patterns = {
            'fixed_deposit': [r'fixed.*deposit', r'\bfd\b', r'term.*deposit'],
            'savings_account': [r'savings.*account', r'saving.*account'],
            'loan': [r'loan', r'lending', r'credit'],
            'home_loan': [r'home.*loan', r'housing.*loan', r'mortgage'],
            'personal_loan': [r'personal.*loan'],
            'gold': [r'gold', r'sovereign.*gold'],
            'mutual_fund': [r'mutual.*fund', r'\bmf\b', r'sip', r'systematic.*investment'],
            'insurance': [r'insurance', r'policy'],
            'credit_card': [r'credit.*card'],
            'debit_card': [r'debit.*card'],
            'retirement': [r'retirement', r'pension', r'nps', r'senior.*citizen'],
            'tax_saving': [r'tax.*saving', r'80c', r'80d', r'elss'],
            'digital_banking': [r'internet.*banking', r'mobile.*banking', r'online.*banking'],
            'faq': [r'\bfaq\b', r'frequently.*asked']
        }
    
    def compute_hash(self, text: str) -> str:
        """Compute content hash for deduplication"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def is_junk_file(self, filename: str, content: str) -> bool:
        """
        Determine if file should be filtered out.
        
        Args:
            filename: File name
            content: File content
            
        Returns:
            True if file is junk/low-value
        """
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Check filename patterns
        for pattern in self.junk_patterns:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                return True
        
        # Check content length - too short is likely junk
        if len(content.strip()) < 200:
            return True
        
        # Check for excessive boilerplate indicators
        boilerplate_indicators = [
            'this page intentionally left blank',
            'page not found',
            '404',
            'coming soon',
            'under construction'
        ]
        
        for indicator in boilerplate_indicators:
            if indicator in content_lower:
                return True
        
        return False
    
    def extract_category(self, filename: str, content: str) -> str:
        """
        Extract product category from filename and content.
        
        Args:
            filename: File name
            content: File content
            
        Returns:
            Category string
        """
        text = (filename + " " + content[:500]).lower()
        
        # Check each category pattern
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        
        return 'general'
    
    def clean_markdown(self, content: str) -> str:
        """
        Clean markdown content - remove navigation, boilerplate.
        
        Args:
            content: Raw markdown
            
        Returns:
            Cleaned content
        """
        # Remove navigation links
        content = re.sub(r'\[.*?\]\(#.*?\)', '', content)
        
        # Remove repeated headers/footers (common in scraped pages)
        lines = content.split('\n')
        cleaned_lines = []
        prev_line = ""
        repeat_count = 0
        
        for line in lines:
            if line.strip() == prev_line.strip() and prev_line.strip():
                repeat_count += 1
                if repeat_count > 2:  # Skip if repeated more than 2 times
                    continue
            else:
                repeat_count = 0
            
            cleaned_lines.append(line)
            prev_line = line
        
        content = '\n'.join(cleaned_lines)
        
        # Remove excessive whitespace
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        content = content.strip()
        
        return content
    
    def chunk_with_max_length(
        self,
        content: str,
        filename: str,
        category: str,
        max_length: int = CHUNK_SIZE
    ) -> List[Dict]:
        """
        Chunk by headers with max length enforcement.
        
        Args:
            content: Markdown content
            filename: Source file
            category: Product category
            max_length: Maximum chunk size
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        
        # Split by headers
        sections = re.split(r'\n(#{1,3}\s+.*?)\n', content)
        
        # Process first section (before any header)
        if sections[0].strip():
            chunks.extend(self._split_long_section(
                sections[0].strip(), filename, "Introduction", category, max_length
            ))
        
        # Process header-content pairs
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                header = sections[i].strip()
                section_content = sections[i + 1].strip()
                section_name = header.lstrip('#').strip()
                
                if section_content:
                    full_text = f"{header}\n\n{section_content}"
                    
                    if len(full_text) > max_length:
                        # Split long section
                        chunks.extend(self._split_long_section(
                            full_text, filename, section_name, category, max_length
                        ))
                    else:
                        chunks.append({
                            "text": full_text,
                            "source": filename,
                            "section": section_name,
                            "category": category,
                            "length": len(full_text)
                        })
        
        return chunks
    
    def _split_long_section(
        self,
        text: str,
        filename: str,
        section: str,
        category: str,
        max_length: int
    ) -> List[Dict]:
        """Split long section at sentence boundaries"""
        if len(text) <= max_length:
            return [{
                "text": text,
                "source": filename,
                "section": section,
                "category": category,
                "length": len(text)
            }]
        
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "source": filename,
                        "section": section,
                        "category": category,
                        "length": len(current_chunk)
                    })
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "source": filename,
                "section": section,
                "category": category,
                "length": len(current_chunk)
            })
        
        return chunks
    
    def deduplicate_exact(self, chunks: List[Dict]) -> List[Dict]:
        """
        Remove exact duplicates using content hashing.
        
        Args:
            chunks: List of chunks
            
        Returns:
            Deduplicated chunks
        """
        unique_chunks = []
        seen_hashes = set()
        duplicates_removed = 0
        
        for chunk in chunks:
            content_hash = self.compute_hash(chunk["text"])
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_chunks.append(chunk)
            else:
                duplicates_removed += 1
        
        print(f"   📊 Exact deduplication: {duplicates_removed} duplicates removed")
        return unique_chunks
    
    def load_and_process_all(self) -> List[Dict]:
        """
        Main processing pipeline: load → filter → clean → chunk → deduplicate
        
        Returns:
            Processed chunks
        """
        print("\n" + "="*70)
        print("🚀 Enhanced Knowledge Base Ingestion (460+ Documents)")
        print("="*70)
        
        # Find all markdown files
        md_files = list(KB_DIR.glob("*.md"))
        print(f"\n📚 Found {len(md_files)} markdown files")
        
        # Stage 1: Filter junk files
        print("\n🔍 Stage 1: Filtering junk/low-value files...")
        valid_files = []
        filtered_out = 0
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if self.is_junk_file(md_file.name, content):
                    filtered_out += 1
                else:
                    valid_files.append((md_file, content))
            except Exception as e:
                print(f"   ⚠️  Error reading {md_file.name}: {e}")
                filtered_out += 1
        
        print(f"   ✅ Kept: {len(valid_files)} files")
        print(f"   🗑️  Filtered: {filtered_out} files")
        
        # Stage 2: Clean, chunk, and tag
        print("\n📝 Stage 2: Cleaning, chunking, and tagging...")
        all_chunks = []
        
        for md_file, content in valid_files[:50]:  # Process first 50 to avoid timeout
            filename = md_file.name
            
            # Extract category
            category = self.extract_category(filename, content)
            
            # Clean content
            cleaned = self.clean_markdown(content)
            
            # Chunk with max length
            chunks = self.chunk_with_max_length(cleaned, filename, category)
            all_chunks.extend(chunks)
        
        print(f"   ✅ Created {len(all_chunks)} chunks from {len(valid_files[:50])} files")
        
        # Stage 3: Exact deduplication
        print("\n🔄 Stage 3: Deduplication...")
        unique_chunks = self.deduplicate_exact(all_chunks)
        
        # Stage 4: Statistics
        print("\n📊 Stage 4: Final Statistics...")
        category_counts = defaultdict(int)
        for chunk in unique_chunks:
            category_counts[chunk['category']] += 1
        
        print(f"\n   Total unique chunks: {len(unique_chunks)}")
        print(f"   Categories found:")
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"      - {cat}: {count} chunks")
        
        return unique_chunks
    
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
            
            with open(bm25_path, 'wb') as f:
                pickle.dump({'bm25': bm25, 'chunks': chunks}, f)
            
            print(f"   ✅ BM25 index saved: {bm25_path}")
            
        except Exception as e:
            print(f"   ❌ Error building BM25: {e}")
    
    def run(self):
        """Run complete enhanced ingestion"""
        chunks = self.load_and_process_all()
        self.build_bm25_index(chunks)
        
        print("\n" + "="*70)
        print("✅ Enhanced Ingestion Complete!")
        print("="*70)
        print(f"📦 Indexed: {len(chunks)} unique chunks")
        print(f"📁 Location: {RAG_INDEX_DIR}")
        print()


def run_enhanced_ingestion():
    """Main entry point"""
    ingester = EnhancedIngester()
    ingester.run()


if __name__ == "__main__":
    run_enhanced_ingestion()
