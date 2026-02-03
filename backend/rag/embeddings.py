"""
Embedding service for generating vector embeddings using sentence-transformers.

Uses all-mpnet-base-v2 (768D) for better semantic understanding compared to all-MiniLM-L6-v2 (384D).
"""
import os
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self, model_name: str = None, device: str = None):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Model name (default: all-mpnet-base-v2 from env or hardcoded)
            device: Device to use ('cpu', 'cuda', or None for auto)
        """
        # Get model name from env or use default
        if model_name is None:
            model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
        
        # Get device from env or parameter
        if device is None:
            device = os.getenv("EMBEDDING_DEVICE", "cpu")
        
        print(f"Loading embedding model: {model_name} on {device}")
        self.model = SentenceTransformer(model_name, device=device)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.model_name = model_name
        
        print(f"✓ Embedding model loaded (dimension: {self.dimension})")
    
    def embed_texts(self, texts: List[str], show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of text strings to embed
            show_progress: Whether to show progress bar
        
        Returns:
            numpy array of shape (len(texts), dimension)
        """
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(
            texts,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        return embeddings
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query.
        
        Args:
            query: Query text string
        
        Returns:
            numpy array of shape (dimension,)
        """
        embedding = self.model.encode(
            [query],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )[0]
        
        return embedding
    
    def embed_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text (alias for embed_query).
        
        Args:
            text: Text string
        
        Returns:
            numpy array of shape (dimension,)
        """
        return self.embed_query(text)


# Global singleton instance
_embedding_service: EmbeddingService = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
