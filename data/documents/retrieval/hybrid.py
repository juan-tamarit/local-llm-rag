"""Recuperador híbrido: Qdrant (semántico) + BM25 (léxico) + RRF."""

from typing import Any, Dict, List, Optional

from src.retrieval.base import RetrievalResult
from src.retrieval.bm25_index import BM25Index
from src.retrieval.fusion import reciprocal_rank_fusion


class HybridRetriever:
    """Orquesta Embedder, VectorStore, BM25Index y RRF.

    Expone los tres modos por separado para poder compararlos en la Fase 6.
    Un futuro reranker se aplicaría sobre la salida de `search_hybrid`.
    """

    def __init__(
        self,
        embedder: Any,
        vector_store: Any,
        bm25_index: Optional[BM25Index] = None,
        rrf_k: int = 60,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.bm25_index = bm25_index or BM25Index(vector_store)
        self.rrf_k = rrf_k
        self.weights = weights  # None = pesos iguales

    def refresh(self) -> None:
        """Reconstruye BM25 (llamar tras add_chunks / delete_by_document)."""
        self.bm25_index.refresh()

    def _semantic_raw(self, query: str, limit: int, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        vector = self.embedder.embed_queries(query)[0]
        return self.vector_store.search(vector, limit=limit, filters=filters)

    def search_semantic(
        self, query: str, limit: int = 20, filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        return [
            RetrievalResult(
                chunk_id=h["payload"]["chunk_id"], score=h["score"], payload=h["payload"],
                semantic_rank=i, semantic_score=h["score"],
            )
            for i, h in enumerate(self._semantic_raw(query, limit, filters), start=1)
        ]

    def search_lexical(
        self, query: str, limit: int = 20, filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        return [
            RetrievalResult(
                chunk_id=h["payload"]["chunk_id"], score=h["score"], payload=h["payload"],
                lexical_rank=i, lexical_score=h["score"],
            )
            for i, h in enumerate(self.bm25_index.search(query, limit, filters), start=1)
        ]

    def search_hybrid(
        self,
        query: str,
        limit: int = 20,
        per_retriever: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        semantic = self.search_semantic(query, per_retriever, filters)
        lexical = self.search_lexical(query, per_retriever, filters)

        by_id: Dict[str, RetrievalResult] = {}
        for r in semantic + lexical:
            merged = by_id.setdefault(r.chunk_id, RetrievalResult(r.chunk_id, 0.0, r.payload))
            if r.semantic_rank is not None:
                merged.semantic_rank, merged.semantic_score = r.semantic_rank, r.semantic_score
            if r.lexical_rank is not None:
                merged.lexical_rank, merged.lexical_score = r.lexical_rank, r.lexical_score

        fused = reciprocal_rank_fusion(
            {"semantic": [r.chunk_id for r in semantic], "lexical": [r.chunk_id for r in lexical]},
            k=self.rrf_k, weights=self.weights, limit=limit,
        )
        results = []
        for chunk_id, score in fused:
            by_id[chunk_id].score = score
            results.append(by_id[chunk_id])
        return results
