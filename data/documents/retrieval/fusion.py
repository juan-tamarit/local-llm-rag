"""Reciprocal Rank Fusion. Funciones puras, sin dependencias del proyecto."""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple


def reciprocal_rank_fusion(
    rankings: Dict[str, List[str]],
    k: int = 60,
    weights: Optional[Dict[str, float]] = None,
    limit: int = 20,
) -> List[Tuple[str, float]]:
    """Fusiona rankings {nombre: [chunk_id, ...]} (mejor primero).

    RRF(d) = sum_r w_r / (k + rank_r(d)), con rank empezando en 1.
    Devuelve [(chunk_id, score)] ordenado por score descendente.
    """
    if k <= 0:
        raise ValueError("k debe ser positivo.")
    scores: Dict[str, float] = defaultdict(float)
    for name, ids in rankings.items():
        weight = (weights or {}).get(name, 1.0)
        seen = set()
        for rank, chunk_id in enumerate(ids, start=1):
            if chunk_id in seen:  # un buscador no debe puntuar dos veces el mismo chunk
                continue
            seen.add(chunk_id)
            scores[chunk_id] += weight / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
