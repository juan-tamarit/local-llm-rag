# src/generation/citations.py
from __future__ import annotations
import re
from .base import ContextChunk, GenerationResult

_CITATION = re.compile(r"\[(S\d+(?:\s*,\s*S\d+)*)\]")


def extract_refs(answer: str) -> list[str]:
    """Referencias citadas, sin duplicados y en orden de aparición."""
    refs: list[str] = []
    for group in _CITATION.findall(answer):
        for ref in re.split(r"\s*,\s*", group):
            if ref not in refs:
                refs.append(ref)
    return refs


def build_result(answer: str, context_chunks: list[ContextChunk]) -> GenerationResult:
    by_ref = {c.ref: c for c in context_chunks}
    cited = extract_refs(answer)
    valid = [r for r in cited if r in by_ref]
    invalid = [r for r in cited if r not in by_ref]
    sources = [
        {
            "ref": r,
            "chunk_id": by_ref[r].chunk_id,
            "source": by_ref[r].source,
            "start_line": by_ref[r].start_line,
            "end_line": by_ref[r].end_line,
        }
        for r in valid
    ]
    uncited = bool(context_chunks) and not valid
    return GenerationResult(
        answer=answer, cited_refs=valid, invalid_refs=invalid,
        sources=sources, context_chunks=context_chunks, uncited=uncited,
    )