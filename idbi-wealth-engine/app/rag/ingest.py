"""
Knowledge Base Ingestion Pipeline
Loads markdown files, chunks them, embeds them, and builds searchable indexes.
"""

import os
import re
import pickle
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

from app.config import KB_DIR, RAG_INDEX_DIR, EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP


class KnowledgeBaseIngester:
    """Handles ingestion of knowledge base documents into vector and BM25 indexes"""
    
    def __init__(self):
        """Initialize ingester with embedding model and indexes"""
        print("🔄 Initializing Knowledge Base Ingester...")
        
        # Initialize embedding model
        print(f"📦 Loading embedding model: {EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Initialize Chroma vector store
        self.chroma_client = chromadb.PersistentClient(
            path=str(RAG_INDEX_DIR / "chroma"),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="idbi_knowledge",
            metadata={"description": "IDBI Bank knowledge base"}
        )
        
        print("✅ Ingester initialized")
    
    def clean_markdown(self, content: str) -> str:
        """
        Clean markdown content by removing navigation elements and excessive whitespace.
        
        Args:
            content: Raw markdown content
            
        Returns:
            Cleaned content
        """
        # Remove common navigation patterns
        content = re.sub(r'\[.*?\]\(#.*?\)', '', content)  # Remove anchor links
        content = re.sub(r'^\s*\*+\s*$', '', content, flags=re.MULTILINE)  # Remove line separators
        content = re.sub(r'\n{3,}', '\n\n', content)  # Normalize multiple newlines
        content = content.strip()
        
        return content
    
    def chunk_by_headers(self, content: str, filename: str) -> List[Dict[str, str]]:
        """
        Chunk markdown content by headers while preserving context.
        
        Args:
            content: Markdown content
            filename: Source filename for metadata
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        
        # Split by markdown headers (##, ###, etc.)
        sections = re.split(r'\n(#{1,3}\s+.*?)\n', content)
        
        # First section (before any header)
        if sections[0].strip():
            chunks.append({
                "text": sections[0].strip(),
                "source": filename,
                "section": "Introduction"
            })
        
        # Process header-content pairs
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                header = sections[i].strip()
                content_text = sections[i + 1].strip()
                
                if content_text:
                    # If content is too long, split further
                    if len(content_text) > CHUNK_SIZE:
                        # Split by paragraphs
                        paragraphs = content_text.split('\n\n')
                        current_chunk = ""
                        
                        for para in paragraphs:
                            if len(current_chunk) + len(para) < CHUNK_SIZE:
                                current_chunk += para + "\n\n"
                            else:
                                if current_chunk:
                                    chunks.append({
                                        "text": f"{header}\n\n{current_chunk.strip()}",
                                        "source": filename,
                                        "section": header.lstrip('#').strip()
                                    })
                                current_chunk = para + "\n\n"
                        
                        if current_chunk:
                            chunks.append({
                                "text": f"{header}\n\n{current_chunk.strip()}",
                                "source": filename,
                                "section": header.lstrip('#').strip()
                            })
                    else:
                        chunks.append({
                            "text": f"{header}\n\n{content_text}",
                            "source": filename,
                            "section": header.lstrip('#').strip()
                        })
        
        return chunks
    
    def load_and_chunk_documents(self) -> List[Dict[str, str]]:
        """
        Load all markdown files from KB directory and chunk them.
        
        Returns:
            List of document chunks with metadata
        """
        all_chunks = []
        
        print(f"\n📚 Loading documents from: {KB_DIR}")
        
        # Find all markdown files
        md_files = list(KB_DIR.glob("*.md"))
        
        if not md_files:
            print(f"⚠️  No markdown files found in {KB_DIR}")
            return all_chunks
        
        print(f"📄 Found {len(md_files)} documents")
        
        for md_file in md_files:
            print(f"   - Processing: {md_file.name}")
            
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Clean content
                cleaned_content = self.clean_markdown(content)
                
                # Chunk by headers
                chunks = self.chunk_by_headers(cleaned_content, md_file.name)
                all_chunks.extend(chunks)
                
                print(f"     ✓ Created {len(chunks)} chunks")
                
            except Exception as e:
                print(f"     ✗ Error processing {md_file.name}: {e}")
        
        print(f"\n✅ Total chunks created: {len(all_chunks)}")
        return all_chunks
    
    def embed_and_index(self, chunks: List[Dict[str, str]]):
        """
        Embed chunks and add to vector store.
        
        Args:
            chunks: List of document chunks
        """
        if not chunks:
            print("⚠️  No chunks to embed")
            return
        
        print(f"\n🔮 Embedding {len(chunks)} chunks...")
        
        # Extract texts
        texts = [chunk["text"] for chunk in chunks]
        
        # Generate embeddings
        print("   Generating embeddings (this may take a moment)...")
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Prepare metadata
        metadatas = [
            {
                "source": chunk["source"],
                "section": chunk["section"]
            }
            for chunk in chunks
        ]
        
        # Generate IDs
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        
        # Clear existing collection and add new documents
        print("   Adding to vector store...")
        
        # Delete existing documents
        try:
            self.collection.delete(where={})
        except:
            pass
        
        # Add in batches (Chroma has limits)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            end_idx = min(i + batch_size, len(chunks))
            
            self.collection.add(
                ids=ids[i:end_idx],
                embeddings=embeddings[i:end_idx].tolist(),
                documents=texts[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
        
        print(f"✅ Vector indexing complete: {len(chunks)} chunks indexed")
    
    def build_bm25_index(self, chunks: List[Dict[str, str]]):
        """
        Build BM25 index for keyword search.
        
        Args:
            chunks: List of document chunks
        """
        if not chunks:
            print("⚠️  No chunks for BM25 indexing")
            return
        
        print(f"\n🔍 Building BM25 index...")
        
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            print("⚠️  rank-bm25 not installed. Run: pip install rank-bm25")
            return
        
        # Tokenize documents (simple word-based)
        texts = [chunk["text"] for chunk in chunks]
        tokenized_corpus = [doc.lower().split() for doc in texts]
        
        # Build BM25 index
        bm25 = BM25Okapi(tokenized_corpus)
        
        # Save index
        bm25_path = RAG_INDEX_DIR / "bm25_index.pkl"
        with open(bm25_path, 'wb') as f:
            pickle.dump({
                'bm25': bm25,
                'chunks': chunks
            }, f)
        
        print(f"✅ BM25 index saved: {bm25_path}")
    
    def ingest_all(self):
        """
        Complete ingestion pipeline: load → chunk → embed → index
        """
        print("\n" + "="*60)
        print("🚀 Starting Knowledge Base Ingestion")
        print("="*60)
        
        # Step 1: Load and chunk
        chunks = self.load_and_chunk_documents()
        
        if not chunks:
            print("\n❌ No documents to ingest")
            return False
        
        # Step 2: Embed and add to vector store
        self.embed_and_index(chunks)
        
        # Step 3: Build BM25 index
        self.build_bm25_index(chunks)
        
        print("\n" + "="*60)
        print("✅ Knowledge Base Ingestion Complete!")
        print("="*60)
        print(f"📊 Total documents indexed: {len(chunks)}")
        print(f"📁 Index location: {RAG_INDEX_DIR}")
        print()
        
        return True


def run_ingestion():
    """Main function to run ingestion pipeline"""
    ingester = KnowledgeBaseIngester()
    success = ingester.ingest_all()
    return success


if __name__ == "__main__":
    # Run ingestion when script is executed directly.
    # Exit with a non-zero code on failure so CI/build steps (e.g. Render) fail loudly
    # instead of silently shipping a broken/empty index.
    import sys
    try:
        success = run_ingestion()
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        sys.exit(1)
    sys.exit(0 if success else 1)
