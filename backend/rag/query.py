import os
from pathlib import Path
from typing import Dict, Any, Optional
from .graph import create_graph, get_llm, load_vectorstore


def query_rag(question: str, index_dir: str = "index/", k: int = 6, headless: bool = False) -> Dict[str, Any]:
    """Query the RAG system with a question. Returns answer with context information."""
    # Resolve index directory relative to project root if not absolute
    index_path = Path(index_dir)
    if not index_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        index_path = backend_root / index_dir
    index_dir = str(index_path)

    # Load vectorstore
    if not index_path.exists():
        raise ValueError(f"Index directory not found: {index_dir}. Please run ingestion first.")

    vectorstore = load_vectorstore(str(index_path))

    # Get LLM
    llm = get_llm(headless=headless)

    # Create graph
    graph = create_graph(vectorstore, llm, k=k)

    # Execute query
    initial_state = {
        "question": question,
        "context": [],
        "answer": ""
    }

    result = graph.invoke(initial_state)

    # Format response
    context_info = []
    for item in result.get("context", []):
        context_info.append({
            "paper": item.get("meta", {}).get("paper", "Unknown"),
            "source": item.get("meta", {}).get("source", ""),
            "chunk_count": item.get("chunk_count", 0),
            "index": item.get("index", 0)
        })

    return {
        "question": question,
        "answer": result.get("answer", ""),
        "context": context_info,
        "num_sources": len(context_info)
    }


def check_index_status(index_dir: str = "index/") -> Dict[str, Any]:
    """Check if the RAG index exists and return status information."""
    # Resolve index directory relative to project root if not absolute
    index_path = Path(index_dir)
    if not index_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        index_path = backend_root / index_dir
    exists = index_path.exists()

    if not exists:
        return {
            "exists": False,
            "message": "Index not found. Please run ingestion first."
        }

    # Check for required files
    required_files = ["index.faiss", "index.pkl"]
    missing_files = []
    for file in required_files:
        if not (index_path / file).exists():
            missing_files.append(file)

    if missing_files:
        return {
            "exists": False,
            "message": f"Index incomplete. Missing files: {', '.join(missing_files)}"
        }

    # Try to load and get basic stats
    try:
        vectorstore = load_vectorstore(str(index_path))
        # Get approximate count (FAISS doesn't expose this directly, so we'll estimate)
        return {
            "exists": True,
            "message": "Index is ready",
            "index_dir": str(index_path.absolute())
        }
    except Exception as e:
        return {
            "exists": False,
            "message": f"Index exists but cannot be loaded: {str(e)}"
        }
