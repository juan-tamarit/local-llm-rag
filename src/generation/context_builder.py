# src/generation/context_builder.py
from __future__ import annotations
from typing import Callable
from src.retrieval.base import RetrievalResult
from .base import ContextChunk


def format_chunk(ref: str, payload: dict) -> str:
    lines = [f"[DOCUMENT {ref}]", f"Source: {payload.get('source', '')}"]
    ctype = payload.get("content_type")
    if ctype:
        lines.append(f"Type: {ctype}")
    if payload.get("language"):
        lines.append(f"Language: {payload['language']}")
    if payload.get("parent"):
        lines.append(f"Parent: {payload['parent']}")
    if payload.get("section"):
        key = "Element" if ctype == "code" else "Section"
        lines.append(f"{key}: {payload['section']}")
    start, end = payload.get("start_line"), payload.get("end_line")
    if start is not None and end is not None:
        lines.append(f"Lines: {start}-{end}")
    lines += ["", "Content:", payload.get("content", "")]
    return "\n".join(lines)


def build_context(
    results: list[RetrievalResult],
    count_tokens: Callable[[str], int],
    max_tokens: int = 2500,
    max_chunks: int = 5,
) -> list[ContextChunk]:
    """Selecciona fragmentos en orden RRF dentro del presupuesto.
    Si un fragmento no cabe, se descarta y se prueba con el siguiente."""
    selected: list[ContextChunk] = []
    used = 0
    for r in results:
        if len(selected) >= max_chunks:
            break
        ref = f"S{len(selected) + 1}"
        text = format_chunk(ref, r.payload)
        n = count_tokens(text)
        if used + n > max_tokens:
            continue
        selected.append(ContextChunk(
            ref=ref, chunk_id=r.chunk_id, text=text, tokens=n,
            source=r.payload.get("source", ""),
            start_line=r.payload.get("start_line"),
            end_line=r.payload.get("end_line"),
        ))
        used += n
    return selected