# tests/test_generation.py
import pytest
from src.retrieval.base import RetrievalResult
from src.generation.base import Exchange, GenerationConfig
from src.generation.context_builder import build_context
from src.generation.history import select_history
from src.generation.citations import extract_refs, build_result
from src.generation.prompt_builder import build_prompt, PromptTooLongError


def count(text: str) -> int:
    return len(text.split())


def count_messages(msgs: list[dict]) -> int:
    return sum(count(m["content"]) + 5 for m in msgs) + 3


def make_result(i: int, words: int) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=f"c{i}", score=1.0,
        payload={"source": f"f{i}.py", "content_type": "code", "language": "python",
                 "start_line": 1, "end_line": 9, "content": "palabra " * words},
    )


def test_context_respects_max_chunks_and_contiguous_refs():
    results = [make_result(i, 10) for i in range(8)]
    chunks = build_context(results, count, max_tokens=10_000, max_chunks=5)
    assert [c.ref for c in chunks] == ["S1", "S2", "S3", "S4", "S5"]


def test_context_skips_chunk_that_does_not_fit():
    results = [make_result(0, 10), make_result(1, 500), make_result(2, 10)]
    chunks = build_context(results, count, max_tokens=100, max_chunks=5)
    assert [c.chunk_id for c in chunks] == ["c0", "c2"]
    assert [c.ref for c in chunks] == ["S1", "S2"]


def test_history_most_recent_first_and_stops_at_first_misfit():
    ex = [Exchange("a " * 5, "b " * 5), Exchange("c " * 100, "d " * 100), Exchange("e " * 5, "f " * 5)]
    sel = select_history(ex, count, max_tokens=50)
    assert sel == [ex[2]]          # no se salta el intercambio grande para coger el antiguo


def test_extract_refs_variants_and_order():
    assert extract_refs("Usa X [S2], también [S1, S3] y otra vez [S2].") == ["S2", "S1", "S3"]


def test_build_result_flags_invalid_refs():
    chunks = build_context([make_result(0, 5)], count)
    res = build_result("Ver [S1] y [S7].", chunks)
    assert res.cited_refs == ["S1"] and res.invalid_refs == ["S7"]
    assert res.sources[0]["chunk_id"] == "c0"


def test_prompt_fits_global_budget_and_drops_rag_first():
    cfg = GenerationConfig(max_context_tokens=400, max_new_tokens=100,
                           max_rag_tokens=250, max_history_tokens=60)
    results = [make_result(i, 60) for i in range(5)]
    history = [Exchange("hola " * 5, "adios " * 5)]
    parts = build_prompt(system_prompt="sys " * 20, question="que hace X?", history=history,
                         results=results, count_tokens=count, count_messages=count_messages,
                         config=cfg)
    assert parts.prompt_tokens <= 300
    assert parts.history == history            # el historial se conserva
    assert 0 < len(parts.context_chunks) < 5   # el RAG es lo que se recorta


def test_prompt_without_results_uses_marker():
    parts = build_prompt(system_prompt="sys", question="q", history=[], results=[],
                         count_tokens=count, count_messages=count_messages)
    assert "[NO DOCUMENTS RETRIEVED]" in parts.messages[-1]["content"]


def test_question_too_long_raises():
    cfg = GenerationConfig(max_context_tokens=120, max_new_tokens=100)
    with pytest.raises(PromptTooLongError):
        build_prompt(system_prompt="sys", question="palabra " * 200, history=[], results=[],
                     count_tokens=count, count_messages=count_messages, config=cfg)