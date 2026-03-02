from __future__ import annotations

"""
Compatibility wrapper for keyword search helpers.

Backend code delegates search logic to the reusable Phase 1 package (`ia_phase1`).
"""

try:
    from backend.core.phase1_runtime import ensure_ia_phase1_on_path
except ImportError:
    from core.phase1_runtime import ensure_ia_phase1_on_path

ensure_ia_phase1_on_path()

from ia_phase1.search_keyword import (  # noqa: E402
    SearchType,
    configure_connection_factory,
    search_all,
    search_notes,
    search_papers,
    search_sections,
    search_summaries,
)

try:  # noqa: E402
    from backend.core.database import get_conn
except ImportError:  # noqa: E402
    from core.database import get_conn

configure_connection_factory(get_conn)

__all__ = [
    "SearchType",
    "search_papers",
    "search_sections",
    "search_notes",
    "search_summaries",
    "search_all",
]
