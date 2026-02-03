"""
Smart chunking strategy for text blocks.

Handles:
- Combining small blocks
- Splitting large blocks
- Maintaining block metadata through chunking
"""
from typing import List, Dict, Any


def chunk_text_blocks(
    blocks: List[Dict[str, Any]],
    target_size: int = 1000,
    overlap: int = 200,
    min_chunk_size: int = 100
) -> List[Dict[str, Any]]:
    """
    Smart chunking that respects block boundaries.
    
    Strategy:
    1. If a block is smaller than target_size, try to combine with adjacent blocks
    2. If a block is larger than target_size, split it with overlap
    3. Always maintain block metadata (page_no, block_index, bbox)
    
    Args:
        blocks: List of text blocks from extract_text_blocks()
        target_size: Target chunk size in characters
        overlap: Overlap between chunks in characters
        min_chunk_size: Minimum chunk size (discard smaller)
    
    Returns:
        List of chunks with metadata
    """
    if not blocks:
        return []
    
    chunks = []
    current_chunk = ""
    current_metadata = []
    
    for i, block in enumerate(blocks):
        text = block["text"]
        
        # If adding this block would exceed target size, finalize current chunk
        if current_chunk and len(current_chunk) + len(text) > target_size:
            if len(current_chunk) >= min_chunk_size:
                chunks.append({
                    "text": current_chunk.strip(),
                    "page_no": current_metadata[0]["page_no"],
                    "block_index": current_metadata[0]["block_index"],
                    "bbox": current_metadata[0]["bbox"],
                    "metadata": {
                        "blocks": current_metadata,
                        "chunk_type": "combined" if len(current_metadata) > 1 else "single"
                    }
                })
            
            # Start new chunk with overlap
            if overlap > 0 and len(current_chunk) > overlap:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + " " + text
                current_metadata = [block]
            else:
                current_chunk = text
                current_metadata = [block]
        else:
            # Add to current chunk
            if current_chunk:
                current_chunk += " " + text
            else:
                current_chunk = text
            current_metadata.append(block)
        
        # If current block is very large, split it
        if len(text) > target_size * 1.5:
            # Split large block into smaller chunks
            split_chunks = _split_large_text(
                text,
                block,
                target_size,
                overlap,
                min_chunk_size
            )
            chunks.extend(split_chunks)
            current_chunk = ""
            current_metadata = []
    
    # Add final chunk
    if current_chunk and len(current_chunk) >= min_chunk_size:
        chunks.append({
            "text": current_chunk.strip(),
            "page_no": current_metadata[0]["page_no"],
            "block_index": current_metadata[0]["block_index"],
            "bbox": current_metadata[0]["bbox"],
            "metadata": {
                "blocks": current_metadata,
                "chunk_type": "combined" if len(current_metadata) > 1 else "single"
            }
        })
    
    return chunks


def _split_large_text(
    text: str,
    block: Dict[str, Any],
    target_size: int,
    overlap: int,
    min_chunk_size: int
) -> List[Dict[str, Any]]:
    """
    Split a large text block into smaller chunks with overlap.
    
    Args:
        text: Text to split
        block: Original block metadata
        target_size: Target chunk size
        overlap: Overlap between chunks
        min_chunk_size: Minimum chunk size
    
    Returns:
        List of chunk dictionaries
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + target_size
        
        # If this is not the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence end within last 200 chars
            search_start = max(start, end - 200)
            for delimiter in [". ", ".\n", "! ", "?\n", "? "]:
                pos = text.rfind(delimiter, search_start, end)
                if pos != -1:
                    end = pos + 1
                    break
        
        chunk_text = text[start:end].strip()
        
        if len(chunk_text) >= min_chunk_size:
            chunks.append({
                "text": chunk_text,
                "page_no": block["page_no"],
                "block_index": block["block_index"],
                "bbox": block["bbox"],
                "metadata": {
                    "blocks": [block],
                    "chunk_type": "split",
                    "split_index": len(chunks)
                }
            })
        
        # Move start position with overlap
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


def simple_chunk_blocks(
    blocks: List[Dict[str, Any]],
    max_chars: int = 1200
) -> List[Dict[str, Any]]:
    """
    Simple chunking: combine blocks until max_chars is reached.
    
    This is a simpler alternative to chunk_text_blocks() that just combines
    blocks without splitting large ones.
    
    Args:
        blocks: List of text blocks
        max_chars: Maximum characters per chunk
    
    Returns:
        List of chunks
    """
    if not blocks:
        return []
    
    chunks = []
    current_chunk = ""
    current_blocks = []
    
    for block in blocks:
        text = block["text"]
        
        # If adding this block exceeds max_chars, finalize current chunk
        if current_chunk and len(current_chunk) + len(text) > max_chars:
            chunks.append({
                "text": current_chunk.strip(),
                "page_no": current_blocks[0]["page_no"],
                "block_index": current_blocks[0]["block_index"],
                "bbox": current_blocks[0]["bbox"],
                "metadata": {
                    "blocks": current_blocks,
                    "chunk_type": "combined" if len(current_blocks) > 1 else "single"
                }
            })
            current_chunk = text
            current_blocks = [block]
        else:
            # Add to current chunk
            if current_chunk:
                current_chunk += " " + text
            else:
                current_chunk = text
            current_blocks.append(block)
    
    # Add final chunk
    if current_chunk:
        chunks.append({
            "text": current_chunk.strip(),
            "page_no": current_blocks[0]["page_no"],
            "block_index": current_blocks[0]["block_index"],
            "bbox": current_blocks[0]["bbox"],
            "metadata": {
                "blocks": current_blocks,
                "chunk_type": "combined" if len(current_blocks) > 1 else "single"
            }
        })
    
    return chunks
