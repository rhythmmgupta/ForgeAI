"""
ForgeAI Configuration Module
Centralizes all configuration, model selection, and environment setup.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    """Configuration for the LLM provider."""
    provider: str = os.getenv("LLM_PROVIDER", "groq")
    model: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    temperature: float = 0.3
    max_tokens: int = 4096
    groq_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    google_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY"))


@dataclass
class EmbeddingConfig:
    """Configuration for the embedding model."""
    model_name: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    chunk_size: int = 500
    chunk_overlap: int = 100


@dataclass
class BudgetConfig:
    """Token/latency budget for stretch goal: budget enforcement."""
    max_tokens_per_run: int = int(os.getenv("MAX_TOKENS_PER_RUN", "500000"))
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "3"))
    tokens_used: int = 0
    early_stop_threshold: float = 0.02  # Stop if improvement < 2%

    @property
    def budget_remaining(self) -> int:
        return self.max_tokens_per_run - self.tokens_used

    @property
    def budget_exhausted(self) -> bool:
        return self.tokens_used >= self.max_tokens_per_run

    def consume(self, tokens: int):
        self.tokens_used += tokens


@dataclass
class ForgeAIConfig:
    """Master configuration for a ForgeAI run."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    output_dir: Path = Path("output")
    verbose: bool = True


def get_llm(config: LLMConfig):
    """Factory function to create the appropriate LLM instance with resilient fallback."""
    if config.provider in ("mock", "offline", "simulator"):
        from forgeai.core.mock_llm import OfflineSimulationChatModel
        return OfflineSimulationChatModel()

    if config.provider == "groq":
        if not config.groq_api_key or config.groq_api_key == "your_groq_api_key_here":
            from forgeai.core.mock_llm import OfflineSimulationChatModel
            return OfflineSimulationChatModel()
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                api_key=config.groq_api_key,
                timeout=30.0,
                max_retries=1,
            )
        except Exception:
            from forgeai.core.mock_llm import OfflineSimulationChatModel
            return OfflineSimulationChatModel()

    elif config.provider == "gemini":
        if not config.google_api_key or config.google_api_key == "your_google_api_key_here":
            from forgeai.core.mock_llm import OfflineSimulationChatModel
            return OfflineSimulationChatModel()
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=config.model,
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
                google_api_key=config.google_api_key,
                request_timeout=30.0,
                retries=1,
            )
        except Exception:
            from forgeai.core.mock_llm import OfflineSimulationChatModel
            return OfflineSimulationChatModel()
    else:
        from forgeai.core.mock_llm import OfflineSimulationChatModel
        return OfflineSimulationChatModel()


try:
    from langchain_core.embeddings import Embeddings as _BaseEmbeddings
except ImportError:
    _BaseEmbeddings = object


class LocalDeterministicEmbeddings(_BaseEmbeddings):
    """
    Lightweight, robust embeddings based on character/word hashing and n-grams.
    Zero-network dependency, completely offline-compatible, and produces fixed-length
    normalized 384-dimensional vectors compatible with FAISS.
    """
    def __init__(self, dim: int = 384):
        self.dim = dim

    def __call__(self, text: str) -> List[float]:
        return self.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        import hashlib
        import math
        vec = [0.0] * self.dim
        tokens = text.lower().split()
        if not tokens:
            return vec
        for i, word in enumerate(tokens):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % self.dim
            vec[idx] += 1.0 + (1.0 / (i + 1.0))
        # Normalize L2
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


def get_embeddings(config: EmbeddingConfig):
    """Factory function to create the embedding model with offline fallback."""
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        emb = HuggingFaceEmbeddings(
            model_name=config.model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        emb.embed_query("test")
        return emb
    except Exception:
        return LocalDeterministicEmbeddings(dim=384)
