import gc
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from sentence_transformers import SentenceTransformer, CrossEncoder

GENERATOR_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
EMBEDDING_ID = "Qwen/Qwen3-Embedding-0.6B"
RERANKER_ID = "Qwen/Qwen3-Reranker-0.6B"

def report_memory(label):
    torch.cuda.synchronize()
    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    free, total = torch.cuda.mem_get_info()
    print(f"\n[{label}]")
    print(f"PyTorch allocated: {allocated:.2f} GB")
    print(f"PyTorch reserved:  {reserved:.2f} GB")
    print(f"CUDA free:         {free / 1024**3:.2f} GB")
    print(f"CUDA total:        {total / 1024**3:.2f} GB")

def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no está disponible.")

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA de PyTorch: {torch.version.cuda}")

    torch.cuda.reset_peak_memory_stats()
    report_memory("Estado inicial")

    # 1. Cargar el modelo generativo y mantenerlo en memoria.
    print("\n1/3 Cargando modelo generativo...")
    tokenizer = AutoTokenizer.from_pretrained(GENERATOR_ID)
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
    )
    generator = AutoModelForCausalLM.from_pretrained(
        GENERATOR_ID,
        quantization_config=quantization_config,
        device_map={"": 0},
        torch_dtype=torch.float16,
    )
    report_memory("Tras cargar generativo")

    # 2. Cargar embeddings sin liberar el generativo.
    print("\n2/3 Cargando modelo de embeddings...")
    embedding_model = SentenceTransformer(
        EMBEDDING_ID,
        device="cuda",
        model_kwargs={"torch_dtype": torch.float16},
    )
    report_memory("Tras cargar generativo + embeddings")

    # 3. Cargar reranker sin liberar los otros dos modelos.
    print("\n3/3 Cargando reranker...")
    reranker = CrossEncoder(
        RERANKER_ID,
        device="cuda",
        max_length=1024,
        automodel_args={"torch_dtype": torch.float16},
    )
    report_memory("Tras cargar los tres modelos")

    # Ejecutar una inferencia pequeña de cada modelo manteniendo los tres cargados.
    print("\nEjecutando inferencias con los tres modelos residentes en GPU...")

    messages = [
        {
            "role": "user",
            "content": "Escribe una función Python breve que compruebe si un número es primo.",
        }
    ]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        generated = generator.generate(**inputs, max_new_tokens=64, do_sample=False)
    generated_text = tokenizer.decode(
        generated[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    print("\nGenerativo: inferencia correcta.")
    print(generated_text[:500])
    del inputs, generated
    report_memory("Tras inferencia generativa")

    texts = [
        "Cómo obtener una conexión de un pool en Python.",
        "def connect(self): return self.pool.acquire()",
    ]
    with torch.inference_mode():
        embeddings = embedding_model.encode(
            texts,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )
    print(f"\nEmbeddings: inferencia correcta. Forma: {tuple(embeddings.shape)}")
    del embeddings
    report_memory("Tras inferencia de embeddings")

    query = "¿Cómo obtener una conexión del pool?"
    documents = [
        "Para obtener una conexión del pool, utiliza el método acquire.",
        "La biblioteca json permite serializar objetos de Python.",
    ]
    pairs = [[query, document] for document in documents]
    scores = reranker.predict(pairs, batch_size=1)
    print(f"\nReranker: inferencia correcta. Puntuaciones: {scores}")
    report_memory("Tras inferencia del reranker")

    print("\nPRUEBA COMPLETADA: los tres modelos se han cargado y han ejecutado inferencia.")
    print(
        "Pico de memoria asignada por PyTorch: "
        f"{torch.cuda.max_memory_allocated() / 1024**3:.2f} GB"
    )
    print(
        "Pico de memoria reservada por PyTorch: "
        f"{torch.cuda.max_memory_reserved() / 1024**3:.2f} GB"
    )

if __name__ == "__main__":
    try:
        main()
    except torch.cuda.OutOfMemoryError as exc:
        print("\nPRUEBA INTERRUMPIDA: CUDA se ha quedado sin memoria.")
        print(f"Detalle: {exc}")
        if torch.cuda.is_available():
            print(
                "Memoria asignada al fallar: "
                f"{torch.cuda.memory_allocated() / 1024**3:.2f} GB"
            )
            print(
                "Pico de memoria asignada: "
                f"{torch.cuda.max_memory_allocated() / 1024**3:.2f} GB"
            )
        raise
    except Exception:
        print("\nLa prueba ha fallado por un error distinto de falta de VRAM.")
        raise
