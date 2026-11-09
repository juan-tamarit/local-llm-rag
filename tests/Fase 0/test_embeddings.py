
import torch
from sentence_transformers import SentenceTransformer

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"

print(f"CUDA disponible: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")

torch.cuda.reset_peak_memory_stats()

model = SentenceTransformer(
    MODEL_ID,
    device="cuda",
    model_kwargs={
        "torch_dtype": torch.float16,
    },
)

print(f"\nDispositivo del modelo: {model.device}")

texts = [
    "¿Cómo se establece una conexión con una base de datos?",
    "def connect(self):\n    return self.pool.acquire()",
]

embeddings = model.encode(
    texts,
    convert_to_tensor=True,
    normalize_embeddings=True,
)

print("\nResultados:")
print(f"Forma: {embeddings.shape}")
print(f"Dispositivo: {embeddings.device}")
print(f"Tipo de dato: {embeddings.dtype}")

print(
    f"\nVRAM asignada: "
    f"{torch.cuda.memory_allocated() / 1024**3:.2f} GB"
)

print(
    f"Pico de VRAM asignada: "
    f"{torch.cuda.max_memory_allocated() / 1024**3:.2f} GB"
)
