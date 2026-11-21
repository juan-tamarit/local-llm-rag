# src/generation/history.py
from __future__ import annotations
from typing import Callable
from .base import Exchange

MESSAGE_OVERHEAD = 5  # aprox. <|im_start|>role\n ... <|im_end|>\n por mensaje


def select_history(
    exchanges: list[Exchange],
    count_tokens: Callable[[str], int],
    max_tokens: int,
) -> list[Exchange]:
    """Devuelve los intercambios más recientes que caben, en orden cronológico."""
    selected: list[Exchange] = []
    used = 0
    for ex in reversed(exchanges):
        n = count_tokens(ex.user) + count_tokens(ex.assistant) + 2 * MESSAGE_OVERHEAD
        if used + n > max_tokens:
            break
        selected.append(ex)
        used += n
    selected.reverse()
    return selected