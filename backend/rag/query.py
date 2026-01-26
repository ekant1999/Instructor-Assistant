import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from .graph import create_graph, get_llm, load_vectorstore, retrieve_node
from ..services import call_local_llm


def query_rag(
    question: str,
    index_dir: str = "index/",
    k: int = 6,
    headless: bool = False,
    paper_ids: Optional[List[int]] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
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

    selected_ids: Optional[Set[int]] = None
    if paper_ids:
        selected_ids = {int(pid) for pid in paper_ids}
    retrieve_k = max(k * 4, k) if selected_ids else k
    resolved_provider = (provider or "openai").strip().lower()
    if resolved_provider not in {"openai", "local"}:
        resolved_provider = "openai"

    if resolved_provider == "local":
        initial_state = {"question": question, "context": [], "answer": ""}
        retrieved = retrieve_node(initial_state, vectorstore, k=retrieve_k, paper_ids=selected_ids)
        context = retrieved.get("context", [])
        if not context:
            reason = "No indexed chunks found. Please run ingestion to build the index."
            if selected_ids:
                reason = "No indexed chunks found for the selected paper(s). Re-ingest the library to include metadata."
            return {
                "question": question,
                "answer": reason,
                "context": [],
                "num_sources": 0,
            }
        context_text = "\n\n".join([f"[{item['index']}] {item['text']}" for item in context])
        system_prompt = (
            "You are a helpful research assistant. Answer the question based ONLY on the provided context. "
            "Always include numbered citations [1], [2], etc. that correspond to the source numbers in the context. "
            "If information is not in the context, say so explicitly. "
            "Format your answer clearly with proper citations."
        )
        user_prompt = f"Context:\n\n{context_text}\n\nQuestion: {question}\n\nAnswer:"
        answer = call_local_llm(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        result = {"context": context, "answer": answer}
    else:
        # Get LLM
        llm = get_llm(headless=headless)
        graph = create_graph(vectorstore, llm, k=retrieve_k, paper_ids=selected_ids)
        initial_state = {"question": question, "context": [], "answer": ""}
        result = graph.invoke(initial_state)
        if not result.get("context"):
            reason = "No indexed chunks found. Please run ingestion to build the index."
            if selected_ids:
                reason = "No indexed chunks found for the selected paper(s). Re-ingest the library to include metadata."
            result["answer"] = reason

    # Format response
    context_info = []
    for item in result.get("context", []):
        meta = item.get("meta", {}) or {}
        context_info.append({
            "paper": meta.get("paper_title") or meta.get("paper", "Unknown"),
            "source": meta.get("source", ""),
            "chunk_count": item.get("chunk_count", 0),
            "index": item.get("index", 0),
            "paper_id": meta.get("paper_id"),
            "paper_title": meta.get("paper_title"),
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
