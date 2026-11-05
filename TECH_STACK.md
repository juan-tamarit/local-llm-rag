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

## 4. Embeddings

**Sentence Transformers**

Se utilizará para transformar documentos y consultas en representaciones vectoriales.

Responsabilidades:

- Generación de embeddings.
- Representación semántica de documentos.
- Cálculo de similitud entre consultas y fragmentos.
- Ejecución de modelos Cross-Encoder para reranking.

La generación de embeddings será independiente del modelo generativo.

Se utilizará PyTorch como backend y CUDA cuando resulte conveniente.

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

### 6.3. Búsqueda híbrida

Se combinarán los resultados de la búsqueda semántica y léxica para obtener un conjunto de candidatos más completo.

### 6.4. Reranking

**CrossEncoder (Sentence Transformers)**

Se utilizará para volver a ordenar los fragmentos recuperados según su relevancia respecto a la consulta original.

El objetivo es proporcionar al LLM únicamente el contexto más relevante.

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
| Embeddings | Sentence Transformers |
| Vector Database | Qdrant |
| Búsqueda léxica | rank-bm25 |
| Reranking | CrossEncoder |

## 9. Decisiones pendientes

Las siguientes cuestiones quedan fuera del alcance de este documento y deberán resolverse en sus correspondientes fases de desarrollo:

- Selección del modelo de embeddings.
- Selección del modelo Cross-Encoder.
- Estrategia y parámetros de chunking.
- Estrategia de combinación de resultados de búsqueda híbrida.
- Diseño de prompts y gestión del contexto.
- Interfaz de usuario y comunicación con el sistema.
- Estrategia de evaluación de la calidad del RAG.

Estas decisiones deberán documentarse cuando se adopten, evitando introducir dependencias o funcionalidades futuras sin una necesidad concreta.