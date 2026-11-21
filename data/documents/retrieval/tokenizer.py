"""Tokenizador para BM25, sensible a identificadores de código.

Para cada palabra se emite el identificador completo en minúsculas y,
si es compuesto (snake_case, camelCase, dígitos), también sus partes:

    DatabaseManager -> databasemanager, database, manager
    get_user_id     -> get_user_id, get, user, id
"""

import re
import unicodedata
from typing import List

_WORD_RE = re.compile(r"\w+", re.UNICODE)  # rutas y puntos se separan solos
_CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for word in _WORD_RE.findall(_strip_accents(text)):
        word = word.strip("_")
        if not word:
            continue
        tokens.append(word.lower())
        parts: List[str] = []
        for segment in word.split("_"):
            parts.extend(m.lower() for m in _CAMEL_RE.findall(segment))
        if len(parts) > 1:
            tokens.extend(parts)
    return tokens
