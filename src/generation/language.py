from __future__ import annotations
import re

_ES_CHARS = re.compile(r"[¿¡áéíóúñü]", re.IGNORECASE)
_ES = {"qué", "que", "cómo", "como", "cuál", "cual", "el", "la", "los", "las", "de", "del",
       "en", "por", "para", "es", "un", "una", "y", "se", "con", "dónde", "donde",
       "cuándo", "hay", "puedo", "si", "al", "lo"}
_EN = {"the", "what", "how", "is", "are", "of", "to", "and", "in", "for", "a", "an", "with",
       "does", "do", "can", "why", "where", "which", "this", "that", "it"}


def detect_language(text: str, default: str = "Spanish") -> str:
    """Heurística ES/EN sin dependencias. Devuelve 'Spanish' o 'English'."""
    if _ES_CHARS.search(text):
        return "Spanish"
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    es = sum(w in _ES for w in words)
    en = sum(w in _EN for w in words)
    if en > es:
        return "English"
    if es > en:
        return "Spanish"
    return default