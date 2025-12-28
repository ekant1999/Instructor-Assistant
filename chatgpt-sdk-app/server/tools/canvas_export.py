"""
Compatibility wrapper for Canvas markdown helpers which are shifted in backend.core.questions
"""
from backend.core.questions import (  # noqa: F401
    save_canvas_md_for_set,
    render_canvas_markdown,
)
