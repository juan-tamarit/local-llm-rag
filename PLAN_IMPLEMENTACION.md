# PLAN_IMPLEMENTACION.md

# Plan de implementación

Orden de desarrollo del proyecto Local LLM & RAG. Cada fase indica el
módulo responsable, su ubicación y las tecnologías previstas.

## Fase 0. Preparación del entorno

-   **Objetivo:** preparar el entorno de desarrollo y comprobar que el
    hardware puede ejecutar los modelos seleccionados.
-   **Ubicación:** raíz del proyecto.
-   **Archivos principales:** `requirements.txt`.
-   **Tecnologías:** Python, PyTorch, CUDA, Hugging Face Transformers,
    bitsandbytes.
-   **Resultado:** entorno reproducible y pruebas de carga e inferencia
    de los modelos en la GPU objetivo.

## Fase 1. Ingesta documental

-   **Objetivo:** leer los formatos admitidos y extraer su contenido y
    estructura.
-   **Ubicación:** `src/ingestion/`.
-   **Tecnologías:**
    -   Docling: PDF y documentos Office.
    -   BeautifulSoup: HTML.
    -   markdown-it-py: Markdown.
    -   Tree-sitter: código fuente.
-   **Resultado:** contenido extraído y estructurado, con información de
    procedencia, preparado para su procesamiento.

## Fase 2. Procesamiento y chunking

-   **Objetivo:** normalizar los documentos y generar chunks coherentes
    con su estructura y tipo de contenido.
-   **Ubicación:** `src/processing/`.
-   **Tecnologías:** Python y Tree-sitter para el análisis sintáctico
    del código; estrategia de Recursive Text Splitting adaptada a la
    estructura documental.
-   **Resultado:** representación común de chunks con contenido y
    metadatos de procedencia y contexto.

## Fase 3. Embeddings e indexación

-   **Objetivo:** generar embeddings de los chunks y almacenarlos junto
    con sus metadatos.
-   **Ubicación:** `src/embeddings/` y `data/indexes/`.
-   **Tecnologías:** Qwen3-Embedding-0.6B, Sentence Transformers,
    PyTorch, CUDA y Qdrant.
-   **Datos:** documentos originales en `data/documents/`.
-   **Resultado:** índice vectorial local consultable y persistente.

## Fase 4. Recuperación y reranking

-   **Objetivo:** recuperar candidatos mediante búsqueda semántica y
    léxica, combinar los resultados y reordenarlos por relevancia.
-   **Ubicación:** `src/retrieval/`.
-   **Tecnologías:** Qdrant, rank-bm25, Reciprocal Rank Fusion (RRF),
    Qwen3-Reranker-0.6B y Sentence Transformers (CrossEncoder).
-   **Resultado:** fragmentos recuperados y ordenados para construir el
    contexto de generación.

## Fase 5. Generación y gestión del contexto

-   **Objetivo:** construir el prompt, incorporar historial y contexto
    RAG, ejecutar el LLM y validar las referencias documentales.
-   **Ubicación:** `src/generation/`.
-   **Tecnologías:** Qwen2.5-Coder-1.5B-Instruct, Hugging Face
    Transformers, PyTorch, bitsandbytes, CUDA y LangChain.
-   **Resultado:** respuestas generadas con referencias a los fragmentos
    utilizados.

## Fase 6. Evaluación

-   **Objetivo:** implementar el conjunto de evaluación y medir
    Retrieval, Generation y End-to-End.
-   **Ubicación:** `tests/` para los casos y pruebas; los componentes
    propios del pipeline de evaluación se ubicarán en `src/evaluation/`.
-   **Tecnologías:** Python y métricas implementadas inicialmente en el
    proyecto. Ragas o DeepEval podrán estudiarse como complementos.
-   **Resultado:** ejecuciones reproducibles y resultados en JSON que
    permitan comparar configuraciones.

## Fase 7. API backend

-   **Objetivo:** exponer el motor RAG mediante una API independiente de
    los clientes.
-   **Ubicación:** `src/api/`.
-   **Tecnologías:** FastAPI, REST y Server-Sent Events (SSE).
-   **Resultado:** API capaz de gestionar solicitudes y coordinar el
    acceso al motor RAG.

## Fase 8. Interfaz web

-   **Objetivo:** desarrollar la aplicación web para gestionar proyectos
    y conversaciones e interactuar con el asistente.
-   **Ubicación:** `frontend/`.
-   **Tecnologías:** React y Vite.
-   **Comunicación:** API REST y SSE.
-   **Resultado:** interfaz web conectada al backend.
