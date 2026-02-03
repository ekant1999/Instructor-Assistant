"""
LangGraph workflow for pgvector-based RAG (replaces FAISS-based graph.py).

Simplified workflow since retrieval is handled by pgvector/hybrid search.
"""
import os
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage


async def generate_answer(
    question: str,
    context: List[Dict[str, Any]],
    llm
) -> str:
    """
    Generate answer from retrieved context using LLM.
    
    Args:
        question: User question
        context: List of context items with text and metadata
        llm: LLM instance
    
    Returns:
        Generated answer string
    """
    # Format context with citations
    context_text = "\n\n".join([
        f"[{item['index']}] {item['text']}"
        for item in context
    ])
    
    # Format sources list for error message
    sources_list = "\n".join([
        f"[{item['index']}] {item['meta'].get('paper_title', 'Unknown')} "
        f"(Page {item['meta'].get('page_number', '?')}, Block {item['meta'].get('block_index', '?')})"
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
        
        return answer
    
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        import traceback
        traceback.print_exc()
        
        # Provide a helpful error message with the retrieved sources
        answer = f"""I apologize, but I encountered an error while generating an answer. The system successfully retrieved relevant sources from your PDFs, but the language model had trouble generating a response.

**Error details:** {error_msg}

**Retrieved Sources ({len(context)}):**
{sources_list}

**You can try:**
1. Make sure the browser window opened and you're logged into ChatGPT
2. If the browser didn't open, uncheck 'Show browser window' and check it again, then try the query
3. Try refreshing the browser window and logging in again
4. The ChatGPT web interface may have changed - the selectors may need updating

**Retrieved Context:**

The following context was retrieved from your PDFs. You can read it directly:

{context_text[:2000]}{'...' if len(context_text) > 2000 else ''}"""
        
        return answer


def get_llm(**kwargs):
    """Create and return ChatGPT Web LLM instance."""
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
    
    # Default to headless=False so browser window opens for login
    headless = kwargs.get("headless", os.getenv("CHATGPT_HEADLESS", "false").lower() == "true")
    timeout = kwargs.get("timeout", 120000)  # 120 seconds
    
    try:
        return ChatGPTWebLLM(headless=headless, timeout=timeout)
    except Exception as e:
        raise ValueError(
            f"Failed to create ChatGPT Web LLM instance: {str(e)}. "
            "Make sure playwright is installed: pip install playwright && playwright install chromium"
        )
