import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from .graph import create_graph, get_llm, load_vectorstore, retrieve_node
from .image_index import query_image_index
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

    total_docs = None
    try:
        total_docs = int(getattr(vectorstore.index, "ntotal", 0))
    except Exception:
        total_docs = None

    selected_ids: Optional[Set[int]] = None
    if paper_ids:
        selected_ids = {int(pid) for pid in paper_ids}
    if selected_ids and total_docs:
        # When filtering by paper_id, search the whole index so the selected paper
        # is guaranteed to be present before filtering.
        retrieve_k = total_docs
    else:
        retrieve_k = max(k * 4, k) if selected_ids else k
    resolved_provider = (provider or "openai").strip().lower()
    if resolved_provider not in {"openai", "local"}:
        resolved_provider = "openai"

    image_index_dir = os.getenv(
        "IMAGE_INDEX_DIR",
        str(Path(__file__).resolve().parents[1] / "index_images"),
    )
    image_k = int(os.getenv("IMAGE_QUERY_K", "4"))
    image_results: List[Dict[str, Any]] = []

    if resolved_provider == "local":
        initial_state = {"question": question, "context": [], "answer": ""}
        retrieved = retrieve_node(initial_state, vectorstore, k=retrieve_k, paper_ids=selected_ids)
        context = retrieved.get("context", [])
        if os.getenv("ENABLE_IMAGE_INDEX", "true").lower() in {"1", "true", "yes"}:
            image_results = query_image_index(question, image_index_dir, k=image_k, paper_ids=selected_ids)
            if image_results:
                base_index = len(context) + 1
                for offset, item in enumerate(image_results):
                    item["index"] = base_index + offset
                context = context + image_results
                image_results = []
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
        if os.getenv("ENABLE_IMAGE_INDEX", "true").lower() in {"1", "true", "yes"}:
            image_results = query_image_index(question, image_index_dir, k=image_k, paper_ids=selected_ids)
        if not result.get("context"):
            reason = "No indexed chunks found. Please run ingestion to build the index."
            if selected_ids:
                reason = "No indexed chunks found for the selected paper(s). Re-ingest the library to include metadata."
            result["answer"] = reason

    # Format response
    context_info = []
    combined_context = list(result.get("context", []))
    if image_results:
        base_index = len(combined_context) + 1
        for offset, item in enumerate(image_results):
            item["index"] = base_index + offset
        combined_context.extend(image_results)

    for item in combined_context:
        meta = item.get("meta", {}) or {}
        context_info.append({
            "paper": meta.get("paper_title") or meta.get("paper", "Unknown"),
            "source": meta.get("source", ""),
            "chunk_count": item.get("chunk_count", 0),
            "index": item.get("index", 0),
            "paper_id": meta.get("paper_id"),
            "paper_title": meta.get("paper_title"),
            "kind": meta.get("kind") or "text",
            "figure_number": meta.get("figure_number"),
            "caption": meta.get("caption"),
            "image_path": meta.get("image_path"),
            "page_number": meta.get("page_number"),
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
