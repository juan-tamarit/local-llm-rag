# PLAN_IMPLEMENTACION.md

# Plan de implementación

Orden de desarrollo del proyecto Local LLM & RAG. Cada fase indica el
módulo responsable, su ubicación y las tecnologías previstas.

## Fase 0. Preparación del entorno

* **Objetivo:** preparar un entorno reproducible, comprobar que el hardware puede ejecutar operaciones de inferencia mediante GPU y definir la arquitectura de modelos viable para el sistema.
* **Ubicación:** raíz del proyecto.
* **Archivos principales:** `pyproject.toml`, `uv.lock`, `.python-version` y `.gitignore`. El entorno virtual se mantiene en `.venv/` y no se versiona.
* **Sistema operativo:** Windows 11.
* **Gestión del entorno:** uv.
* **Tecnologías:** Python, PyTorch, CUDA, NumPy, Hugging Face Transformers, Accelerate y bitsandbytes.
* **Hardware objetivo:** NVIDIA GeForce RTX 3050 Laptop GPU, 4 GB de VRAM, Compute Capability 8.6.

### Estado

Comprobaciones completadas:

* uv instalado (versión 0.12.7).
* Entorno virtual `.venv/` y archivo `uv.lock` creados.
* PyTorch 2.14.1+cu130 instalado y CUDA 13.0 detectada.
* GPU RTX 3050 Laptop detectada por PyTorch.
* NumPy 2.4.6 instalado.
* bitsandbytes 0.50.2 instalado.
* Operación matricial FP16 ejecutada correctamente en CUDA.
* Capa lineal NF4 ejecutada correctamente en CUDA.
* Transformers y Accelerate instalados.
* Sentence Transformers 6.2.0 instalado.
* Carga e inferencia de `Qwen/Qwen2.5-Coder-1.5B-Instruct` validadas correctamente en la RTX 3050 Laptop mediante cuantización NF4 de 4 bits y cálculo FP16, sin CPU offloading.
* Generación de código comprobada mediante una prueba de inferencia. Pico de memoria asignada por PyTorch: aproximadamente 1,15 GB (1,13 GB en la prueba aislada).
* Carga e inferencia individuales de `Qwen/Qwen3-Embedding-0.6B` validadas experimentalmente mediante Sentence Transformers, con FP16 y CUDA. Dimensión de salida: 1.024. Pico de memoria asignada por PyTorch: aproximadamente 1,12 GB.
* Carga e inferencia individuales de `Qwen/Qwen3-Reranker-0.6B` validadas experimentalmente mediante Sentence Transformers (CrossEncoder), con FP16 y CUDA. Longitud máxima: 1.024 tokens y batch size 1. Pico de memoria asignada por PyTorch: aproximadamente 1,12 GB.
* Carga e inferencia de `Qwen/Qwen2.5-Coder-1.5B-Instruct` validadas correctamente en la RTX 3050 Laptop mediante cuantización NF4 de 4 bits (con `BitsAndBytesConfig`) y cálculo FP16, sin CPU offloading.
* **Prueba de límites de contexto y generación completada con éxito (Fase 0 finalizada):**
  - Consumo inicial tras carga: ~1,13 GB de VRAM asignada / 1,18 GB reservada.
  - Contexto de entrada hasta ~22.828 tokens ejecutado dentro de la VRAM física de la GPU (3,58 GB reservados).
  - Contexto de ~45.628 tokens registró una advertencia de Transformers por superar la secuencia máxima nativa (32.768 tokens).
  - Pruebas de generación de hasta 1.024 tokens completadas de forma fluida y estable con VRAM reservada en 1,23 GB.

Desviación experimental y prueba conjunta de VRAM:

* Durante la Fase 0 se realizó una prueba de convivencia simultánea en GPU de los tres modelos de la familia Qwen (`Qwen2.5-Coder-1.5B-Instruct`, `Qwen3-Embedding-0.6B` y `Qwen3-Reranker-0.6B`).
* **Resultados de la prueba conjunta (NVIDIA RTX 3050 Laptop GPU, 4 GB VRAM):**
* Solo generador: ~1,13 GB de memoria asignada.
* Generador + embeddings: ~2,24 GB de memoria asignada.
* Los tres modelos cargados: 3,35–3,37 GB de memoria asignada.
* Memoria reservada por PyTorch al finalizar: ~3,38 GB.
* VRAM libre disponible: prácticamente 0 GB.


* **Conclusión técnica:** Aunque la convivencia es técnicamente posible para ejecuciones de prueba reducidas, no existe margen de VRAM suficiente para trabajar con garantías al aumentar la longitud del contexto, el tamaño de las consultas o la carga operacional de la aplicación.

Decisión de arquitectura definitiva:

* **Generación:** Se mantiene `Qwen/Qwen2.5-Coder-1.5B-Instruct` como único modelo neuronal residente en GPU (cuantizado en NF4 con cálculo FP16).
* **Embeddings:** Se sustituye `Qwen/Qwen3-Embedding-0.6B` por `intfloat/multilingual-e5-small`, ejecutándose inicialmente en CPU para reservar VRAM al generador.
* **Reranking:** Se excluye el modelo de reranking (`Qwen/Qwen3-Reranker-0.6B`) de la implementación inicial para optimizar recursos.

* **Estado de la fase:** FINALIZADA. Todos los límites de VRAM, contexto y generación han sido evaluados y la arquitectura de modelos queda formalmente validada.

## Fase 1. Ingesta documental

* **Objetivo:** leer los formatos admitidos y extraer su contenido y estructura.
* **Ubicación:** `src/ingestion/`.
* **Tecnologías:**
  * BeautifulSoup: HTML.
  * markdown-it-py: Markdown.
  * Tree-sitter: código fuente.
  * PyMuPDF: Extracción rápida de PDF
  * python-docx / python-pptx: Extracción de documentos Office (`.docx`, `.pptx`)
  * Descartado:
    * Docling: PDF y documentos Office. Lamentablemente no es compatible con nuestra versión de transformers

* **Estructura de archivos y clases:**
  - `src/ingestion/base.py`: Define el modelo de datos estandarizado (`ExtractedDocument`, `DocumentMetadata`) y la interfaz abstracta lectora (`BaseReader`).
  - `src/ingestion/pipeline.py`: Contiene el orquestador (`IngestionPipeline`) encargado de mapear extensiones de archivo a su lector especializado y procesar documentos o directorios.
  - `src/ingestion/pdf_reader.py`: Lector de PDF.
  - `src/ingestion/office_reader.py`: Lector unificado o separado para archivos Office (`.docx` / `.pptx`).
  - `src/ingestion/html_reader.py`: Adaptador especializado para HTML mediante BeautifulSoup.
  - `src/ingestion/markdown_reader.py`: Adaptador especializado para Markdown mediante markdown-it-py.
  - `src/ingestion/code_reader.py`: Adaptador especializado para código fuente mediante Tree-sitter.
  - Descartado:
    - `src/ingestion/docling_reader.py`: Adaptador especializado para PDF y Office mediante Docling. Por no poder incluir Docling
* **Nota de Adaptación Tecnológica:** Se ha sustituido *Docling* por adaptadores especializados ligeros (`pymupdf`, `python-docx` y `python-pptx`) para garantizar una compatibilidad estricta con Python 3.11, el ecosistema CUDA y los límites de hardware locales sin conflictos de dependencias.

* **Resultado:** Colección de objetos `ExtractedDocument` unificados con metadatos de procedencia, listos para la fase de chunking.
* **Estado de la fase:** FINAL


## Fase 2. Procesamiento y chunking (Completada)
* **Objetivo:** Normalizar los documentos y generar chunks coherentes con su estructura y tipo de contenido, preservando la trazabilidad de líneas, secciones y metadatos de procedencia.
* **Ubicación:** `src/processing/`
* **Tecnologías:** 
  - **Recursive Text Splitting:** Estrategia recursiva basada en jerarquía de encabezados y delimitadores para prosa y documentación (configurada con tamaño objetivo, límite máximo y solapamiento / *overlap*).
  - **Tree-sitter (`tree-sitter-python`):** Análisis de Árboles de Sintaxis Abstracta (AST) para fragmentar código fuente respetando los límites lógicos de funciones, métodos y clases.
* **Estructura de archivos implementada:**
  - `src/processing/base.py`: Modelo de datos estandarizado (`Chunk`, `ChunkMetadata`) y contrato abstracto (`BaseChunker`).
  - `src/processing/text_splitter.py`: Chunker recursivo para documentación y texto plano con extracción contextual de encabezados.
  - `src/processing/code_splitter.py`: Chunker basado en AST para código fuente en Python.
* **Resultado:** Generación de fragmentos estandarizados y trazables equipados con metadatos de contexto (líneas de inicio/fin, nombres de sección, elementos contenedores y lenguaje), validados mediante la suite de pruebas unitarias (`tests/test_processing.py`).

## Fase 3. Embeddings e indexación

* **Objetivo:** generar embeddings de los chunks y almacenarlos junto con sus metadatos.
* **Ubicación:** `src/embeddings/` y `data/indexes/`.
* **Tecnologías:** `intfloat/multilingual-e5-small` (ejecutado inicialmente en CPU), Sentence Transformers, PyTorch y Qdrant.
* **Datos:** documentos originales en `data/documents/`.
* **Estado:**
* Pendiente: validar la calidad de los embeddings de `intfloat/multilingual-e5-small` y su comportamiento en la recuperación de documentación técnica y código fuente.


* **Resultado:** índice vectorial local consultable y persistente.

## Fase 4. Recuperación y fusión

* **Objetivo:** recuperar candidatos mediante búsqueda semántica y léxica y combinar los resultados para construir el contexto de generación.
* **Ubicación:** `src/retrieval/`.
* **Tecnologías:** Qdrant, rank-bm25 y Reciprocal Rank Fusion (RRF).
* **Notas de arquitectura:** el componente de reranking se excluye de la versión inicial; solo se reconsiderará como posible mejora futura condicionada a los resultados obtenidos en la fase de evaluación.
* **Resultado:** fragmentos recuperados y fusionados listos para construir el contexto de generación.

## Fase 5. Generación y gestión del contexto

* **Objetivo:** construir el prompt, incorporar historial y contexto RAG, ejecutar el LLM residente en GPU y validar las referencias documentales.
* **Ubicación:** `src/generation/`.
* **Tecnologías:** Qwen2.5-Coder-1.5B-Instruct (único modelo neuronal en GPU, cuantización NF4 y FP16), Hugging Face Transformers, PyTorch, bitsandbytes, CUDA y LangChain.
* **Resultado:** respuestas generadas con referencias a los fragmentos utilizados.

## Fase 6. Evaluación

* **Objetivo:** implementar el conjunto de evaluación y medir Retrieval (semántica, léxica e híbrida), Generation y End-to-End.
* **Ubicación:** `tests/` para los casos y pruebas; los componentes propios del pipeline de evaluación se ubicarán en `src/evaluation/`.
* **Tecnologías:** Python y métricas implementadas inicialmente en el proyecto. Ragas o DeepEval podrán estudiarse como complementos.
* **Estado:**
* Incluye la evaluación comparativa de la recuperación de `intfloat/multilingual-e5-small` frente a la búsqueda léxica e híbrida.
* Se contempla la posibilidad de comparar los resultados con y sin reranking si en el futuro se decide evaluar un modelo de reranking.


* **Resultado:** ejecuciones reproducibles y resultados en JSON que permitan comparar configuraciones.

## Fase 7. API backend

* **Objetivo:** exponer el motor RAG mediante una API independiente de los clientes.
* **Ubicación:** `src/api/`.
* **Tecnologías:** FastAPI, REST y Server-Sent Events (SSE).
* **Resultado:** API capaz de gestionar solicitudes y coordinar el acceso al motor RAG.

## Fase 8. Interfaz web

* **Objetivo:** desarrollar la aplicación web para gestionar proyectos y conversaciones e interactuar con el asistente.
* **Ubicación:** `frontend/`.
* **Tecnologías:** React y Vite.
* **Comunicación:** API REST y SSE.
* **Resultado:** interfaz web conectada al backend.

---

### Resumen de la actualización

**1. Cambios realizados:**

* **Fase 0:** Se documentó formalmente la prueba conjunta de los tres modelos de la familia Qwen y el desglose de consumo de VRAM (~3,37 GB asignados, VRAM libre cercana a 0 GB). Se especificó la razón técnica de la desestimación de esta carga simultánea en la GPU de 4 GB.
* **Fase 3:** Se actualizó el modelo de embeddings a `intfloat/multilingual-e5-small`, indicando su ejecución inicial en CPU.
* **Fase 4:** Se renombró la fase a "Recuperación y fusión", eliminando `Qwen3-Reranker-0.6B` y `CrossEncoder` de las tecnologías activas y redefiniendo el objetivo en torno a la búsqueda semántica, léxica (BM25) y su fusión (RRF).
* **Fase 5:** Se ratificó que `Qwen2.5-Coder-1.5B-Instruct` (NF4/FP16) es el único modelo neuronal residente en GPU.
* **Fase 6:** Se adaptó la evaluación para contemplar la comparación de recuperación semántica, léxica e híbrida, así como la eventual prueba del reranking en el futuro.

**2. Decisiones reflejadas:**

* La convivencia de los tres modelos en GPU es viable para pruebas aisladas, pero inviable para producción por falta de margen de memoria.
* Selección de `intfloat/multilingual-e5-small` en CPU como primera opción de embeddings.
* Exclusión del reranking en la implementación inicial.
* Mantenimiento íntegro del enfoque de recuperación híbrida (Qdrant + BM25 + RRF + LangChain).

**3. Tareas que continúan pendientes:**

* Evaluar los límites prácticos de contexto y generación del modelo generador en el hardware disponible (Fase 0).
* Validar la calidad de recuperación y representación de `intfloat/multilingual-e5-small` en código y documentos técnicos (Fase 3 y Fase 6).