"""Modelo de datos común de la capa de recuperación."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class RetrievalResult:
    """Un fragmento recuperado, con su trazabilidad por buscador.

    `score` depende del modo: similitud coseno (semántico), BM25 (léxico)
    o puntuación RRF (híbrido). Los rankings empiezan en 1; None indica que
    el buscador correspondiente no devolvió el fragmento.
    """

    chunk_id: str
    score: float
    payload: Dict[str, Any]
    semantic_rank: Optional[int] = None
    lexical_rank: Optional[int] = None
    semantic_score: Optional[float] = None
    lexical_score: Optional[float] = None

    @property
    def content(self) -> str:
        return self.payload.get("content", "")
