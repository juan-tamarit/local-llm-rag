import torch
from sentence_transformers import CrossEncoder

MODEL_ID = "Qwen/Qwen3-Reranker-0.6B"
MAX_LENGTH = 1024
BATCH_SIZE = 1

QUERY = "¿Cómo puedo obtener una conexión del pool de conexiones a una base de datos?"

DOCUMENTS = [
    {
        "id": "doc_1",
        "text": (
            "Para obtener una conexión del pool, utiliza el método acquire. "
            "La conexión devuelta debe liberarse cuando termine la operación."
        ),
    },
    {
        "id": "doc_2",
        "text": "def connect(self):\n    return self.pool.acquire()",
    },
    {
        "id": "doc_3",
        "text": (
            "La biblioteca json permite serializar objetos de Python "
            "y convertirlos en cadenas JSON mediante json.dumps."
        ),
    },
]


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no está disponible. Esta prueba requiere GPU.")

    print(f"CUDA disponible: {torch.cuda.is_available()}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Modelo: {MODEL_ID}")
    print("Precisión solicitada: float16")
    print(f"Longitud máxima: {MAX_LENGTH}")
    print(f"Batch size: {BATCH_SIZE}")

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    print("\nCargando reranker...")
    model = CrossEncoder(
        MODEL_ID,
        device="cuda",
        max_length=MAX_LENGTH,
        model_kwargs={"torch_dtype": torch.float16},
    )

    print(f"Dispositivo del modelo: {model.model.device}")
    model_dtype = next(model.model.parameters()).dtype
    print(f"Tipo de dato de los parámetros: {model_dtype}")

    pairs = [(QUERY, document["text"]) for document in DOCUMENTS]

    print("\nCalculando puntuaciones...")
    scores = model.predict(
        pairs,
        batch_size=BATCH_SIZE,
        show_progress_bar=False,
        convert_to_numpy=True,
    )

    results = [
        {
            "id": document["id"],
            "score": float(score),
            "text": document["text"],
        }
        for document, score in zip(DOCUMENTS, scores)
    ]
    results.sort(key=lambda result: result["score"], reverse=True)

    print("\nResultados ordenados por relevancia:")
    for position, result in enumerate(results, start=1):
        print(f"\n{position}. {result['id']} | score: {result['score']:.4f}")
        print(result["text"])

    print("\nMemoria GPU:")
    print(f"VRAM asignada: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
    print(
        "Pico de VRAM asignada: "
        f"{torch.cuda.max_memory_allocated() / 1024**3:.2f} GB"
    )

    print("\nPrueba finalizada.")
    print(
        "Nota: las puntuaciones son valores de relevancia del modelo; "
        "no deben interpretarse como probabilidades calibradas."
    )


if __name__ == "__main__":
    main()