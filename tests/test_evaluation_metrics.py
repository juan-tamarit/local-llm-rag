"""Pruebas de src/evaluation/metrics.py (sin GPU ni modelos)."""

import math

import pytest

from src.evaluation.metrics import (
    aggregate,
    evaluate_query,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)

REL = {"a": 3, "b": 2, "c": 1, "z": 0}


def test_recall_all_found():
    assert recall_at_k(["a", "x", "b", "c"], REL, k=20) == 1.0


def test_recall_partial_and_cutoff():
    assert recall_at_k(["a", "x", "y"], REL, k=20) == pytest.approx(1 / 3)
    # b y c quedan fuera del corte k=2
    assert recall_at_k(["a", "x", "b", "c"], REL, k=2) == pytest.approx(1 / 3)


def test_grade_zero_is_not_relevant():
    assert recall_at_k(["z"], REL, k=5) == 0.0


def test_undefined_without_relevant_chunks():
    empty = {"z": 0}
    assert recall_at_k(["a"], empty) is None
    assert mrr_at_k(["a"], empty) is None
    assert ndcg_at_k(["a"], empty) is None
    assert precision_at_k(["a"], empty) is None
    assert recall_at_k(["a"], {}) is None


def test_mrr_positions():
    assert mrr_at_k(["a"], REL) == 1.0
    assert mrr_at_k(["x", "y", "c"], REL) == pytest.approx(1 / 3)
    assert mrr_at_k(["x", "y"], REL) == 0.0
    assert mrr_at_k(["x", "y", "a"], REL, k=2) == 0.0


def test_precision_denominator_is_k():
    # Solo 2 resultados devueltos: el denominador sigue siendo k=5
    assert precision_at_k(["a", "b"], REL, k=5) == pytest.approx(2 / 5)


def test_ndcg_perfect_order_is_one():
    assert ndcg_at_k(["a", "b", "c"], REL, k=5) == pytest.approx(1.0)


def test_ndcg_penalizes_bad_order():
    perfect = ndcg_at_k(["a", "b", "c"], REL, k=5)
    swapped = ndcg_at_k(["c", "b", "a"], REL, k=5)
    assert 0 < swapped < perfect


def test_ndcg_known_value():
    rel = {"a": 1, "b": 1}
    # ranking [x, a, b]: DCG = 1/log2(3) + 1/log2(4); ideal = 1/log2(2) + 1/log2(3)
    expected = (1 / math.log2(3) + 1 / math.log2(4)) / (1 / math.log2(2) + 1 / math.log2(3))
    assert ndcg_at_k(["x", "a", "b"], rel, k=5) == pytest.approx(expected)


def test_duplicates_are_ignored():
    # El segundo "a" no ocupa posición ni cuenta dos veces
    assert recall_at_k(["a", "a", "a"], REL, k=3) == pytest.approx(1 / 3)
    assert mrr_at_k(["x", "x", "a"], REL) == pytest.approx(1 / 2)


def test_invalid_k():
    with pytest.raises(ValueError):
        recall_at_k(["a"], REL, k=0)
    with pytest.raises(ValueError):
        ndcg_at_k(["a"], REL, k=-1)


def test_evaluate_query_keys():
    result = evaluate_query(["a", "x"], REL)
    assert set(result) == {"recall@20", "mrr@20", "ndcg@5", "precision@5"}


def test_aggregate_skips_undefined():
    rows = [
        {"recall@20": 1.0, "mrr@20": 1.0},
        {"recall@20": 0.0, "mrr@20": 0.5},
        {"recall@20": None, "mrr@20": None},  # consulta sin respuesta documental
    ]
    summary = aggregate(rows)
    assert summary["recall@20"] == {"mean": 0.5, "n": 2}
    assert summary["mrr@20"] == {"mean": 0.75, "n": 2}


def test_aggregate_all_none():
    assert aggregate([{"x": None}]) == {"x": {"mean": None, "n": 0}}