# TECH_STACK.md

# Local LLM & RAG

## 1. Objetivo del proyecto

Desarrollar un asistente de programación basado en un Large Language Model (LLM) ejecutado localmente, complementado con un sistema Retrieval-Augmented Generation (RAG).

El objetivo del RAG es proporcionar al modelo acceso a documentación técnica, código fuente y otros documentos introducidos por el usuario, permitiéndole generar respuestas fundamentadas en información externa a sus conocimientos originales.

### Principios del proyecto

- **Local first:** tanto los modelos como el procesamiento de documentos y la recuperación de información se ejecutarán localmente.
- **Open source:** priorizar tecnologías y librerías de código abierto.
- **Modularidad:** mantener independientes la ingesta, el procesamiento, la recuperación y la generación.
- **Control:** evitar depender innecesariamente de abstracciones que oculten el funcionamiento interno del RAG.
- **Especialización:** optimizar la recuperación de información para tareas de programación y consulta de documentación técnica.

## 2. Tecnologías principales

### 2.1. Lenguaje y entorno de ejecución

- **Python:** lenguaje principal del proyecto.
- **PyTorch:** framework de aprendizaje profundo y ejecución de modelos.
- **CUDA:** aceleración por GPU cuando el hardware lo permita.
- **Hugging Face Transformers:** carga e inferencia de modelos generativos.

### 2.2. Modelo generativo

**Qwen/Qwen2.5-Coder-1.5B-Instruct**

Se utilizará como modelo generativo inicial del asistente, por su especialización en programación y su tamaño, adecuado como punto de partida para la GPU disponible (NVIDIA GTX 1060 de portátil con 4 GB de VRAM).

Configuración inicial prevista:

- **Cuantización:** 4 bits NF4 mediante bitsandbytes.
- **Tipo de cómputo:** FP16.
- **Dispositivo:** GPU mediante CUDA, sin CPU offloading.
- **Longitud de contexto inicial:** 4.096 tokens.
- **Licencia:** Apache 2.0.

Esta configuración queda pendiente de validación mediante una prueba real de carga e inferencia en el hardware objetivo. Qwen2.5-Coder-3B-Instruct se mantiene como candidato experimental para futuras comparaciones, no como modelo seleccionado.

### 2.3. Framework RAG

**LangChain**

Responsable de coordinar los componentes del sistema RAG.

Se utilizará para integrar los distintos procesos de ingesta, recuperación y generación, así como para gestionar la interacción entre el contexto recuperado y el LLM.

La lógica específica del proyecto deberá mantenerse desacoplada de LangChain siempre que sea razonable.

## 3. Ingesta y procesamiento documental

El sistema admitirá distintos formatos de entrada. Se utilizarán herramientas especializadas según el tipo de documento.

| Formato | Tecnología | Responsabilidad |
|---|---|---|
| PDF y documentos Office | Docling | Extracción de contenido y estructura documental. |
| HTML | BeautifulSoup | Análisis del DOM y extracción del contenido relevante. |
| Markdown | markdown-it-py | Análisis y conservación de la estructura Markdown. |
| Código fuente | Tree-sitter | Análisis sintáctico y extracción de estructuras de código. |

### Criterios de procesamiento

- Preservar la estructura original siempre que sea posible.
- Mantener la procedencia de cada fragmento.
- Conservar metadatos relevantes, como nombre del archivo, formato, lenguaje de programación y ubicación dentro del documento.
- Evitar divisiones arbitrarias que separen elementos semánticamente relacionados.
- Utilizar estrategias de chunking adaptadas al tipo de contenido.

El resultado de la ingesta será una representación común de documentos y fragmentos, independiente del formato original.


### Estrategia de chunking

Se utilizará una estrategia de chunking híbrida, adaptada a la naturaleza del contenido. El código fuente y la documentación seguirán procesos de fragmentación diferentes, pero producirán una representación común de chunks.

#### Código fuente

**Estrategia: AST-based chunking mediante Tree-sitter.**

La fragmentación utilizará la estructura sintáctica del código para evitar divisiones arbitrarias.

Criterios:

- Cada función o método constituirá inicialmente un chunk independiente.
- Las clases pequeñas se conservarán en un único chunk cuando su tamaño lo permita.
- Las clases grandes se dividirán por métodos, conservando la relación con su clase contenedora.
- Las funciones y métodos que superen el tamaño máximo se dividirán respetando la estructura sintáctica siempre que sea posible.
- No se aplicará overlap por defecto.
- Se conservarán las referencias al archivo original y a las líneas de código correspondientes.

#### Documentación

**Estrategia: Recursive Text Splitting adaptado a la estructura documental.**

La fragmentación tendrá en cuenta la jerarquía y organización del documento.

Criterios:

- Priorizar la división por secciones y encabezados.
- Agrupar párrafos relacionados.
- Mantener listas y bloques de código unidos cuando sea posible.
- Dividir las secciones demasiado grandes por párrafos.
- Aplicar overlap únicamente cuando sea necesario para preservar la continuidad entre fragmentos.
- Conservar la jerarquía de encabezados y la procedencia del contenido.

Parámetros iniciales:

- **Tamaño objetivo:** 500 tokens.
- **Tamaño máximo:** 800 tokens.
- **Overlap:** 80 tokens.
- **Unidad de división:** secciones, párrafos y elementos estructurales.

Estos valores son iniciales y podrán ajustarse mediante la evaluación del sistema RAG.

#### Contexto y metadatos

Cada chunk conservará información sobre su procedencia y contexto estructural.

Se utilizará una representación común con los siguientes campos:

| Campo | Descripción |
|---|---|
| `chunk_id` | Identificador único del fragmento. |
| `document_id` | Identificador del documento de origen. |
| `content` | Contenido del fragmento. |
| `source` | Ruta del archivo original. |
| `content_type` | Tipo de contenido: `code` o `documentation`. |
| `language` | Lenguaje de programación o idioma, cuando corresponda. |
| `start_line` | Línea inicial, cuando esté disponible. |
| `end_line` | Línea final, cuando esté disponible. |
| `section` | Sección o elemento estructural al que pertenece. |
| `parent` | Clase, sección o elemento contenedor, cuando corresponda. |

El contexto adicional se conservará preferentemente mediante metadatos. Cuando aporte información relevante para la recuperación semántica, podrá incorporarse también al texto utilizado para generar el embedding.

Los metadatos permitirán localizar el contenido original, reconstruir su contexto y aplicar filtros durante la recuperación.

#### Consideraciones generales

- El tamaño de los chunks deberá ser compatible con los límites de los modelos de embeddings y reranking.
- La longitud máxima de entrada del Cross-Encoder incluirá tanto la consulta como el fragmento.
- Se evitará duplicar contenido innecesariamente.
- La fragmentación deberá preservar la coherencia semántica y estructural.


## 4. Embeddings

**Modelo: `Qwen/Qwen3-Embedding-0.6B`**

Se utilizará como modelo inicial para transformar documentos y consultas en representaciones vectoriales. Se selecciona por su capacidad multilingüe y su adecuación a tareas de recuperación que combinan código fuente, documentación técnica y consultas en lenguaje natural.

Configuración inicial prevista:

- **Biblioteca:** Sentence Transformers.
- **Backend:** PyTorch.
- **Precisión:** FP16.
- **Dispositivo:** GPU mediante CUDA.
- **Dimensiones de salida:** 1.024.
- **Batch size inicial:** 1-4, sujeto a validación de memoria.
- **Contexto máximo del modelo:** hasta 32.768 tokens.
- **Licencia:** Apache 2.0.

La configuración queda pendiente de una prueba real de carga e inferencia en la NVIDIA GTX 1060 de 4 GB de VRAM. El tamaño de los fragmentos y el contexto efectivo de recuperación se definirán posteriormente en la decisión de chunking.

La generación de embeddings será independiente del modelo generativo. La selección de este modelo no implica utilizar embeddings distintos para código y documentación: inicialmente ambos tipos de contenido compartirán el mismo espacio vectorial.

## 5. Almacenamiento vectorial

**Qdrant**

Base de datos vectorial encargada de almacenar los embeddings y permitir su recuperación mediante búsquedas de similitud.

Responsabilidades:

- Almacenamiento de vectores.
- Gestión de metadatos.
- Búsqueda por similitud semántica.
- Filtrado de resultados mediante metadatos.
- Persistencia local de los índices.

Qdrant podrá ejecutarse localmente sin necesidad de utilizar servicios externos.

## 6. Sistema de recuperación (Retrieval)

El sistema utilizará una estrategia de búsqueda híbrida para mejorar la recuperación de información técnica.

### 6.1. Búsqueda semántica

Se utilizarán los embeddings y Qdrant para recuperar fragmentos relacionados semánticamente con la consulta.

### 6.2. Búsqueda léxica

**rank-bm25**

Se utilizará para recuperar documentos mediante coincidencias léxicas.

Resulta especialmente útil para búsquedas de identificadores, nombres de clases, métodos, variables y términos técnicos concretos.

### 6.3. Búsqueda híbrida y combinación de resultados

Se utilizará **Reciprocal Rank Fusion (RRF)** para combinar los resultados de la búsqueda semántica y léxica.

Cada buscador recuperará inicialmente sus 20 fragmentos más relevantes:

- Qdrant: búsqueda semántica mediante embeddings.
- BM25: búsqueda léxica mediante coincidencia de términos.

Los rankings se combinarán mediante RRF, utilizando la siguiente fórmula:

\[
RRF(d)=\sum_{r \in R}\frac{1}{k+rank_r(d)}
\]

Configuración inicial:

- **Algoritmo:** Reciprocal Rank Fusion.
- **Constante:** \(k=60\).
- **Pesos:** iguales para ambos buscadores.
- **Resultados por buscador:** 20.
- **Resultados fusionados:** 20.

Los fragmentos duplicados se identificarán mediante su `chunk_id` y se combinarán en una única entrada del ranking.

El resultado de esta fase será un conjunto de 20 candidatos ordenados por relevancia híbrida, que se enviarán al Cross-Encoder para su reranking.


### 6.4. Reranking

**Modelo: `Qwen/Qwen3-Reranker-0.6B`**

Se utilizará para volver a ordenar los fragmentos recuperados durante la fase de búsqueda híbrida, evaluando conjuntamente la consulta original y cada fragmento candidato.

Se selecciona por su capacidad multilingüe y su adecuación a tareas de recuperación de código fuente y documentación técnica.

Configuración inicial prevista:

- **Biblioteca:** Sentence Transformers.
- **Clase:** CrossEncoder.
- **Backend:** PyTorch.
- **Precisión:** FP16.
- **Dispositivo:** GPU mediante CUDA.
- **Batch size inicial:** 1.
- **Longitud máxima inicial:** 1.024 tokens por pareja consulta-documento.
- **Licencia:** Apache 2.0.

La configuración queda pendiente de una prueba real de carga e inferencia en la NVIDIA GTX 1060 de 4 GB de VRAM.

El objetivo es proporcionar al LLM únicamente los fragmentos más relevantes, mejorando la calidad del contexto utilizado durante la generación.

La gestión de memoria deberá contemplar que el modelo generativo, el modelo de embeddings y el Cross-Encoder no tienen por qué permanecer cargados simultáneamente en GPU.

## 7. Arquitectura general

El flujo principal del sistema será:

1. **Ingesta:** recepción de documentos y código fuente.
2. **Procesamiento:** extracción y normalización del contenido.
3. **Chunking:** división del contenido en fragmentos semánticamente coherentes.
4. **Embeddings:** generación de representaciones vectoriales.
5. **Indexación:** almacenamiento de vectores y metadatos en Qdrant.
6. **Retrieval:** recuperación híbrida de fragmentos relevantes.
7. **Reranking:** clasificación de los fragmentos recuperados.
8. **Generación:** incorporación del contexto seleccionado al prompt del LLM.
9. **Respuesta:** generación de una respuesta fundamentada en el contexto disponible.

## 8. Stack tecnológico consolidado

| Componente | Tecnología |
|---|---|
| Lenguaje | Python |
| Framework RAG | LangChain |
| Deep Learning | PyTorch |
| Inferencia LLM | Hugging Face Transformers |
| Modelo generativo | Qwen2.5-Coder-1.5B-Instruct |
| Cuantización LLM | bitsandbytes (NF4, 4 bits) |
| Aceleración | CUDA |
| PDF / Office | Docling |
| HTML | BeautifulSoup |
| Markdown | markdown-it-py |
| Código fuente | Tree-sitter |
| Modelo de embeddings | Qwen3-Embedding-0.6B |
| Biblioteca de embeddings | Sentence Transformers |
| Vector Database | Qdrant |
| Búsqueda léxica | rank-bm25 |
| Modelo de reranking | Qwen3-Reranker-0.6B |
| Biblioteca de reranking | Sentence Transformers (CrossEncoder) |

## 9. Decisiones pendientes

Las siguientes cuestiones quedan fuera del alcance de este documento y deberán resolverse en sus correspondientes fases de desarrollo:

- Diseño de prompts y gestión del contexto.
- Interfaz de usuario y comunicación con el sistema.
- Estrategia de evaluación de la calidad del RAG.

Estas decisiones deberán documentarse cuando se adopten, evitando introducir dependencias o funcionalidades futuras sin una necesidad concreta.