"""
Compatibility wrapper exposing shared question set services.
"""
from backend.core.questions import (  # noqa: F401
    list_question_sets,
    get_question_set,
    create_question_set,
    update_question_set,
    delete_question_set,
)
