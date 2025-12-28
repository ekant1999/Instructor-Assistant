from typing import List, Dict, TypedDict
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
import os


class GraphState(TypedDict):
    """State structure for the RAG workflow graph."""
    question: str
    context: List[Dict]
    answer: str


def retrieve_node(state: GraphState, vectorstore: FAISS, k: int = 6) -> Dict:
    """Retrieve relevant document chunks from vectorstore based on the question. Groups chunks by paper and deduplicates."""
    question = state["question"]
    docs = vectorstore.similarity_search(question, k=k)

    paper_to_chunks = {}
    seen_texts = set()

    for doc in docs:
        text_key = doc.page_content[:100]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        paper_name = doc.metadata.get("paper", "Unknown")
        if paper_name not in paper_to_chunks:
            paper_to_chunks[paper_name] = []

        paper_to_chunks[paper_name].append({
            "text": doc.page_content,
            "meta": doc.metadata
        })

    context = []
    index = 1
    for paper_name, chunks in paper_to_chunks.items():
        combined_text = "\n\n".join([chunk["text"] for chunk in chunks])
        context.append({
            "text": combined_text,
            "meta": chunks[0]["meta"],
            "index": index,
            "chunk_count": len(chunks)
        })
        index += 1

    return {"context": context}


def generate_node(state: GraphState, llm) -> Dict:
    """Generate answer from retrieved context using LLM. Formats prompt with citations and handles errors gracefully."""
    question = state["question"]
    context = state["context"]

    context_text = "\n\n".join([
        f"[{item['index']}] {item['text']}"
        for item in context
    ])

    # Format sources list for error message
    sources_list = "\n".join([
        f"[{item['index']}] {item['meta'].get('paper', 'Unknown')} ({item.get('chunk_count', 0)} chunks)"
        for item in context
    ])

    system_prompt = """You are a helpful research assistant. Answer the question based ONLY on the provided context. 
Always include numbered citations [1], [2], etc. that correspond to the source numbers in the context.
If information is not in the context, say so explicitly.
Format your answer clearly with proper citations."""

    user_prompt = f"""Context:

{context_text}

Question: {question}

Answer:"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

    try:
        response = llm.invoke(messages)

        if hasattr(response, 'content'):
            answer = response.content
        elif isinstance(response, str):
            answer = response
        elif hasattr(response, 'text'):
            answer = response.text
        else:
            answer = str(response)

        if not answer or answer.strip() == "":
            raise ValueError("Empty response from LLM")

    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        import traceback
        traceback.print_exc()
        
        # Provide a helpful error message with the retrieved sources
        answer = f"I apologize, but I encountered an error while generating an answer. The system successfully retrieved relevant sources from your PDFs, but the language model had trouble generating a response.\n\n**Error details:** {error_msg}\n\n**Retrieved Sources ({len(context)}):**\n{sources_list}\n\n**You can try:**\n1. Make sure the browser window opened and you're logged into ChatGPT\n2. If the browser didn't open, uncheck 'Show browser window' and check it again, then try the query\n3. Try refreshing the browser window and logging in again\n4. The ChatGPT web interface may have changed - the selectors may need updating\n\n**Retrieved Context:**\n\nThe following context was retrieved from your PDFs. You can read it directly:\n\n{context_text[:2000]}{'...' if len(context_text) > 2000 else ''}"

    return {"answer": answer}


def create_graph(vectorstore: FAISS, llm, k: int = 6) -> StateGraph:
    """Create LangGraph workflow: retrieve → generate. Returns compiled graph ready for execution."""
    workflow = StateGraph(GraphState)

    def retrieve_wrapper(state: GraphState):
        return retrieve_node(state, vectorstore, k=k)

    def generate_wrapper(state: GraphState):
        return generate_node(state, llm)

    workflow.add_node("retrieve", retrieve_wrapper)
    workflow.add_node("generate", generate_wrapper)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


def get_llm(**kwargs):
    """Create and return ChatGPT Web LLM instance. Configures headless mode and timeout from kwargs or environment."""
    try:
        from .chatgpt_web import ChatGPTWebLLM
    except ImportError as e:
        error_msg = str(e)
        if "playwright" in error_msg.lower():
            raise ValueError(
                "ChatGPT Web integration requires playwright. "
                "Install it with: pip install playwright && playwright install chromium"
            )
        else:
            raise ValueError(
                f"Failed to import ChatGPT Web integration: {error_msg}. "
                "Make sure playwright is installed: pip install playwright && playwright install chromium"
            )
    except Exception as e:
        raise ValueError(
            f"Failed to initialize ChatGPT Web integration: {str(e)}. "
            "Make sure playwright is installed: pip install playwright && playwright install chromium"
        )

    # Default to headless=False so browser window opens for login
    headless = kwargs.get("headless", os.getenv("CHATGPT_HEADLESS", "false").lower() == "true")
    timeout = kwargs.get("timeout", 120000)  # Increased default timeout to 120 seconds

    try:
        return ChatGPTWebLLM(headless=headless, timeout=timeout)
    except Exception as e:
        raise ValueError(
            f"Failed to create ChatGPT Web LLM instance: {str(e)}. "
            "Make sure playwright is installed: pip install playwright && playwright install chromium"
        )


def load_vectorstore(index_dir: str = "index/") -> FAISS:
    """Load FAISS vectorstore from disk. Uses Hugging Face embeddings (same as ingestion) to ensure compatibility."""
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except ImportError:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            raise ValueError(
                "HuggingFaceEmbeddings not found. Please install langchain-community or langchain-huggingface: "
                "pip install langchain-community"
            )

    try:
        # Get model name, but ensure it's a valid Hugging Face model
        env_model = os.getenv("EMBEDDING_MODEL", "")
        # If it's an OpenAI model name, use the default Hugging Face model instead
        if env_model and ("text-embedding" in env_model.lower() or "ada" in env_model.lower()):
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
        else:
            model_name = env_model or "sentence-transformers/all-MiniLM-L6-v2"
        
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'}
        )
    except Exception as e:
        raise ValueError(
            f"Failed to initialize Hugging Face embeddings: {e}. "
            "Please check that the model name is correct and you have the required dependencies installed."
        )

    vectorstore = FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)
    return vectorstore

