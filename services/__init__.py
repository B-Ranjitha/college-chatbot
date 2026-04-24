"""
services/__init__.py
---------------------
Makes `services` a proper Python package.

Public API — import these from anywhere in the project:

    from services import chat_response, build_embeddings

`chat_response`    → the main orchestrator (rule → semantic → LLM)
`build_embeddings` → pre-compute and store FAQ vectors in the DB
`detect_intent`    → classify a query string into a topic category
"""

from services.ai_engine import (   # noqa: F401
    get_response       as chat_response,
    build_embeddings,
    detect_intent,
)

__all__ = [
    "chat_response",
    "build_embeddings",
    "detect_intent",
]

