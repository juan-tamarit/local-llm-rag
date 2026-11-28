"""Métricas de recuperación: Recall@K, Precision@K, MRR@K y nDCG@K.

Funciones puras, sin dependencias del resto del proyecto.

Convenciones:
- `ranked_ids`: lista de `chunk_id` en el orden devuelto por el buscador
  (el primero es el mejor). Los duplicados se ignoran (cuenta la primera aparición).
- `relevance`: diccionario `chunk_id -> grado` con la escala 0-3 de TECH_STACK.md §11.2.
  Un fragmento ausente del diccionario tiene grado 0.
- Un fragmento es "relevante" si su grado es >= `min_grade` (por defecto 1).
- Si una consulta no tiene fragmentos relevantes (p. ej. `answerable=false`),
  las métricas de recuperación no están definidas y se devuelve `None`.
  Los agregadores ignoran los `None`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def _check_k(k: int) -> None:
    if k <= 0:
        raise ValueError(f"k debe ser positivo, recibido {k}")


def _top_k(ranked_ids: Sequence[str], k: int) -> list[str]:
    """Primeros k identificadores distintos, conservando el orden."""
    _check_k(k)
    seen: set[str] = set()
    top: list[str] = []
    for chunk_id in ranked_ids:
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        top.append(chunk_id)
        if len(top) == k:
            break
    return top


def relevant_set(relevance: Mapping[str, int], min_grade: int = 1) -> set[str]:
    return {cid for cid, grade in relevance.items() if grade >= min_grade}


def recall_at_k(
    ranked_ids: Sequence[str],
    relevance: Mapping[str, int],
    k: int = 20,
    min_grade: int = 1,
) -> float | None:
    """Proporción de fragmentos relevantes que aparecen en el top k."""
    relevant = relevant_set(relevance, min_grade)
    if not relevant:
        return None
    hits = sum(1 for cid in _top_k(ranked_ids, k) if cid in relevant)
    return hits / len(relevant)


def precision_at_k(
    ranked_ids: Sequence[str],
    relevance: Mapping[str, int],
    k: int = 5,
    min_grade: int = 1,
) -> float | None:
    """Proporción de resultados relevantes entre los k primeros.

    El denominador es k, no el número de resultados devueltos: un buscador
    que devuelve menos de k resultados (BM25 descarta los de puntuación 0)
    no sale favorecido.
    """
    if not relevant_set(relevance, min_grade):
        return None
    relevant = relevant_set(relevance, min_grade)
    hits = sum(1 for cid in _top_k(ranked_ids, k) if cid in relevant)
    return hits / k


def mrr_at_k(
    ranked_ids: Sequence[str],
    relevance: Mapping[str, int],
    k: int = 20,
    min_grade: int = 1,
) -> float | None:
    """Inverso de la posición (desde 1) del primer relevante dentro del top k; 0 si no hay."""
    relevant = relevant_set(relevance, min_grade)
    if not relevant:
        return None
    for position, cid in enumerate(_top_k(ranked_ids, k), start=1):
        if cid in relevant:
            return 1.0 / position
    return 0.0


def _gain(grade: int) -> float:
    """Ganancia exponencial estándar: 0->0, 1->1, 2->3, 3->7."""
    return float(2 ** max(grade, 0) - 1)


def dcg_at_k(grades: Sequence[int], k: int) -> float:
    _check_k(k)
    return sum(_gain(g) / math.log2(pos + 1) for pos, g in enumerate(grades[:k], start=1))


def ndcg_at_k(
    ranked_ids: Sequence[str],
    relevance: Mapping[str, int],
    k: int = 5,
) -> float | None:
    """nDCG@k con grados 0-3. El ideal ordena todos los grados conocidos de mayor a menor."""
    ideal_grades = sorted((g for g in relevance.values() if g > 0), reverse=True)
    if not ideal_grades:
        return None
    grades = [relevance.get(cid, 0) for cid in _top_k(ranked_ids, k)]
    ideal = dcg_at_k(ideal_grades, k)
    return dcg_at_k(grades, k) / ideal


def evaluate_query(
    ranked_ids: Sequence[str],
    relevance: Mapping[str, int],
    recall_k: int = 20,
    mrr_k: int = 20,
    ndcg_k: int = 5,
    precision_k: int = 5,
) -> dict[str, float | None]:
    """Métricas iniciales de TECH_STACK.md §11.3 para una consulta."""
    return {
        f"recall@{recall_k}": recall_at_k(ranked_ids, relevance, recall_k),
        f"mrr@{mrr_k}": mrr_at_k(ranked_ids, relevance, mrr_k),
        f"ndcg@{ndcg_k}": ndcg_at_k(ranked_ids, relevance, ndcg_k),
        f"precision@{precision_k}": precision_at_k(ranked_ids, relevance, precision_k),
    }


def aggregate(per_query: Sequence[Mapping[str, float | None]]) -> dict[str, dict[str, float | int | None]]:
    """Media por métrica ignorando las consultas donde no está definida.

    Devuelve, por métrica, la media y `n` (consultas que cuentan).
    """
    names: list[str] = []
    for row in per_query:
        for name in row:
            if name not in names:
                names.append(name)
    summary: dict[str, dict[str, float | int | None]] = {}
    for name in names:
        values = [row[name] for row in per_query if row.get(name) is not None]
        summary[name] = {
            "mean": (sum(values) / len(values)) if values else None,
            "n": len(values),
        }
    return summary