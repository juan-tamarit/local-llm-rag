from types import SimpleNamespace

import numpy as np
import pytest

from src.processing.base import Chunk, ChunkMetadata
from src.embeddings.embedder import Embedder
from src.embeddings.vector_store import VectorStore


def make_chunk(chunk_id, content, document_id, source, **extra):
    return Chunk(
        chunk_id=chunk_id, document_id=document_id, content=content,
        source=source, content_type=extra.get("content_type", "documentation"),
        language=extra.get("language", "es"),
        metadata=ChunkMetadata(format="md", start_line=1, end_line=5,
                               section=extra.get("section")),
    )

@pytest.fixture(scope="module")
def embedder():
    return Embedder(device="cpu")


@pytest.fixture
def store(tmp_path):
    s = VectorStore(
        collection_name="test_collection",
        persist_dir=str(tmp_path / "qdrant_test_db"),
        vector_size=384,
    )
    yield s
    s.close()


@pytest.fixture
def chunks():
    return [
        make_chunk("chunk-001", "Python es un lenguaje de programación interpretado y de tipado dinámico.",
                   "doc-1", "python_intro.md"),
        make_chunk("chunk-002", "La cocina italiana destaca por sus pastas, pizzas y el aceite de oliva.",
                   "doc-2", "recetas.md"),
    ]


def test_embedder_dimensions_and_norm(embedder):
    vec = embedder.embed_passages(["Fragmento de prueba."])[0]
    assert len(vec) == 384 == embedder.dimension
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-3


def test_prefixes_change_embeddings(embedder):
    text = "Python"
    assert embedder.embed_passages([text])[0] != embedder.embed_queries([text])[0]


def test_add_and_search(embedder, store, chunks):
    store.add_chunks(chunks, embedder.embed_passages([c.content for c in chunks]))
    qv = embedder.embed_queries(["¿Qué características tiene Python?"])[0]
    results = store.search(qv, limit=2)
    assert results[0]["payload"]["document_id"] == "doc-1"
    assert results[0]["payload"]["source"] == "python_intro.md"
    assert "Python" in results[0]["payload"]["content"]


def test_upsert_is_idempotent(embedder, store, chunks):
    vecs = embedder.embed_passages([c.content for c in chunks])
    store.add_chunks(chunks, vecs)
    store.add_chunks(chunks, vecs)
    assert store.count() == 2


def test_delete_by_document(embedder, store, chunks):
    store.add_chunks(chunks, embedder.embed_passages([c.content for c in chunks]))
    store.delete_by_document("doc-1")
    assert store.count() == 1


def test_filter_by_source(embedder, store, chunks):
    store.add_chunks(chunks, embedder.embed_passages([c.content for c in chunks]))
    qv = embedder.embed_queries(["Python"])[0]
    results = store.search(qv, limit=5, filters={"source": "recetas.md"})
    assert len(results) == 1
    assert results[0]["payload"]["document_id"] == "doc-2"


def test_persistence(embedder, tmp_path, chunks):
    path = str(tmp_path / "persist_db")
    s1 = VectorStore("persist", path, 384)
    s1.add_chunks(chunks, embedder.embed_passages([c.content for c in chunks]))
    s1.close()

    s2 = VectorStore("persist", path, 384)
    try:
        assert s2.count() == 2
    finally:
        s2.close()


def test_missing_chunk_id_raises(embedder, store):
    bad = make_chunk("", "x", "d", "s.md")
    with pytest.raises(ValueError):
        store.add_chunks([bad], embedder.embed_passages(["x"]))