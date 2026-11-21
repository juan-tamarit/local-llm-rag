"""Recuperación semántica, léxica e híbrida (Fase 4)."""

from src.retrieval.base import RetrievalResult
from src.retrieval.bm25_index import BM25Index
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.hybrid import HybridRetriever

__all__ = ["RetrievalResult", "BM25Index", "HybridRetriever", "reciprocal_rank_fusion"]
