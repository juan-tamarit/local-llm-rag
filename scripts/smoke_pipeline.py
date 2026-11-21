# scripts/smoke_pipeline.py
import logging
from src.embeddings.embedder import Embedder
from src.embeddings.vector_store import VectorStore
from src.retrieval.hybrid import HybridRetriever
from src.generation.llm import LLM
from src.generation.token_counter import TokenCounter
from src.generation.pipeline import RAGGenerator
from src.generation.base import Mode

logging.basicConfig(level=logging.WARNING)

store = VectorStore()
try:
    embedder = Embedder()
    retriever = HybridRetriever(embedder=embedder, vector_store=store)
    gen = RAGGenerator(retriever, LLM(), TokenCounter())
    preguntas = [
    "¿Qué hace HybridRetriever?",                                   # código
    "¿Cómo se calcula la fusión RRF y qué valor tiene k?",           # código + docs
    "¿Por qué no se usa reranking en la primera versión?",           # solo documentación
    "¿Cómo se despliega la aplicación en Kubernetes?",               # no disponible
    ]
    for q in preguntas:
        res = gen.answer(q, Mode.CONSULTANT)
        print(f"\n### {q}")
        print("Fragmentos:", [(c.ref, c.source, c.start_line) for c in res.context_chunks])
        print(res.answer)
        print(f"-> citadas={res.cited_refs} invalidas={res.invalid_refs} uncited={res.uncited}")
finally:
    store.close()