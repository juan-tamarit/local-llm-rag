# PLAN_IMPLEMENTACION.md

# Plan de implementación

Orden de desarrollo del proyecto Local LLM & RAG. Cada fase indica el
módulo responsable, su ubicación y las tecnologías previstas.

## Fase 0. Preparación del entorno (Completada)

* **Objetivo:** preparar un entorno reproducible, comprobar que el hardware puede ejecutar operaciones de inferencia mediante GPU y definir la arquitectura de modelos viable para el sistema.
* **Ubicación:** raíz del proyecto.
* **Archivos principales:** `pyproject.toml`, `uv.lock`, `.python-version` y `.gitignore`. El entorno virtual se mantiene en `.venv/` y no se versiona.
* **Sistema operativo:** Windows 11.
* **Gestión del entorno:** uv.
* **Tecnologías:** Python 3.11, PyTorch, CUDA, NumPy, Hugging Face Transformers, Accelerate y bitsandbytes.
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
* Carga e inferencia de `Qwen/Qwen2.5-Coder-1.5B-Instruct` validadas correctamente en la RTX 3050 Laptop mediante cuantización NF4 de 4 bits (con `BitsAndBytesConfig`) y cálculo FP16, sin CPU offloading.
* Generación de código comprobada mediante una prueba de inferencia. Pico de memoria asignada por PyTorch: aproximadamente 1,15 GB (1,13 GB en la prueba aislada).
* Carga e inferencia individuales de `Qwen/Qwen3-Embedding-0.6B` validadas experimentalmente mediante Sentence Transformers, con FP16 y CUDA. Dimensión de salida: 1.024. Pico de memoria asignada por PyTorch: aproximadamente 1,12 GB.
* Carga e inferencia individuales de `Qwen/Qwen3-Reranker-0.6B` validadas experimentalmente mediante Sentence Transformers (CrossEncoder), con FP16 y CUDA. Longitud máxima: 1.024 tokens y batch size 1. Pico de memoria asignada por PyTorch: aproximadamente 1,12 GB.
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

## Fase 1. Ingesta documental(Completada)

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
* **Estado de la fase:** FINALIZADA.

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

## Fase 3. Embeddings e indexación (Completada)

* **Objetivo:** generar embeddings de los chunks y almacenarlos junto con sus metadatos en un índice vectorial local y persistente.
* **Ubicación:** `src/embeddings/` y `data/indexes/`.
* **Tecnologías:** `intfloat/multilingual-e5-small` (CPU, FP32), Sentence Transformers 6.2.0, PyTorch y Qdrant en modo local persistente (`qdrant-client` 1.20.0, `urllib3` 2.8.0).
* **Datos:** documentos originales en `data/documents/`; índice persistente en `data/indexes/qdrant_db/` (no se versiona).
* **Estructura de archivos implementada:**
  - `src/embeddings/embedder.py`: `Embedder`. Carga el modelo en CPU, aplica los prefijos `passage:` y `query:`, normaliza los vectores (384 dimensiones), fija `max_seq_length` en 512 tokens, avisa en el log de los fragmentos que se truncarían y expone `count_tokens()`.
  - `src/embeddings/vector_store.py`: `VectorStore` y `chunk_to_payload`. Qdrant local con distancia coseno, `add_chunks` (`upsert` por lotes), `delete_by_document`, `search` (con filtros por metadatos, mediante `query_points`), `scroll_all` (recorrido de la colección para construir BM25 en la Fase 4), `count` y `close`.
  - `tests/test_embeddings.py`: 8 pruebas unitarias, todas superadas.
* **Decisiones de implementación:**
  - Los puntos usan un UUID determinista (`uuid5`) derivado de `chunk_id`, de modo que reindexar el mismo chunk no duplica puntos.
  - Un chunk sin `chunk_id` se rechaza con un error.
  - El payload se construye a partir del `Chunk` real de `src/processing/base.py`: usa `content` (no `text`), conserva los campos del contrato y añade `format` y `extra_info`.
  - Al abrir una colección existente se comprueba que su dimensión coincida con la del modelo.
  - `close()` libera el bloqueo de la carpeta del índice, necesario en Windows.
* **Pruebas realizadas:** dimensión y normalización de los vectores, efecto de los prefijos, inserción y búsqueda, idempotencia del `upsert`, borrado por documento, filtro por `source`, persistencia tras cerrar y reabrir, y rechazo de chunks sin `chunk_id`.
* **Descartado / sustituido:**
  - `qdrant-client` 1.0.1: era la única versión resoluble, porque no admite el modo local ni `query_points`.
* **Nota de adaptación tecnológica:** el índice de PyTorch `cu130` alojaba una copia antigua de `urllib3` (1.26.13) y uv, por defecto, solo consulta el primer índice que contiene un paquete. Todas las versiones modernas de `qdrant-client` exigen `urllib3>=1.26.14`, por lo que no había solución y se resolvía la 1.0.1. Se ha declarado el índice con `explicit = true`, de modo que solo se usa para `torch`; el resto de paquetes proceden de PyPI. `torch` se mantiene en 2.14.1+cu130 con CUDA operativa.
* **Registrado en la Fase 5 (`scripts/ingest.py`, corpus de prueba de 9 archivos: los tres `.md` del proyecto y 6 archivos de `src/retrieval/`):** 180 chunks indexados, 2 de ellos sobre los 512 tokens del modelo (1,1 %, ambos funciones largas de código que se truncan al embeber) y 7,1 s de embeddings en CPU (unos 40 ms por chunk).
* **Pendiente de registrar:** resultados formales de la validación de calidad de recuperación de `intfloat/multilingual-e5-small` con código y documentación (consultas, aciertos en el top 5, casos fallidos). La comparación con BM25 y la búsqueda híbrida se realizará en la Fase 6.
* **Resultado:** índice vectorial local consultable y persistente.
* **Estado de la fase:** FINALIZADA.

## Fase 4. Recuperación y fusión (Completada)

* **Objetivo:** recuperar candidatos mediante búsqueda semántica y léxica y combinar los resultados para construir el contexto de generación.
* **Ubicación:** `src/retrieval/`.
* **Tecnologías:** Qdrant (vía `VectorStore`), `rank-bm25` (`BM25Okapi`; versión por registrar, ver `uv.lock`), Reciprocal Rank Fusion (RRF) y NumPy. La capa es Python puro, sin LangChain (aplazado, ver Fase 5 y "Líneas futuras").
* **Entradas de la Fase 3:** `VectorStore.search(query_vector, limit, filters)` para la búsqueda semántica y `VectorStore.scroll_all()` para construir el índice BM25. `Embedder.embed_queries` para vectorizar la consulta.
* **Estructura de archivos y clases implementada:**
  - `src/retrieval/base.py`: `RetrievalResult` (`chunk_id`, `score`, `payload`, `semantic_rank`, `lexical_rank`, `semantic_score`, `lexical_score`). Los rankings empiezan en 1 y valen `None` si el buscador no devolvió el fragmento.
  - `src/retrieval/tokenizer.py`: `tokenize()`, tokenizador de BM25 sensible a código. Pasa a minúsculas, elimina acentos y emite el identificador completo más sus partes (`DatabaseManager` -> `databasemanager`, `database`, `manager`; `get_user_id` -> `get_user_id`, `get`, `user`, `id`).
  - `src/retrieval/bm25_index.py`: `BM25Index`. Se construye con `VectorStore.scroll_all()`, deduplica por `chunk_id` del payload e indexa `content` junto con `parent`, `section` y el nombre del archivo. `search(query, limit, filters)` devuelve `id`, `score` y `payload`, igual que `VectorStore.search`. Los filtros (igualdad por campo del payload) se aplican tras puntuar todo el corpus, y se descartan los resultados con puntuación 0. `refresh()` reconstruye el índice y `ensure_fresh()` lo reconstruye si `count()` difiere del tamaño del corpus en memoria.
  - `src/retrieval/fusion.py`: `reciprocal_rank_fusion(rankings, k=60, weights=None, limit=20)`, función pura sin dependencias del resto del proyecto.
  - `src/retrieval/hybrid.py`: `HybridRetriever`, con `search_semantic`, `search_lexical`, `search_hybrid` y `refresh()`. La consulta se vectoriza una sola vez y el mismo `filters` se aplica a ambos buscadores. Configuración por defecto: 20 resultados por buscador, `k=60`, pesos iguales y 20 resultados fusionados.
  - `tests/test_retrieval.py`: 11 pruebas unitarias (tokenizador, RRF, `BM25Index` y `HybridRetriever` con un almacén y un embedder simulados), todas superadas.
* **Decisiones de implementación:**
  - Los tres modos se exponen por separado para que la Fase 6 pueda compararlos con el mismo código.
  - La deduplicación se hace por `chunk_id` del payload, no por el UUID del punto de Qdrant.
  - El reranking queda fuera: si se incorpora, será una etapa que se aplique sobre la salida de `search_hybrid`.
* **Limitación conocida:** `ensure_fresh()` solo detecta cambios en el número de chunks. Si se borra un documento y se indexa otro con el mismo número de chunks, hay que llamar a `refresh()` de forma explícita tras reindexar.
* **Notas de arquitectura:** el componente de reranking se excluye de la versión inicial; solo se reconsiderará como posible mejora futura condicionada a los resultados obtenidos en la fase de evaluación.
* **Resultado:** fragmentos recuperados y fusionados (`RetrievalResult`) listos para construir el contexto de generación.
* **Estado de la fase:** FINALIZADA.

## Fase 5. Generación y gestión del contexto (Completada)

* **Objetivo:** construir el prompt, incorporar historial y contexto RAG, ejecutar el LLM residente en GPU y validar las referencias documentales.
* **Ubicación:** `src/generation/`, más `src/model_paths.py`, `scripts/` y `models/`.
* **Entrada de la Fase 4:** `HybridRetriever.search_hybrid(query, limit, per_retriever, filters)` devuelve hasta 20 `RetrievalResult` ordenados por RRF; el contexto se construye a partir de su `payload`.
* **Tecnologías:** Qwen2.5-Coder-1.5B-Instruct (único modelo neuronal en GPU, cuantización NF4 y cálculo FP16, sin CPU offloading), Hugging Face Transformers (`TextIteratorStreamer` para el streaming), PyTorch, bitsandbytes y CUDA. La capa es Python puro, sin LangChain.
* **Estructura de archivos y clases implementada:**
  - `src/generation/base.py`: `Mode` (`PROGRAMMER` / `CONSULTANT`), `GenerationConfig`, `ContextChunk`, `Exchange`, `PromptParts` y `GenerationResult`.
  - `src/generation/token_counter.py`: `TokenCounter`. Cuenta con el tokenizador de Qwen (no el de e5) y mide el prompt completo con `apply_chat_template`.
  - `src/generation/language.py`: `detect_language()`, heurística ES/EN sin dependencias (por defecto, español).
  - `src/generation/prompts.py`: `build_system_prompt(mode)`, bloque común más bloque del modo. Texto en inglés; responde en el idioma de la pregunta.
  - `src/generation/context_builder.py`: `format_chunk`, `build_context` y `sanitize`. Los fragmentos se numeran `S1..Sn` de forma contigua, en orden RRF; el que no cabe en el presupuesto se descarta y se prueba el siguiente. `sanitize` neutraliza los delimitadores del prompt (`<context>`, `<question>`, `[DOCUMENT S#]`) y elimina órdenes triviales del tipo "ignora las instrucciones" (con aviso en el log).
  - `src/generation/history.py`: `select_history`. Intercambios completos, de más reciente a más antiguo; se detiene en el primero que no cabe.
  - `src/generation/prompt_builder.py`: `build_prompt`. Ajusta el prompt al presupuesto global con la plantilla real. Sin fragmentos añade un marcador y una nota de "sin documentos"; con fragmentos añade un recordatorio final con el idioma.
  - `src/generation/llm.py`: `LLM`, con `generate()` y `generate_stream()` (hilo y `TextIteratorStreamer`). Determinista por defecto (`temperature=0.0`).
  - `src/generation/citations.py`: `extract_refs` (admite `[S1]`, `[S1][S2]` y `[S1, S2]`) y `build_result`, que separa referencias válidas e inválidas y marca `uncited`.
  - `src/generation/pipeline.py`: `RAGGenerator` con `answer()` y `answer_stream()`.
  - `src/model_paths.py`: `local_model_path()`, resuelve la carpeta de cada modelo en `models/`.
  - `scripts/download_models.py`, `scripts/ingest.py`, `scripts/smoke_llm.py` y `scripts/smoke_pipeline.py`.
  - `tests/test_generation.py`: pruebas de la lógica pura, sin GPU (contexto, historial, prompt, citas, saneamiento, marca `uncited`, system prompt, idioma).
* **Parámetros por defecto (`GenerationConfig`):** contexto global 4.096 tokens, RAG 2.500, máximo 5 fragmentos, historial 500 y reserva para la respuesta 512. Todos son experimentales y se ajustarán en la Fase 6.
* **Decisiones de implementación:**
  - Los presupuestos se miden con el tokenizador de Qwen y la plantilla de chat, no con el de e5.
  - Orden de recorte bajo el presupuesto global: primero el contexto RAG, después el historial; nunca el system prompt ni la pregunta.
  - Si un fragmento no cabe se descarta; el truncamiento estructural (por bloques de código o párrafos) queda como mejora posterior.
  - Lo que se puede decidir en código se decide en código: el caso "sin resultados" lo detecta el constructor del prompt y el idioma se fija con `detect_language`, porque el modelo de 1,5B ignoraba esas reglas cuando solo estaban en el system prompt.
  - Las referencias `S#` son temporales; la lista de fuentes la construye `citations.py` con los fragmentos realmente citados y el modelo no la escribe.
  - El modo (`PROGRAMMER` / `CONSULTANT`) lo elige quien llama; `RAGGenerator` usa `CONSULTANT` por defecto.
  - No se establece umbral de relevancia: la suficiencia del contexto la decide el LLM (§7.3 de `TECH_STACK.md`).
* **Modelos locales (offline):** los modelos se descargan una sola vez a `models/` con `scripts/download_models.py` y se cargan con `local_files_only=True` desde `llm.py`, `token_counter.py` y `embedder.py`. `models/` no se versiona. Se guardan los pesos originales en FP16, porque la cuantización NF4 se aplica al cargar.
* **Mediciones registradas:**
  - System prompt: 212 tokens (`PROGRAMMER`) y 223 (`CONSULTANT`), medidos con el tokenizador de Qwen (la primera versión, más larga, ocupaba unos 425).
  - Prompts completos de las pruebas de humo: entre 289 y 355 tokens, con 0 o 1 fragmento de contexto (documentos de prueba).
  - VRAM pico asignada durante la generación: unos 1,19-1,20 GB, en línea con la Fase 0.
  - Ingesta del corpus de prueba: ver Fase 3.
* **Pruebas realizadas:** `tests/test_generation.py` (15 pruebas superadas en la última ejecución registrada; después se añadieron las del detector de idioma, recuento por registrar) y pruebas de humo con el modelo real y con el índice real.
* **Limitaciones observadas del modelo de 1,5B (llevadas a la Fase 6):**
  - Citas: en las 4 respuestas de la prueba con el índice real el modelo no citó ningún fragmento (`uncited=True`).
  - Abstención: con fragmentos irrelevantes (pregunta sobre Kubernetes, sin información en el corpus) respondió con conocimiento general sin avisar de que la documentación no lo cubría, y coló un carácter chino en el texto.
  - Copia del contexto: en una de las preguntas reprodujo los fragmentos `[DOCUMENT S#]` en lugar de redactar una respuesta.
  - Idioma: en la prueba sin recordatorio explícito respondió en inglés a preguntas en español; el idioma explícito se añadió después y no se ha medido de forma sistemática.
  - Inyección: una orden dentro de un documento fue obedecida hasta que `sanitize` la eliminó; con el saneamiento la defensa funcionó en el caso probado, y se considera básica, no infalible.
* **Observación sobre recuperación:** para "¿Qué hace HybridRetriever?" el top 5 solo contenía fragmentos de los tres `.md` y ninguno de `hybrid.py`, y la respuesta fue imprecisa. Se medirá en la Fase 6 (consultas por identificador, peso del BM25 y efecto de la longitud de los chunks de código).
* **Deuda técnica detectada:**
  - Los cinco lectores guardan en `source` la ruta absoluta y derivan `document_id` de `Path.as_uri()`, que exige rutas absolutas. Las citas muestran rutas largas de la máquina y, si el proyecto se mueve, el mismo archivo obtiene otro `document_id`, por lo que `delete_by_document` no limpia lo anterior y la reindexación duplica chunks. Corrección prevista: que el lector reciba una raíz (`base_dir`) y calcule `source` y `document_id` a partir de la ruta relativa, como cambio propio con sus pruebas.
  - `IngestionPipeline` no registra lectores por defecto: el registro está en `build_pipeline()` de `scripts/ingest.py`. Conviene moverlo al propio pipeline o a una fábrica.
* **Aplazado:** LangChain / LangGraph. No son necesarios por la sencillez del flujo actual (`retrieve -> build_prompt -> generate -> validate`), que exige control directo del presupuesto de tokens. Se reconsideran en fases futuras (ver "Líneas futuras").
* **Nota de adaptación tecnológica:** el generador se carga desde `models/` con `local_files_only=True` para que el proyecto funcione sin internet; `from_pretrained` consultaba Hugging Face en cada arranque.
* **Resultado:** `RAGGenerator` genera respuestas a partir del índice local, con referencias validadas estructuralmente y soporte de streaming para la Fase 7.
* **Estado de la fase:** FINALIZADA.

## Fase 6. Evaluación

* **Objetivo:** implementar el conjunto de evaluación y medir Retrieval (semántica, léxica e híbrida), Generation y End-to-End.
* **Ubicación:** `tests/` para los casos y pruebas; los componentes propios del pipeline de evaluación se ubicarán en `src/evaluation/`.
* **Tecnologías:** Python y métricas implementadas inicialmente en el proyecto. Ragas o DeepEval podrán estudiarse como complementos.
* **Estado:**
* Incluye la evaluación comparativa de la recuperación de `intfloat/multilingual-e5-small` frente a la búsqueda léxica e híbrida.
* Se contempla la posibilidad de comparar los resultados con y sin reranking si en el futuro se decide evaluar un modelo de reranking.


* Debe medir las limitaciones observadas en la Fase 5: citas ausentes, abstención ante contexto irrelevante, copia del contexto, idioma y recuperación por identificadores.
* Parámetros a ajustar con los resultados: reserva de 512 tokens para la respuesta, 500 de historial, 2.500 de contexto RAG y máximo de 5 fragmentos.
* Experimento previsto, variando solo el modelo: un generador mayor (por ejemplo, un 3B en NF4) si el 1,5B no cita ni se abstiene de forma aceptable. Debe comprobarse antes su encaje en 4 GB de VRAM.
* Valorar, con datos, un umbral mínimo de relevancia de recuperación que fuerce el caso "sin resultados" (hoy descartado en §7.3 de `TECH_STACK.md`).

* **Resultado:** ejecuciones reproducibles y resultados en JSON que permitan comparar configuraciones.

## Fase 7. API backend

* **Objetivo:** exponer el motor RAG mediante una API independiente de los clientes.
* **Ubicación:** `src/api/`.
* **Tecnologías:** FastAPI, REST y Server-Sent Events (SSE).
* **Entrada disponible de la Fase 5:** `RAGGenerator.answer()` y `RAGGenerator.answer_stream()` (emite `("token", str)` y `("done", GenerationResult)`). El modo local de Qdrant admite un único proceso, y `generate_stream` es un generador síncrono: habrá que ejecutarlo fuera del bucle de eventos de FastAPI.
* **Resultado:** API capaz de gestionar solicitudes y coordinar el acceso al motor RAG.

## Fase 8. Interfaz web

* **Objetivo:** desarrollar la aplicación web para gestionar proyectos y conversaciones e interactuar con el asistente.
* **Ubicación:** `frontend/`.
* **Tecnologías:** React y Vite.
* **Comunicación:** API REST y SSE.
* **Resultado:** interfaz web conectada al backend.

## Líneas futuras

* Cliente CLI y integración con VS Code, como clientes de la API de la Fase 7 (no requieren cambios en el motor RAG).
* Flujos de metodologías ágiles (user stories) y enfoque de programación orientada a modelos: flujos de varios pasos (analizar, descomponer, generar, validar, iterar) con estado, ramas y reintentos.
* Valorar LangGraph, y LangChain si aporta algo, para esos flujos. Los pasos de `src/generation/` son funciones separadas y podrían envolverse como nodos de un grafo sin reescribirse. Aplazado, no descartado.
* Rutas relativas en `source` y `document_id` (deuda técnica de la Fase 5).

---

### Resumen de la actualización

**1. Cambios realizados:**

* **Fase 5:** marcada como completada. Se documentan los archivos implementados en `src/generation/`, `src/model_paths.py` y `scripts/`, los parámetros por defecto, las mediciones (system prompt de 212-223 tokens, VRAM pico de unos 1,2 GB) y las pruebas de `tests/test_generation.py`.
* **Fase 3:** registrados los datos de la ingesta del corpus de prueba (180 chunks, 2 sobre 512 tokens, 7,1 s de embeddings en CPU).
* **Fases 6 y 7:** ajustado el alcance con lo observado en la Fase 5.
* Añadida la sección "Líneas futuras".

**2. Decisiones reflejadas:**

* LangChain / LangGraph aplazado (no descartado) por la sencillez del flujo actual.
* Presupuestos medidos con el tokenizador de Qwen y la plantilla de chat.
* Decisiones que se toman en código y no en el prompt: caso "sin resultados" e idioma.
* Saneamiento de delimitadores y de órdenes triviales dentro de los documentos.
* Modelos locales en `models/`, cargados con `local_files_only=True`.
* Mantenimiento de la exclusión del reranking en la versión inicial.

**3. Tareas que continúan pendientes:**

* Medir en la Fase 6 las limitaciones del modelo de 1,5B (citas, abstención, copia del contexto, idioma) y la recuperación por identificadores.
* Registrar el recuento actual de `tests/test_generation.py` (incluye las pruebas de idioma) y la versión de `rank-bm25` (ver `uv.lock`).
* Registrar la versión exacta de `transformers` y `accelerate` (ver `uv.lock`).
* Corregir las rutas absolutas en `source` y `document_id`.
* Comparar formalmente la recuperación semántica, léxica e híbrida (Fase 6).
