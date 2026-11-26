"""
LLM Invocation & Logging Utilities
==================================
Provides retry-wrapped LLM invocation, resilient fallback on quota/503 errors,
and structured logging for ForgeAI.
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
    max_retries: int = 2,
    base_delay: float = 1.0,
) -> Any:
    """
    Invoke an LLM with exponential backoff retry handling.
    Falls back to OfflineSimulationChatModel if a cloud provider returns
    rate-limit/quota (429), unavailable (503), or network errors.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as exc:
            last_exc = exc
            err_str = str(exc).lower()
            is_quota_or_unavailable = any(
                tok in err_str for tok in [
                    "429", "resource_exhausted", "503", "unavailable", "rate_limit",
                    "404", "model_not_found", "not_found"
                ]
            )
            if is_quota_or_unavailable:
                logger.warning(
                    "Cloud LLM quota/availability limit hit (%s). Falling back to OfflineSimulationChatModel.",
                    type(exc).__name__,
                )
                from forgeai.core.mock_llm import OfflineSimulationChatModel
                return OfflineSimulationChatModel().invoke(messages)

            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1, max_retries, exc, delay,
                )
                time.sleep(delay)

    if getattr(llm, "_llm_type", "") != "offline_simulation_chat_model":
        logger.warning(
            "Cloud LLM failed after %d attempts (%s). Falling back to OfflineSimulationChatModel.",
            max_retries, last_exc,
        )
        from forgeai.core.mock_llm import OfflineSimulationChatModel
        return OfflineSimulationChatModel().invoke(messages)
    raise last_exc
