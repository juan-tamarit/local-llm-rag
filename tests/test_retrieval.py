import pytest

from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.tokenizer import tokenize


def _payload(cid, content, source="a.py", **kw):
    return {"chunk_id": cid, "content": content, "source": source,
            "parent": None, "section": None, **kw}


class FakeStore:
    def __init__(self, payloads, semantic_order):
        self.payloads, self.semantic_order = payloads, semantic_order

    def scroll_all(self, batch_size=256):
        for p in self.payloads:
            yield {"id": p["chunk_id"], "payload": p}

    def count(self):
        return len(self.payloads)

    def search(self, query_vector, limit=20, filters=None):
        by_id = {p["chunk_id"]: p for p in self.payloads}
        out = []
        for i, cid in enumerate(self.semantic_order):
            p = by_id[cid]
            if filters and any(p.get(k) != v for k, v in filters.items()):
                continue
            out.append({"id": cid, "score": 1.0 - 0.1 * i, "payload": p})
        return out[:limit]


class FakeEmbedder:
    def embed_queries(self, q):
        return [[0.0] * 384]


@pytest.fixture
def store():
    return FakeStore(
        [
            _payload("a", "parse json files", source="parser.py"),
            _payload("b", "def connect database pool", source="db.py"),
            _payload("c", "render html templates", source="web.py"),
        ],
        semantic_order=["a", "b", "c"],
    )


# --- tokenizer ---
def test_tokenize_camel_and_snake():
    assert tokenize("DatabaseManager") == ["databasemanager", "database", "manager"]
    assert tokenize("get_user_id") == ["get_user_id", "get", "user", "id"]


def test_tokenize_accents_and_paths():
    assert tokenize("Configuración") == ["configuracion"]
    assert "manager" in tokenize("src/database/manager.py")


def test_tokenize_acronym():
    assert tokenize("HTTPServer")[1:] == ["http", "server"]


# --- fusion ---
def test_rrf_prefers_items_in_both():
    out = reciprocal_rank_fusion({"s": ["a", "b"], "l": ["b", "c"]}, k=60)
    assert out[0][0] == "b"
    assert out[0][1] == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_weights_and_limit():
    out = reciprocal_rank_fusion({"s": ["a"], "l": ["b"]}, weights={"l": 2.0}, limit=1)
    assert out == [("b", pytest.approx(2 / 61))]


def test_rrf_ignores_duplicates_within_ranking():
    out = dict(reciprocal_rank_fusion({"s": ["a", "a"]}))
    assert out["a"] == pytest.approx(1 / 61)


# --- BM25 y recuperador (requieren rank-bm25) ---
def test_bm25_finds_identifier(store):
    pytest.importorskip("rank_bm25")
    from src.retrieval.bm25_index import BM25Index
    hits = BM25Index(store).search("connect database")
    assert hits[0]["id"] == "b"
    assert all(h["id"] != "c" for h in hits)


def test_bm25_filter_and_empty_query(store):
    pytest.importorskip("rank_bm25")
    from src.retrieval.bm25_index import BM25Index
    idx = BM25Index(store)
    assert idx.search("connect", filters={"source": "web.py"}) == []
    assert idx.search("???") == []


def test_bm25_refreshes_when_count_changes(store):
    pytest.importorskip("rank_bm25")
    from src.retrieval.bm25_index import BM25Index
    idx = BM25Index(store)
    store.payloads.append(_payload("d", "quantum flux capacitor", source="q.py"))
    assert idx.search("flux")[0]["id"] == "d"


def test_hybrid_fuses_both_rankings(store):
    pytest.importorskip("rank_bm25")
    from src.retrieval.hybrid import HybridRetriever
    r = HybridRetriever(FakeEmbedder(), store)
    res = r.search_hybrid("connect database")
    assert res[0].chunk_id == "b"
    assert res[0].semantic_rank == 2 and res[0].lexical_rank == 1
    assert [x.chunk_id for x in res].count("a") == 1
    only_lex = r.search_lexical("connect database")
    assert only_lex[0].lexical_rank == 1 and only_lex[0].semantic_rank is None


def test_hybrid_filter_applies_to_both(store):
    pytest.importorskip("rank_bm25")
    from src.retrieval.hybrid import HybridRetriever
    res = HybridRetriever(FakeEmbedder(), store).search_hybrid("connect", filters={"source": "db.py"})
    assert [x.chunk_id for x in res] == ["b"]
