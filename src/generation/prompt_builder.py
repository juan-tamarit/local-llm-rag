# src/generation/prompt_builder.py
from __future__ import annotations
from typing import Callable
from src.retrieval.base import RetrievalResult
from .base import ContextChunk, Exchange, GenerationConfig, PromptParts
from .context_builder import build_context
from .history import select_history

NO_CONTEXT_MARKER = "[NO DOCUMENTS RETRIEVED]"


class PromptTooLongError(ValueError):
    """El system prompt y la pregunta por sí solos no caben en el presupuesto."""


def _user_message(chunks: list[ContextChunk], question: str) -> str:
    ctx = "\n\n".join(c.text for c in chunks) if chunks else NO_CONTEXT_MARKER
    return f"<context>\n{ctx}\n</context>\n\n<question>\n{question}\n</question>"


def _messages(system_prompt, history, chunks, question) -> list[dict]:
    msgs = [{"role": "system", "content": system_prompt}]
    for ex in history:
        msgs.append({"role": "user", "content": ex.user})
        msgs.append({"role": "assistant", "content": ex.assistant})
    msgs.append({"role": "user", "content": _user_message(chunks, question)})
    return msgs


def build_prompt(
    *,
    system_prompt: str,
    question: str,
    history: list[Exchange],
    results: list[RetrievalResult],
    count_tokens: Callable[[str], int],
    count_messages: Callable[[list[dict]], int],
    config: GenerationConfig = GenerationConfig(),
) -> PromptParts:
    limit = config.max_context_tokens - config.max_new_tokens
    base = count_messages(_messages(system_prompt, [], [], question))
    remaining = limit - base
    if remaining < 0:
        raise PromptTooLongError(
            f"System prompt + pregunta ({base} tokens) superan el presupuesto ({limit})."
        )

    hist = select_history(history, count_tokens, min(config.max_history_tokens, remaining))
    with_hist = count_messages(_messages(system_prompt, hist, [], question))
    rag_budget = min(config.max_rag_tokens, limit - with_hist)
    chunks = build_context(results, count_tokens, max(rag_budget, 0), config.max_rag_chunks)

    while True:
        msgs = _messages(system_prompt, hist, chunks, question)
        total = count_messages(msgs)
        if total <= limit:
            break
        if chunks:
            chunks = chunks[:-1]          # S1..Sn siguen contiguos
        elif hist:
            hist = hist[1:]               # se descarta el intercambio más antiguo
        else:
            raise PromptTooLongError("No se puede ajustar el prompt al presupuesto.")

    return PromptParts(msgs, chunks, hist, total, config.max_new_tokens)