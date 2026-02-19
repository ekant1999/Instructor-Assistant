from __future__ import annotations

"""
Compatibility wrapper for chunking utilities.

Backend code now delegates to the reusable Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.chunking import chunk_text_blocks, simple_chunk_blocks

__all__ = [
    "chunk_text_blocks",
    "simple_chunk_blocks",
]
