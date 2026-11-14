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
├── src/
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
│   ├── embeddings/              # Generación de embeddings (pendiente)
│   ├── retrieval/               # Búsqueda híbrida (semántica + BM25 + RRF) (pendiente)
│   ├── generation/              # Prompt, contexto e inferencia del LLM (pendiente)
│   ├── api/                     # API FastAPI (pendiente)
│   └── evaluation/              # Evaluación del pipeline RAG (pendiente)
├── data/
│   ├── documents/               # Documentos fuente
│   └── indexes/                 # Índices y datos persistentes
└── tests/
    └── test_processing.py       # Pruebas del módulo de procesamiento
```

Los módulos marcados como pendientes se incorporarán progresivamente al implementar cada fase (ver `PLAN_IMPLEMENTACION.md`). El reranking no forma parte de la versión inicial; si se incorpora, será una etapa desacoplada dentro de `src/retrieval/`.

## Gestión del entorno Python

- `pyproject.toml` es la fuente de verdad para los metadatos y las dependencias declaradas.
- `uv.lock` registra las versiones resueltas para reproducir el entorno.
- `.python-version` fija la versión de Python utilizada por `uv`.
- `.venv/` contiene el entorno virtual local y debe permanecer fuera del control de versiones.
- `.gitignore` excluye, como mínimo, `.venv/`, cachés, secretos y artefactos locales que no deban versionarse.

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
```

- `ExtractedDocument` y `DocumentMetadata` (`src/ingestion/base.py`): contenido extraído y metadatos de procedencia. Todo lector hereda de `BaseReader`, y `IngestionPipeline` elige el lector según la extensión.
- `Chunk` y `ChunkMetadata` (`src/processing/base.py`): fragmento con metadatos de contexto (líneas de inicio y fin, sección, elemento contenedor y lenguaje). Todo chunker hereda de `BaseChunker`.

Los módulos posteriores (embeddings, indexación, recuperación) consumen únicamente `Chunk`, sin conocer el formato de origen.
