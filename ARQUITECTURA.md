# ARQUITECTURA.md

# Arquitectura del repositorio

El repositorio separa la documentación, el entorno Python, la aplicación web, el motor RAG, los datos y las pruebas.

## Estructura

```text
local-llm-rag/
├── .venv/                       # Entorno virtual local (no versionar)
├── .python-version              # Versión de Python fijada (3.11)
├── .gitignore
├── pyproject.toml               # Metadatos y dependencias del proyecto
├── uv.lock                      # Resolución reproducible de dependencias
├── README.md
├── TECH_STACK.md
├── ARQUITECTURA.md
├── PLAN_IMPLEMENTACION.md
├── frontend/                    # Aplicación web React + Vite (Fase 8, pendiente)
├── scripts/                     # Utilidades ejecutables con `uv run python -m scripts.<nombre>`
│   ├── download_models.py       # Descarga única (con internet) de los modelos a models/
│   ├── ingest.py                # Ingesta -> chunking -> embeddings -> indexación en Qdrant
│   ├── smoke_llm.py             # Prueba de humo del generador y del prompt (requiere GPU)
│   └── smoke_pipeline.py        # Prueba de humo de RAGGenerator con el índice real
├── models/                      # Modelos descargados para uso offline (no versionar)
├── src/
│   ├── model_paths.py           # local_model_path(): resuelve la carpeta local de cada modelo en models/
│   ├── ingestion/               # Lectura y extracción de documentos (implementado)
│   │   ├── base.py              # ExtractedDocument, DocumentMetadata, BaseReader
│   │   ├── pipeline.py          # IngestionPipeline: extensión -> lector
│   │   ├── pdf_reader.py        # PDF (PyMuPDF)
│   │   ├── office_reader.py     # .docx / .pptx (python-docx, python-pptx)
│   │   ├── html_reader.py       # HTML (BeautifulSoup)
│   │   ├── markdown_reader.py   # Markdown (markdown-it-py)
│   │   └── code_reader.py       # Código fuente (Tree-sitter)
│   ├── processing/              # Normalización y chunking (implementado)
│   │   ├── base.py              # Chunk, ChunkMetadata, BaseChunker
│   │   ├── text_splitter.py     # Chunker recursivo para documentación y texto
│   │   └── code_splitter.py     # Chunker basado en AST (Python)
│   ├── embeddings/              # Embeddings e indexación vectorial (implementado)
│   │   ├── embedder.py          # Embedder: multilingual-e5-small (CPU), prefijos query/passage
│   │   └── vector_store.py      # VectorStore (Qdrant local) y chunk_to_payload
│   ├── retrieval/               # Búsqueda híbrida (semántica + BM25 + RRF) (implementado)
│   │   ├── base.py              # RetrievalResult
│   │   ├── tokenizer.py         # Tokenizador de BM25 sensible a código (snake_case, camelCase)
│   │   ├── bm25_index.py        # BM25Index (rank-bm25), construido con VectorStore.scroll_all()
│   │   ├── fusion.py            # reciprocal_rank_fusion (función pura)
│   │   └── hybrid.py            # HybridRetriever: search_semantic / search_lexical / search_hybrid
│   ├── generation/              # Prompt, contexto e inferencia del LLM (implementado)
│   │   ├── base.py              # Mode, GenerationConfig, ContextChunk, Exchange, PromptParts, GenerationResult
│   │   ├── token_counter.py     # TokenCounter: tokens con el tokenizador de Qwen y la plantilla de chat
│   │   ├── language.py          # detect_language(): heurística ES/EN sin dependencias
│   │   ├── prompts.py           # System prompt común + bloques PROGRAMMER / CONSULTANT
│   │   ├── context_builder.py   # RetrievalResult -> fragmentos [S1..Sn]; sanitize() de delimitadores e inyecciones
│   │   ├── history.py           # Selección de intercambios por tokens (más recientes primero)
│   │   ├── prompt_builder.py    # Ensamblado del prompt dentro del presupuesto global de 4.096 tokens
│   │   ├── llm.py               # LLM: Qwen2.5-Coder-1.5B en NF4/FP16, generate() y generate_stream()
│   │   ├── citations.py         # Extracción y validación estructural de referencias [S#]
│   │   └── pipeline.py          # RAGGenerator: consulta -> retrieval -> prompt -> LLM -> respuesta validada
│   ├── api/                     # API FastAPI (pendiente)
│   └── evaluation/              # Evaluación del pipeline RAG (pendiente)
├── data/
│   ├── documents/               # Documentos fuente
│   └── indexes/                 # Índices y datos persistentes (qdrant_db/, no versionar)
└── tests/
    ├── test_processing.py       # Pruebas del módulo de procesamiento
    ├── test_embeddings.py       # Pruebas de embeddings y almacén vectorial (Qdrant)
    ├── test_retrieval.py        # Pruebas de recuperación: tokenizador, RRF, BM25 y búsqueda híbrida
    └── test_generation.py       # Pruebas de la lógica pura de generación (sin GPU): contexto, historial, prompt, citas, saneamiento e idioma
```

Los módulos marcados como pendientes se incorporarán progresivamente al implementar cada fase (ver `PLAN_IMPLEMENTACION.md`). El reranking no forma parte de la versión inicial; si se incorpora, será una etapa desacoplada dentro de `src/retrieval/`.

## Gestión del entorno Python

- `pyproject.toml` es la fuente de verdad para los metadatos y las dependencias declaradas.
- `uv.lock` registra las versiones resueltas para reproducir el entorno.
- `.python-version` fija la versión de Python utilizada por `uv`.
- `.venv/` contiene el entorno virtual local y debe permanecer fuera del control de versiones.
- `.gitignore` excluye, como mínimo, `.venv/`, `models/`, `data/indexes/qdrant_db/`, cachés, secretos y artefactos locales que no deban versionarse.
- El índice de PyTorch (`cu130`) se declara con `explicit = true` y solo se usa para `torch`; los demás paquetes proceden de PyPI. Así se evita que la copia antigua de `urllib3` del índice de PyTorch bloquee la resolución de `qdrant-client`.

Comandos habituales:

```powershell
uv sync           # Sincronizar el entorno con pyproject.toml y uv.lock
uv add <paquete>  # Añadir una dependencia al proyecto
uv run <comando>  # Ejecutar un comando dentro del entorno
```

No se utilizará `requirements.txt` como mecanismo principal de gestión de dependencias. Si en el futuro se necesita exportar dependencias para otra herramienta, se tratará como un artefacto derivado y no como fuente de verdad.

## Separación de responsabilidades

- **Frontend (`frontend/`):** interfaz de usuario React + Vite.
- **API (`src/api/`):** comunicación con los clientes mediante FastAPI, REST y SSE.
- **Motor RAG (`src/ingestion/`, `src/processing/`, `src/embeddings/`, `src/retrieval/`, `src/generation/`):** ingesta, procesamiento, embeddings, recuperación y generación. Su lógica debe mantenerse desacoplada de la API y del frontend.
- **Evaluación (`src/evaluation/`):** pipeline de evaluación independiente del pipeline de producción.
- **Datos (`data/`):** documentos originales e índices locales.
- **Pruebas (`tests/`):** pruebas automatizadas y conjunto de evaluación.

La API no dependerá de una interfaz concreta. El motor RAG podrá ser utilizado por la aplicación web y por futuros clientes compatibles con los contratos de la API.

## Contratos entre módulos

Cada etapa del pipeline produce una representación común, independiente del formato original:

```text
Archivo  ->  [ingestion]  ->  ExtractedDocument  ->  [processing]  ->  Chunk  ->  [embeddings / indexación]
Consulta ->  [retrieval]  ->  RetrievalResult (payload del Chunk)  ->  [generation]  ->  GenerationResult
```

- `ExtractedDocument` y `DocumentMetadata` (`src/ingestion/base.py`): contenido extraído y metadatos de procedencia. Todo lector hereda de `BaseReader`, y `IngestionPipeline` elige el lector según la extensión. `IngestionPipeline` arranca sin lectores: hay que registrarlos con `register_reader` (ver `build_pipeline()` en `scripts/ingest.py`). Los lectores guardan en `source` la ruta absoluta y derivan `document_id` de ella con `Path.as_uri()` (deuda técnica registrada en la Fase 5: ver `PLAN_IMPLEMENTACION.md`).
- `Chunk` y `ChunkMetadata` (`src/processing/base.py`): fragmento con metadatos de contexto (líneas de inicio y fin, sección, elemento contenedor y lenguaje). Todo chunker hereda de `BaseChunker`.

- `Embedder` (`src/embeddings/embedder.py`): recibe textos y devuelve vectores normalizados de 384 dimensiones; aplica los prefijos `passage:` (chunks) y `query:` (consultas).
- `VectorStore` (`src/embeddings/vector_store.py`): recibe `Chunk` y sus vectores. `chunk_to_payload` convierte el `Chunk` en el payload de Qdrant (`content`, `chunk_id`, `document_id`, `source`, `content_type`, `language`, `start_line`, `end_line`, `section`, `parent`, `format` y `extra_info`). Devuelve resultados como diccionarios con `id`, `score` y `payload`, que consume la capa de recuperación.
- `RetrievalResult` (`src/retrieval/base.py`): resultado de la recuperación, con `chunk_id`, `score`, `payload` (el del `Chunk` indexado) y la trazabilidad por buscador (`semantic_rank`, `lexical_rank`, `semantic_score`, `lexical_score`). `BM25Index.search` devuelve diccionarios con el mismo formato que `VectorStore.search` (`id`, `score`, `payload`), y `HybridRetriever` ofrece `search_semantic`, `search_lexical` y `search_hybrid`, que devuelven `list[RetrievalResult]`. Un futuro reranker se aplicaría sobre la salida de `search_hybrid`.

- `GenerationConfig` (`src/generation/base.py`): presupuestos de la generación (`max_context_tokens=4096`, `max_rag_tokens=2500`, `max_rag_chunks=5`, `max_history_tokens=500`, `max_new_tokens=512`).
- `ContextChunk` y `Exchange` (`src/generation/base.py`): `ContextChunk` es el fragmento formateado como `[DOCUMENT S#]` con su referencia temporal (`ref`), el `chunk_id` persistente, el texto, los tokens, `source` y las líneas; el mapa `S# -> chunk_id` vive en la lista de `ContextChunk` de cada respuesta. `Exchange` es un par pregunta/respuesta del historial.
- `PromptParts` (`src/generation/base.py`): mensajes en formato chat (`system` / `user` / `assistant`), fragmentos y historial finalmente incluidos, tokens reales del prompt (medidos con la plantilla de chat de Qwen) y reserva para la respuesta. `build_prompt` lo construye respetando el presupuesto global: recorta primero el contexto RAG, después el historial, y nunca el system prompt ni la pregunta.
- `GenerationResult` (`src/generation/base.py`): `answer`, `cited_refs` (válidas), `invalid_refs`, `sources` (referencia, `chunk_id`, `source` y líneas de los fragmentos realmente citados), `context_chunks` y `uncited` (había contexto pero la respuesta no cita ningún fragmento válido).
- `RAGGenerator` (`src/generation/pipeline.py`): `answer(question, mode, history, filters)` devuelve un `GenerationResult`; `answer_stream(...)` emite `("token", str)` y al final `("done", GenerationResult)`, pensado para SSE en la Fase 7. Recibe `HybridRetriever`, `LLM` y `TokenCounter` ya construidos, sin conocer FastAPI ni el frontend.
- La validación de referencias es solo estructural (el identificador citado existe entre los fragmentos proporcionados); la correspondencia semántica entre afirmación y fuente se evalúa en la Fase 6.

Los módulos posteriores (recuperación, generación) consumen únicamente `Chunk` o los payloads derivados de él, sin conocer el formato de origen. La generación recibe los `RetrievalResult` y trabaja con su `payload`.
