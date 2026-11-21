# src/generation/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    PROGRAMMER = "programmer"
    CONSULTANT = "consultant"


@dataclass(frozen=True)
class GenerationConfig:
    max_context_tokens: int = 4096      # presupuesto global del modelo
    max_rag_tokens: int = 2500
    max_rag_chunks: int = 5
    max_history_tokens: int = 500
    max_new_tokens: int = 512           # reserva para la respuesta


@dataclass(frozen=True)
class ContextChunk:
    ref: str                  # "S1", "S2"... (temporal)
    chunk_id: str             # persistente
    text: str                 # bloque formateado [DOCUMENT S1] ... Content: ...
    tokens: int
    source: str
    start_line: int | None = None
    end_line: int | None = None


@dataclass
class GenerationResult:
    answer: str
    cited_refs: list[str] = field(default_factory=list)
    invalid_refs: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    context_chunks: list[ContextChunk] = field(default_factory=list)