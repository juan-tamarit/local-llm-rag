# scripts/ingest.py
import logging
import time
from pathlib import Path

from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.code_reader import CodeReader
from src.ingestion.markdown_reader import MarkdownReader
from src.ingestion.html_reader import HTMLReader
from src.ingestion.office_reader import OfficeReader
from src.ingestion.pdf_reader import PDFReader
from src.processing.text_splitter import RecursiveTextSplitter
from src.processing.code_splitter import CodeSplitter
from src.embeddings.embedder import Embedder, MAX_SEQ_LENGTH
from src.embeddings.vector_store import VectorStore, chunk_to_payload

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ingest")

DOCS_DIR = Path("data/documents").resolve()
CODE_EXTENSIONS = {".py"}      # el chunker AST solo cubre Python (Fase 2)


def build_pipeline() -> IngestionPipeline:
    pipeline = IngestionPipeline()
    pipeline.register_reader(".py", CodeReader())
    markdown = MarkdownReader()
    for ext in (".md", ".markdown"):
        pipeline.register_reader(ext, markdown)
    html = HTMLReader()
    for ext in (".html", ".htm"):
        pipeline.register_reader(ext, html)
    office = OfficeReader()
    for ext in (".docx", ".pptx"):
        pipeline.register_reader(ext, office)
    pipeline.register_reader(".pdf", PDFReader())
    return pipeline


def main() -> None:
    files = sorted(p for p in DOCS_DIR.rglob("*") if p.is_file())
    if not files:
        raise SystemExit(f"No hay archivos en {DOCS_DIR}. Copia ahí tu corpus.")

    pipeline = build_pipeline()
    text_splitter = RecursiveTextSplitter()
    code_splitter = CodeSplitter()
    embedder = Embedder()
    store = VectorStore()

    total_chunks = truncated = skipped = 0
    t_embed = 0.0
    try:
        for path in files:
            try:
                doc = pipeline.ingest_file(path)
            except Exception as exc:
                log.warning("Omitido %s: %s", path, exc)
                skipped += 1
                continue

            splitter = code_splitter if path.suffix.lower() in CODE_EXTENSIONS else text_splitter
            chunks = splitter.chunk(doc)
            if not chunks:
                log.warning("Sin chunks: %s", path)
                continue

            payloads = [chunk_to_payload(c) for c in chunks]
            texts = [p["content"] for p in payloads]
            truncated += sum(embedder.count_tokens(t) > MAX_SEQ_LENGTH for t in texts)

            t0 = time.perf_counter()
            vectors = embedder.embed_passages(texts)
            t_embed += time.perf_counter() - t0

            store.delete_by_document(payloads[0]["document_id"])   # reindexado limpio
            store.add_chunks(chunks, vectors)
            total_chunks += len(chunks)
            log.info("%s -> %d chunks", path, len(chunks))

        print(f"\nArchivos: {len(files)} (omitidos: {skipped}) | chunks indexados: {total_chunks} "
              f"| total en el índice: {store.count()}")
        print(f"Chunks sobre {MAX_SEQ_LENGTH} tokens (se truncan al embeber): {truncated}")
        print(f"Tiempo de embeddings en CPU: {t_embed:.1f} s")
    finally:
        store.close()


if __name__ == "__main__":
    main()