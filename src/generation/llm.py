# src/generation/llm.py
from __future__ import annotations
import logging
from threading import Thread
from typing import Iterator

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)

from src.model_paths import local_model_path

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-1.5B-Instruct"


class LLM:
    """Modelo generativo residente en GPU (NF4 + cómputo FP16, sin offloading)."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA no disponible: el generador debe ejecutarse en GPU.")
        self.model_name = model_name
        path = local_model_path(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            path,
            quantization_config=quant,
            device_map={"": 0},          # todo en la GPU 0, sin CPU offloading
            dtype=torch.float16,
            local_files_only=True,
        )
        self.model.eval()
        logger.info("Modelo %s cargado (VRAM asignada: %.2f GB)",
                    model_name, torch.cuda.memory_allocated() / 1024**3)

    def _inputs(self, messages: list[dict]):
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return self.tokenizer(text, return_tensors="pt", add_special_tokens=False).to(self.model.device)

    def _gen_kwargs(self, max_new_tokens: int, temperature: float) -> dict:
        kwargs = {
            "max_new_tokens": max_new_tokens,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        if temperature > 0:
            kwargs.update(do_sample=True, temperature=temperature, top_p=0.9)
        else:
            kwargs.update(do_sample=False)
        return kwargs

    def generate(self, messages: list[dict], max_new_tokens: int = 512,
                 temperature: float = 0.0) -> str:
        inputs = self._inputs(messages)
        with torch.inference_mode():
            out = self.model.generate(**inputs, **self._gen_kwargs(max_new_tokens, temperature))
        new_tokens = out[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def generate_stream(self, messages: list[dict], max_new_tokens: int = 512,
                        temperature: float = 0.0) -> Iterator[str]:
        inputs = self._inputs(messages)
        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        kwargs = dict(**inputs, streamer=streamer,
                      **self._gen_kwargs(max_new_tokens, temperature))

        def _run():
            with torch.inference_mode():
                self.model.generate(**kwargs)

        thread = Thread(target=_run, daemon=True)
        thread.start()
        try:
            for piece in streamer:
                yield piece
        finally:
            thread.join()