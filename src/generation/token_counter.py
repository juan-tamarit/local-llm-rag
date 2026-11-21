# src/generation/token_counter.py
from __future__ import annotations
from transformers import AutoTokenizer


class TokenCounter:
    def __init__(self, model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def count(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def count_messages(self, messages: list[dict]) -> int:
        """Tokens del prompt completo, incluidos los tokens especiales de la
        plantilla y el arranque de la respuesta del asistente."""
        rendered = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return len(self.tokenizer.encode(rendered, add_special_tokens=False))