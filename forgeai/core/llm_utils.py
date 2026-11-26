"""
LLM Invocation & Logging Utilities
==================================
Provides retry-wrapped LLM invocation and structured logging for ForgeAI.
"""

import logging
import time
from typing import List, Any

logger = logging.getLogger("forgeai")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def invoke_with_retry(
    llm: Any,
    messages: List[Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """Invoke an LLM with exponential backoff retry handling."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1, max_retries, exc, delay
                )
                time.sleep(delay)
    raise last_exc
