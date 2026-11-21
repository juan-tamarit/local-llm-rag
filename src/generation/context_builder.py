# src/generation/context_builder.py
from __future__ import annotations
from typing import Callable
from src.retrieval.base import RetrievalResult
from .base import ContextChunk
import logging
import re

logger = logging.getLogger(__name__)

_DELIMITERS = re.compile(r"</?(?:context|question)>|\[DOCUMENT\s+S\d+\]", re.IGNORECASE)

# Órdenes triviales dirigidas al modelo (ES/EN). Defensa básica, no infalible.
_INJECTION = re.compile(
    r"\b(?:ignor\w*|olvid\w*|disregard|forget)\b[^.\n]{0,60}"
    r"\b(?:instrucciones|instructions|prompts?|reglas|rules)\b[^.\n]*[.\n]?"
    r"|\b(?:you are now|ahora eres|new instructions|nuevas instrucciones)\b[^.\n]*[.\n]?",
    re.IGNORECASE,
)
REMOVED = "[instruction-like text removed]"


def sanitize(text: str) -> str:
    """Neutraliza delimitadores del prompt y órdenes obvias dentro de un documento (§7.3)."""
    text, n = _INJECTION.subn(REMOVED, text)
    if n:
        logger.warning("Posible inyección en un documento: %d fragmento(s) eliminado(s)", n)
    return _DELIMITERS.sub(lambda m: m.group(0)[0] + "\u200b" + m.group(0)[1:], text)

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
    lines += ["", "Content:", sanitize(payload.get("content", ""))]
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