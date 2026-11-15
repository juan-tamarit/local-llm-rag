"""Índice léxico BM25 en memoria, construido a partir de VectorStore."""

import logging
import os
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
from rank_bm25 import BM25Okapi

from src.retrieval.tokenizer import tokenize

logger = logging.getLogger(__name__)


def _searchable_text(payload: Dict[str, Any]) -> str:
    """Contenido + metadatos que ayudan a localizar identificadores."""
    source = payload.get("source") or ""
    parts = [
        payload.get("content") or "",
        payload.get("parent") or "",
        payload.get("section") or "",
        os.path.basename(source),
    ]
    return "\n".join(p for p in parts if p)


class BM25Index:
    """BM25Okapi sobre los payloads de la colección.

    Los filtros se aplican tras puntuar (el IDF se calcula sobre todo el
    corpus), por lo que son exactos y consistentes con los de Qdrant
    (igualdad por campo del payload).
    """

    def __init__(self, vector_store: Any):
        self.vector_store = vector_store
        self._payloads: List[Dict[str, Any]] = []
        self._bm25: Optional[BM25Okapi] = None
        self.refresh()

    def __len__(self) -> int:
        return len(self._payloads)

    def refresh(self) -> None:
        """Reconstruye el índice desde el almacén vectorial."""
        unique: Dict[str, Dict[str, Any]] = {}
        for point in self.vector_store.scroll_all():
            payload = point["payload"]
            unique[payload["chunk_id"]] = payload  # dedup por chunk_id
        self._payloads = list(unique.values())
        if self._payloads:
            self._bm25 = BM25Okapi([tokenize(_searchable_text(p)) for p in self._payloads])
        else:
            self._bm25 = None
        logger.info("Índice BM25 construido con %d chunks.", len(self._payloads))

    def ensure_fresh(self) -> None:
        """Reconstruye si el número de chunks difiere del de Qdrant.

        Limitación: no detecta cambios que mantengan el recuento (p. ej. borrar
        un documento y añadir otro con los mismos chunks). Tras reindexar,
        llama a refresh() explícitamente.
        """
        if self.vector_store.count() != len(self._payloads):
            self.refresh()

    def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Devuelve [{'id', 'score', 'payload'}] igual que VectorStore.search."""
        self.ensure_fresh()
        tokens = tokenize(query)
        if self._bm25 is None or not tokens:
            return []

        scores = np.asarray(self._bm25.get_scores(tokens), dtype=float)
        if filters:
            mask = np.array(
                [all(p.get(k) == v for k, v in filters.items()) for p in self._payloads]
            )
            scores = np.where(mask, scores, -np.inf)

        order = np.argsort(-scores, kind="stable")
        results: List[Dict[str, Any]] = []
        for idx in order[:limit]:
            if scores[idx] <= 0:  # sin coincidencia léxica (o excluido por filtro)
                break
            payload = self._payloads[idx]
            results.append(
                {"id": payload["chunk_id"], "score": float(scores[idx]), "payload": payload}
            )
        return results
