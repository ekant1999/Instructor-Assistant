import os
import logging
from pathlib import Path
from typing import List
import pickle

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain_core.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        raise ImportError("HuggingFaceEmbeddings not found. Please install langchain-community or langchain-huggingface.")

load_dotenv()

logger = logging.getLogger(__name__)


def load_pdfs(papers_dir: str) -> List:
    """Load all PDF files from the papers directory. Extracts text and metadata from each PDF."""
    papers_path = Path(papers_dir)
    # If relative path, resolve relative to project root (3 levels up from this file: rag -> backend -> webapp -> project_root)
    if not papers_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        papers_path = backend_root / papers_dir
    if not papers_path.exists():
        papers_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {papers_path}")
        return []

    documents = []
    pdf_files = list(papers_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDF files found in {papers_dir}")
        return []

    logger.info(f"Found {len(pdf_files)} PDF file(s)")

    for pdf_file in pdf_files:
        try:
            logger.info(f"Loading: {pdf_file.name}")
            loader = PyPDFLoader(str(pdf_file))
            pages = loader.load()

            for page in pages:
                page.metadata["paper"] = pdf_file.stem
                page.metadata["source"] = str(pdf_file)

            documents.extend(pages)
            logger.info(f"  Loaded {len(pages)} pages")
        except Exception as e:
            logger.error(f"  Error loading {pdf_file.name}: {e}")
            raise ValueError(f"Failed to load PDF {pdf_file.name}: {e}") from e

    return documents


def load_pdfs_from_paths(pdf_paths: List[str]) -> List:
    """Load PDF files from explicit file paths."""
    documents = []
    if not pdf_paths:
        return documents

    for pdf_path in pdf_paths:
        path = Path(pdf_path).expanduser().resolve()
        if not path.exists():
            logger.warning(f"PDF not found: {path}")
            continue
        try:
            logger.info(f"Loading: {path.name}")
            loader = PyPDFLoader(str(path))
            pages = loader.load()

            for page in pages:
                page.metadata["paper"] = path.stem
                page.metadata["source"] = str(path)

            documents.extend(pages)
            logger.info(f"  Loaded {len(pages)} pages")
        except Exception as e:
            logger.error(f"  Error loading {path.name}: {e}")
            raise ValueError(f"Failed to load PDF {path.name}: {e}") from e

    if not documents:
        logger.warning("No valid PDF files were loaded from provided paths")
    return documents


def split_documents(documents: List, chunk_size: int = 1200, chunk_overlap: int = 200) -> List:
    """Split documents into smaller chunks for embedding. Uses recursive character splitting with overlap."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    chunks = text_splitter.split_documents(documents)
    logger.info(f"Split into {len(chunks)} chunks")
    return chunks


def create_faiss_index(chunks: List, index_dir: str = "index/"):
    """Create FAISS vectorstore from chunks. Generates embeddings and saves index to disk with metadata."""
    if not chunks:
        logger.warning("No chunks to index")
        return

    # Resolve index directory relative to project root if not absolute
    index_path = Path(index_dir)
    if not index_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[1]
        index_path = backend_root / index_dir
    index_dir = str(index_path)

    logger.info("Creating embeddings...")

    try:
        # Get model name, but ensure it's a valid Hugging Face model
        env_model = os.getenv("EMBEDDING_MODEL", "")
        # If it's an OpenAI model name, use the default Hugging Face model instead
        if env_model and ("text-embedding" in env_model.lower() or "ada" in env_model.lower()):
            logger.warning(f"EMBEDDING_MODEL is set to '{env_model}' which is not a Hugging Face model. Using default Hugging Face model instead.")
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
        else:
            model_name = env_model or "sentence-transformers/all-MiniLM-L6-v2"
        
        logger.info(f"Using Hugging Face embeddings: {model_name}")
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'}
        )
        logger.info("✓ Hugging Face embeddings initialized")
    except Exception as e:
        error_msg = f"Error initializing Hugging Face embeddings: {e}"
        logger.error(error_msg)
        raise ValueError(f"{error_msg}. Please check that the model name is correct and you have the required dependencies installed.") from e

    logger.info("Building FAISS index...")
    logger.info(f"  This may take a few minutes for {len(chunks)} chunks...")
    try:
        vectorstore = FAISS.from_documents(chunks, embeddings)
    except Exception as e:
        error_msg = f"Error creating FAISS index: {e}"
        logger.error(error_msg)
        raise ValueError(f"{error_msg}. Please check your configuration and try again.") from e

    index_path = Path(index_dir)
    index_path.mkdir(parents=True, exist_ok=True)

    try:
        vectorstore.save_local(str(index_path))
        logger.info(f"✓ Saved FAISS index to {index_dir}")

        metadata_file = index_path / "metadata.pkl"
        metadata = [{"text": chunk.page_content, "meta": chunk.metadata} for chunk in chunks]
        with open(metadata_file, "wb") as f:
            pickle.dump(metadata, f)
        logger.info(f"✓ Saved metadata to {metadata_file}")
    except Exception as e:
        error_msg = f"Error saving index: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def main():
    """Main ingestion pipeline: load PDFs, split into chunks, create and save FAISS index."""
    backend_root = Path(__file__).resolve().parents[1]
    papers_dir = str(backend_root / "data" / "pdfs")
    index_dir = str(backend_root / "index")

    print("=" * 50)
    print("PDF Ingestion Pipeline")
    print("=" * 50)

    documents = load_pdfs(papers_dir)

    if not documents:
        print("No documents to process. Please add PDF files to data/papers/")
        return

    chunks = split_documents(documents, chunk_size=1200, chunk_overlap=200)
    create_faiss_index(chunks, index_dir=index_dir)

    print("=" * 50)
    print("✓ Ingestion complete!")
    print("=" * 50)
    print("\nYou can now start the server and ask questions!")
    print("Run: python server.py")


if __name__ == "__main__":
    main()
