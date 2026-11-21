# src/generation/pipeline.py
from __future__ import annotations
from typing import Iterator

from src.retrieval.hybrid import HybridRetriever
from .base import Exchange, GenerationConfig, GenerationResult, Mode
from .citations import build_result
from .llm import LLM
from .prompt_builder import build_prompt
from .prompts import build_system_prompt
from .token_counter import TokenCounter


class RAGGenerator:
    """Consulta -> retrieval -> prompt -> LLM -> respuesta con referencias validadas."""

    def __init__(self, retriever: HybridRetriever, llm: LLM, counter: TokenCounter,
                 config: GenerationConfig = GenerationConfig()):
        self.retriever = retriever
        self.llm = llm
        self.counter = counter
        self.config = config

    def _prepare(self, question: str, mode: Mode, history: list[Exchange] | None,
                 filters: dict | None):
        question = question.strip()
        if not question:
            raise ValueError("La pregunta está vacía.")
        results = self.retriever.search_hybrid(question, filters=filters)
        return build_prompt(
            system_prompt=build_system_prompt(mode), question=question,
            history=history or [], results=results,
            count_tokens=self.counter.count, count_messages=self.counter.count_messages,
            config=self.config,
        )

    def answer(self, question: str, mode: Mode = Mode.CONSULTANT,
               history: list[Exchange] | None = None,
               filters: dict | None = None) -> GenerationResult:
        parts = self._prepare(question, mode, history, filters)
        text = self.llm.generate(parts.messages, max_new_tokens=parts.max_new_tokens)
        return build_result(text, parts.context_chunks)

    def answer_stream(self, question: str, mode: Mode = Mode.CONSULTANT,
                      history: list[Exchange] | None = None,
                      filters: dict | None = None) -> Iterator[tuple[str, object]]:
        """Emite ("token", str) y, al final, ("done", GenerationResult). Pensado para SSE (Fase 7)."""
        parts = self._prepare(question, mode, history, filters)
        pieces: list[str] = []
        for piece in self.llm.generate_stream(parts.messages, max_new_tokens=parts.max_new_tokens):
            pieces.append(piece)
            yield "token", piece
        yield "done", build_result("".join(pieces).strip(), parts.context_chunks)