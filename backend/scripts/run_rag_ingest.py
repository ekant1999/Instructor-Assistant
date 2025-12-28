#!/usr/bin/env python3
"""Run RAG ingestion on backend/data/pdfs"""

import sys
from pathlib import Path

# Add repo root so backend package imports resolve.
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from backend.rag.ingest import load_pdfs, split_documents, create_faiss_index


def main():
    backend_root = project_root / "backend"
    papers_dir = str(backend_root / "data" / "pdfs")
    index_dir = str(backend_root / "index")

    print("=" * 50)
    print("PDF Ingestion Pipeline")
    print("=" * 50)
    print(f"Papers directory: {papers_dir}")
    print(f"Index directory: {index_dir}")
    print("=" * 50)

    documents = load_pdfs(papers_dir)

    if not documents:
    print(f"No documents to process. Please add PDF files to {papers_dir}/")
        return

    chunks = split_documents(documents, chunk_size=1200, chunk_overlap=200)
    create_faiss_index(chunks, index_dir=index_dir)

    print("=" * 50)
    print("✓ Ingestion complete!")
    print("=" * 50)
    print("\nYou can now query the RAG system!")

if __name__ == "__main__":
    main()
