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

- **Python:** lenguaje principal del proyecto. La versión se gestiona mediante `uv` y se fija en `.python-version`.
- **uv:** gestor de entorno y dependencias. `pyproject.toml` define las dependencias del proyecto y `uv.lock` conserva las versiones resueltas.
- **PyTorch:** framework de aprendizaje profundo y ejecución de modelos.
- **CUDA:** aceleración por GPU. La instalación validada de PyTorch utiliza el runtime CUDA 13.0 (`cu130`).
- **Hugging Face Transformers:** carga e inferencia de modelos generativos.
- **bitsandbytes:** cuantización NF4 de 4 bits para modelos compatibles.

El entorno de desarrollo actual utiliza Windows 11. El entorno virtual local se encuentra en `.venv/` y no debe versionarse.

### 2.2. Hardware objetivo

El desarrollo y las pruebas del sistema se realizarán inicialmente sobre el siguiente hardware:

| Componente | Especificación |
|---|---|
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| Arquitectura | NVIDIA Ampere, Compute Capability 8.6 |
| VRAM | 4 GB |
| RAM | 16 GB (15,7 GB utilizables, según la configuración registrada) |
| Sistema operativo | Windows 11 |

Estas especificaciones constituyen el entorno de referencia para seleccionar y validar los modelos y sus configuraciones de ejecución.

#### Entorno de ejecución validado

| Componente | Versión / resultado |
|---|---|
| Gestor de dependencias | uv 0.12.7 |
| PyTorch | 2.14.1+cu130 |
| Runtime CUDA de PyTorch | 13.0 |
| CUDA disponible en PyTorch | Sí (`torch.cuda.is_available() == True`) |
| NumPy | 2.4.6 |
| bitsandbytes | 0.50.2 |
| Operación FP16 en GPU | Validada |
| Capa lineal NF4 en GPU | Validada |

La capacidad CUDA de la GPU se ha comprobado como `(8, 6)`. Se han validado operaciones PyTorch FP16, una capa NF4 y la carga e inferencia del modelo generativo seleccionado en la GPU.

Las versiones de `transformers` y `accelerate` no se registran aquí porque todavía no se ha documentado su versión instalada.

### 2.3. Modelo generativo

**Qwen/Qwen2.5-Coder-1.5B-Instruct**

Se utilizará como modelo generativo inicial del asistente, por su especialización en programación y su tamaño, adecuado como punto de partida para el hardware disponible.

Configuración inicial prevista:

- **Cuantización:** 4 bits NF4 mediante bitsandbytes.
- **Tipo de cómputo:** FP16.
- **Dispositivo:** GPU mediante CUDA, sin CPU offloading.
- **Longitud de contexto inicial:** 4.096 tokens.
- **Licencia:** Apache 2.0.

La carga e inferencia de `Qwen/Qwen2.5-Coder-1.5B-Instruct` se han validado correctamente en la GPU objetivo utilizando cuantización NF4 de 4 bits y cálculo FP16, sin CPU offloading. La prueba ha generado código correctamente y ha registrado un pico de memoria asignada por PyTorch de aproximadamente 1,15 GB. Esta medición no representa necesariamente el consumo total de VRAM del proceso. La validación confirma que el modelo puede ejecutarse en el hardware disponible, aunque todavía queda pendiente evaluar la convivencia con los modelos de embeddings y reranking. Qwen2.5-Coder-3B-Instruct se mantiene como candidato experimental para futuras comparaciones, no como modelo seleccionado.
### 2.4. Framework RAG

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

La carga e inferencia del modelo se han validado correctamente en la NVIDIA RTX 3050 Laptop de 4 GB de VRAM mediante Sentence Transformers, utilizando FP16 y CUDA.

La prueba generó embeddings de dimensión 1.024 para dos entradas de prueba (texto en español y código Python), con un pico de memoria asignada por PyTorch de aproximadamente 1,12 GB.

La validación confirma el funcionamiento técnico del modelo en el hardware disponible. La calidad semántica de los embeddings queda pendiente de evaluación mediante un conjunto de consultas y documentos representativos del proyecto.

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

La carga e inferencia del modelo se han validado correctamente en la NVIDIA RTX 3050 Laptop de 4 GB de VRAM mediante Sentence Transformers (CrossEncoder), utilizando FP16 y CUDA.

La prueba se realizó con una longitud máxima de 1.024 tokens y batch size 1. Se comprobó la capacidad del modelo para ordenar tres documentos de prueba según su relevancia respecto a una consulta. El pico de memoria asignada por PyTorch fue de aproximadamente 1,12 GB.

La validación confirma el funcionamiento técnico del modelo en el hardware disponible. La calidad del reranking deberá evaluarse posteriormente mediante un conjunto de consultas y documentos representativos del proyecto.

El objetivo es proporcionar al LLM únicamente los fragmentos más relevantes, mejorando la calidad del contexto utilizado durante la generación.

La gestión de memoria deberá contemplar que el modelo generativo, el modelo de embeddings y el Cross-Encoder no tienen por qué permanecer cargados simultáneamente en GPU.Las pruebas individuales han confirmado que los tres modelos pueden ejecutarse en la GPU objetivo. Sin embargo, todavía no se ha validado su convivencia simultánea ni el consumo conjunto de memoria. Se estudiará una estrategia de carga y descarga de modelos según las necesidades de cada operación.

## 7. Diseño de prompts y gestión del contexto

El sistema utilizará una estructura de prompts común para todos los proyectos, con instrucciones específicas según el modo de funcionamiento seleccionado.

El objetivo es proporcionar al modelo instrucciones claras sobre su papel, el uso de la información recuperada mediante RAG y el tratamiento del historial de conversación.

### 7.1. Modos de funcionamiento

El asistente dispondrá de dos modos de funcionamiento:

**PROGRAMMER**

El asistente actuará como programador y estará orientado a ejecutar tareas de desarrollo.

Responsabilidades:
- Implementar funcionalidades solicitadas.
- Generar y modificar código.
- Resolver problemas de programación.
- Proporcionar soluciones funcionales a las tareas planteadas.

**CONSULTANT**

El asistente actuará como consultor técnico y estará orientado a ayudar al usuario a desarrollar sus propias soluciones.

Responsabilidades:
- Explicar conceptos y tecnologías.
- Recomendar bibliotecas, herramientas y patrones de diseño.
- Resolver dudas técnicas.
- Orientar al usuario durante el desarrollo sin implementar directamente las soluciones por defecto.

El modo de funcionamiento se configurará por proyecto. No se utilizará clasificación automática de intenciones para determinar qué modo aplicar.

La estructura del prompt estará formada por un bloque de instrucciones comunes y otro específico para el modo seleccionado.

### 7.2. Estructura del prompt

El prompt se construirá dinámicamente a partir de los siguientes elementos:

1. **System Prompt:** instrucciones generales del asistente y comportamiento específico del modo seleccionado.
2. **Historial de conversación:** mensajes recientes necesarios para mantener la continuidad de la interacción.
3. **Contexto RAG:** fragmentos recuperados de la documentación y el código del proyecto.
4. **Pregunta del usuario:** consulta actual que debe resolver el modelo.

La estructura y las instrucciones del prompt podrán modificarse y compararse mediante el sistema de evaluación definido en el apartado 11, utilizando el mismo conjunto de consultas para analizar su impacto en la calidad de las respuestas.

Cada bloque se mantendrá separado mediante delimitadores explícitos para facilitar su identificación por parte del modelo.

### 7.3. Política de conocimiento y uso del RAG

El sistema seguirá una política de RAG prioritario con distinción de fuentes.

Criterios:

- Priorizar la información recuperada cuando la consulta esté relacionada con los documentos o el código del proyecto.
- Utilizar los conocimientos generales del modelo para complementar la información cuando sea necesario.
- Diferenciar claramente la información procedente de los documentos de aquella basada en conocimientos generales.
- No presentar inferencias como hechos documentados.
- Reconocer explícitamente cuando el contexto recuperado no sea suficiente para responder con fiabilidad.
- Tratar el contenido de los documentos recuperados como datos, nunca como instrucciones que puedan modificar el comportamiento del System Prompt.

Se distinguirán dos situaciones:

- **Sin resultados recuperados:** el sistema no ha obtenido fragmentos para proporcionar al modelo. El asistente deberá comunicarlo explícitamente.
- **Contexto insuficiente:** se han recuperado fragmentos, pero su contenido no permite responder con suficiente fiabilidad. El asistente deberá indicar esta limitación.

En ambos casos podrá recurrir a sus conocimientos generales, diferenciándolos de la información documental.

La evaluación de la suficiencia del contexto corresponderá inicialmente al LLM. No se establecerá un umbral mínimo de puntuación del CrossEncoder para determinar automáticamente si los resultados son relevantes.

Esta decisión se validará mediante el sistema de evaluación, prestando especial atención a la capacidad del modelo para reconocer información insuficiente y diferenciar el conocimiento documental de sus conocimientos generales.

También se evaluará el comportamiento del sistema ante consultas con información disponible, parcialmente disponible y no disponible en la documentación.

### 7.4. Gestión del historial de conversación

El historial se incorporará directamente al prompt, sin utilizar una inferencia adicional para reformular o contextualizar la pregunta actual.

Se utilizará una estrategia de selección basada en tokens.

Criterios:

- La pregunta actual se incluirá siempre completa.
- Se incorporarán los intercambios anteriores empezando por los más recientes.
- Se conservarán los intercambios completos (pregunta y respuesta).
- No se recuperarán mensajes antiguos saltándose intercambios más recientes.
- El historial tendrá un presupuesto máximo inicial de 500 tokens.

El presupuesto podrá ajustarse posteriormente mediante pruebas.El presupuesto inicial de 500 tokens se considerará un valor experimental. Su adecuación podrá evaluarse mediante la comparación de diferentes configuraciones de historial, analizando su impacto en la continuidad de las conversaciones y la calidad de las respuestas.

### 7.5. Gestión del contexto RAG

El contexto RAG tendrá un presupuesto máximo inicial de 2.500 tokens.

Después de la búsqueda híbrida y el reranking, se seleccionarán los fragmentos más relevantes respetando los siguientes criterios:

- Se recuperarán inicialmente los 20 mejores candidatos de la búsqueda híbrida.
- Los candidatos se ordenarán mediante el Cross-Encoder.
- Se utilizarán como máximo cinco fragmentos para construir el contexto.
- No se establecerá inicialmente un umbral mínimo de puntuación del CrossEncoder.
- La selección respetará el presupuesto máximo de 2.500 tokens.

Si un fragmento no cabe completo en el presupuesto disponible, se intentará reducirlo respetando su estructura semántica.

Criterios de truncamiento:

- Código: conservar funciones, métodos y bloques completos siempre que sea posible.
- Documentación: conservar párrafos, listas y secciones completas siempre que sea posible.
- Si no se puede realizar un recorte coherente, se descartará el fragmento y se continuará con el siguiente candidato.

El objetivo es evitar cortes arbitrarios que puedan eliminar información necesaria para interpretar el contenido.Los límites iniciales de 2.500 tokens para el contexto RAG y un máximo de cinco fragmentos se considerarán parámetros experimentales.

Su adecuación se evaluará mediante el sistema definido en el apartado 11, analizando el impacto de diferentes presupuestos y cantidades de fragmentos sobre la calidad de la recuperación y las respuestas generadas.

Cualquier modificación de estos parámetros deberá considerar tanto los resultados de Retrieval como los de Generation y End-to-End.

#### Presupuesto global de contexto

El modelo generativo tendrá una longitud de contexto inicial de 4.096 tokens.

Los presupuestos de historial y contexto RAG son límites máximos, no cantidades que deban ocuparse obligatoriamente.

La construcción del prompt deberá respetar el límite global del modelo, teniendo en cuenta todos sus componentes:

- System Prompt e instrucciones del modo.
- Historial de conversación.
- Contexto RAG.
- Pregunta actual.
- Espacio reservado para la generación de la respuesta.

Por tanto, los límites de 500 tokens para el historial y 2.500 para el contexto RAG estarán subordinados al presupuesto global. Si no existe espacio suficiente, se reducirá el contexto incorporado respetando los criterios de selección establecidos.

### 7.6. Formato de los fragmentos recuperados

Cada fragmento incorporado al contexto tendrá un identificador temporal para permitir su referencia durante la generación de la respuesta.

Ejemplo para código:

    [DOCUMENT S1]
    Source: src/database/manager.py
    Type: code
    Language: python
    Parent: DatabaseManager
    Element: connect
    Lines: 15-32

    Content:
    ...

Para documentación, el formato podrá incluir la sección correspondiente en lugar de los metadatos específicos del código.

Los campos serán:

| Campo | Descripción |
|---|---|
| Identificador | Referencia temporal del fragmento (`S1`, `S2`, etc.). |
| Source | Ruta del archivo original. |
| Type | Tipo de contenido: `code` o `documentation`. |
| Language | Lenguaje de programación o formato del documento, cuando corresponda. |
| Parent | Clase, sección o elemento contenedor, cuando esté disponible. |
| Element | Función, método u otro elemento concreto, cuando esté disponible. |
| Lines | Rango de líneas original, cuando esté disponible. |
| Content | Contenido del fragmento. |

Estos campos se obtendrán de los metadatos persistentes de los chunks:

| Campo del contexto | Metadato persistente |
|---|---|
| Source | `source` |
| Type | `content_type` |
| Language | `language` |
| Parent | `parent` |
| Element | `section`, cuando identifique un elemento concreto de código. |
| Lines | `start_line` y `end_line` |
| Content | `content` |

En documentación, el metadato `section` podrá utilizarse para representar la sección correspondiente en el contexto.

Los identificadores temporales no sustituirán al `chunk_id` persistente almacenado en el sistema de recuperación.

Los metadatos opcionales se incluirán únicamente cuando estén disponibles y aporten información estructural.

### 7.7. Política de referencias

Las respuestas deberán utilizar referencias inline para identificar la procedencia de la información documental.

Cada referencia utilizará el identificador temporal del fragmento correspondiente.

Ejemplo:

    La conexión se establece mediante DatabaseManager,
    que utiliza un pool de conexiones [S1].

    Fuentes:
    [S1] src/database/manager.py (líneas 15-32)

El sistema deberá validar la integridad de las referencias generadas:

- Cada identificador citado deberá existir entre los fragmentos proporcionados al modelo.
- No se admitirán referencias a fragmentos inexistentes.
- La lista final de fuentes se construirá a partir de los fragmentos realmente citados.

Esta validación garantiza que las referencias apunten a fragmentos existentes, pero no verifica semánticamente que el contenido de cada fragmento respalde la afirmación asociada.La correspondencia entre las referencias y las afirmaciones realizadas se evaluará mediante la dimensión Citation Accuracy definida en el apartado 11.

La validación estructural de las referencias y la evaluación de su correspondencia semántica se considerarán comprobaciones independientes.

## 8. Interfaz de usuario y comunicación con el sistema

### 8.1. Arquitectura de interacción

El sistema dispondrá inicialmente de una aplicación web independiente para interactuar con el asistente.

La arquitectura separará la interfaz de usuario, la API de comunicación y el motor RAG, evitando dependencias entre la lógica del sistema y los clientes que lo utilicen.

Se contemplan tres componentes principales:

- **Frontend:** aplicación web encargada de gestionar la interacción con el usuario.
- **Backend:** API responsable de gestionar las solicitudes, proyectos y conversaciones, así como coordinar el acceso al motor RAG.
- **Motor RAG:** componente independiente encargado de la ingesta, recuperación, reranking y generación de respuestas.

### 8.2. Tecnologías seleccionadas

**Frontend: React + Vite**

Se utilizará React para desarrollar la interfaz de usuario y Vite como entorno de desarrollo y construcción.

La aplicación permitirá gestionar proyectos y conversaciones, enviar consultas al asistente y visualizar las respuestas generadas junto con sus referencias documentales.

**Backend: FastAPI**

Se utilizará FastAPI para implementar la API que permitirá la comunicación entre los clientes y el sistema.

Será responsable de gestionar las solicitudes, identificar los proyectos y conversaciones correspondientes y coordinar la ejecución del motor RAG.

**Comunicación: REST + Server-Sent Events (SSE)**

Se utilizará una API REST para las operaciones generales del sistema.

Para la generación de respuestas se utilizará Server-Sent Events (SSE), permitiendo transmitir progresivamente el contenido generado por el modelo al cliente.

### 8.3. Desacoplamiento e integración con clientes externos

La API se diseñará independientemente de la aplicación web, de manera que cualquier cliente compatible con sus contratos pueda utilizar el sistema.

Aunque inicialmente se desarrollará una aplicación web, la arquitectura permitirá incorporar posteriormente integraciones con entornos de desarrollo (IDE), como Visual Studio Code.

La API deberá admitir tanto consultas independientes como consultas acompañadas de contexto adicional proporcionado por el cliente.

Este contexto podrá incluir información del entorno de desarrollo, como archivos seleccionados, fragmentos de código o rutas del proyecto.

La implementación inicial se centrará en las consultas independientes. La incorporación de contexto externo se desarrollará cuando se aborde la integración con clientes adicionales.

### 8.4. Principios de diseño

La arquitectura seguirá los siguientes principios:

- **Independencia del cliente:** el backend no dependerá de ninguna interfaz concreta.
- **Desacoplamiento:** el motor RAG mantendrá su independencia respecto a FastAPI y React.
- **Contratos explícitos:** las operaciones de la API definirán formatos de entrada y salida bien establecidos.
- **Extensibilidad:** la incorporación de nuevos clientes no deberá requerir modificaciones en la lógica interna del motor RAG.
- **Ejecución local:** inicialmente, tanto el backend como los modelos y componentes del sistema se ejecutarán localmente.

La arquitectura resultante permitirá utilizar el mismo motor RAG desde diferentes interfaces sin duplicar su implementación.

## 9. Arquitectura general

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

## 10. Stack tecnológico consolidado

| Componente | Tecnología |
|---|---|
| Lenguaje | Python |
| Gestión del entorno y dependencias | uv (`pyproject.toml` + `uv.lock`) |
| Framework RAG | LangChain |
| Deep Learning | PyTorch |
| Aceleración GPU | CUDA (runtime cu130 validado) |
| Cuantización | bitsandbytes (NF4, 4 bits) |
| Utilidades numéricas | NumPy |
| Inferencia LLM | Hugging Face Transformers + Accelerate |
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

## 11. Estrategia de evaluación de la calidad del RAG

### 11.1. Objetivo

Se establecerá un sistema de evaluación que permita medir la calidad del RAG y validar experimentalmente las decisiones adoptadas en su diseño.

La evaluación cubrirá tres niveles independientes:

- **Retrieval:** capacidad del sistema para recuperar fragmentos relevantes.
- **Generation:** calidad de las respuestas generadas a partir del contexto recuperado.
- **End-to-End:** calidad del asistente en la resolución completa de las consultas.

Se combinarán métricas automáticas con evaluación humana para obtener resultados cuantitativos y cualitativos.

### 11.2. Conjunto de evaluación (Evaluation Dataset)

Se construirá un conjunto de preguntas elaboradas manualmente a partir de código fuente y documentación técnica.

Cada caso de evaluación contendrá:

| Campo | Descripción |
|---|---|
| `query` | Pregunta realizada al asistente. |
| `expected_answer` | Respuesta esperada o criterios para evaluar su corrección. |
| `relevant_chunks` | Fragmentos relevantes para responder, identificados mediante su `chunk_id` y grado de relevancia. |
| `answerable` | Indica si existe información documental suficiente para responder. |
| `category` | Categoría de la consulta. |

Los grados de relevancia de los fragmentos se establecerán inicialmente mediante la siguiente escala:

- **3:** fragmento directamente necesario para responder.
- **2:** fragmento que aporta información importante.
- **1:** fragmento relacionado, pero secundario.
- **0:** fragmento irrelevante.

El conjunto de evaluación será independiente de la implementación del RAG y podrá utilizarse para comparar diferentes configuraciones del sistema.

Se contemplarán preguntas sobre código, documentación, identificadores, consultas que combinen diferentes fuentes, preguntas ambiguas y consultas sin respuesta documental.

### 11.3. Evaluación de Retrieval

Se evaluará la capacidad de los distintos componentes de recuperación para encontrar y ordenar los fragmentos relevantes.

Se utilizarán inicialmente las siguientes métricas:

| Métrica | Objetivo |
|---|---|
| Recall@20 | Medir la proporción de fragmentos relevantes recuperados entre los 20 candidatos iniciales. |
| MRR@20 | Medir la posición del primer fragmento relevante. |
| nDCG@5 | Evaluar la calidad del ordenamiento de los cinco primeros resultados, considerando los grados de relevancia. |

Se podrá utilizar Precision@K como métrica complementaria para analizar la proporción de resultados relevantes entre los fragmentos recuperados.

La evaluación permitirá analizar las distintas etapas del proceso:

- Búsqueda semántica mediante Qdrant.
- Búsqueda léxica mediante BM25.
- Combinación de resultados mediante RRF.
- Reranking mediante Cross-Encoder.

El objetivo será identificar la aportación de cada componente y detectar posibles problemas de recuperación u ordenamiento.

### 11.4. Evaluación de Generation

Se evaluará la calidad de las respuestas generadas por el LLM y su utilización del contexto recuperado.

Se contemplarán las siguientes dimensiones:

| Dimensión | Objetivo |
|---|---|
| Correctness | Evaluar la corrección de las respuestas. |
| Faithfulness | Comprobar que las afirmaciones están respaldadas por el contexto recuperado. |
| Answer Relevance | Evaluar si la respuesta resuelve la consulta planteada. |
| Citation Accuracy | Comprobar que las referencias respaldan las afirmaciones correspondientes. |
| Abstention | Evaluar si el modelo reconoce cuándo la información disponible es insuficiente. |

Se combinarán evaluadores automáticos con revisión humana. La corrección técnica y la correspondencia entre afirmaciones y fuentes requerirán especial atención durante la evaluación manual.

Se prestará especial atención al comportamiento del modelo ante tres situaciones:

- **Información disponible:** debe responder utilizando el contexto documental.
- **Información no disponible:** debe reconocer la insuficiencia de información documental y diferenciar los posibles complementos basados en conocimientos generales.
- **Información parcialmente disponible:** debe responder únicamente a las cuestiones que pueda justificar e identificar las limitaciones del contexto.

### 11.5. Evaluación End-to-End

Se evaluará el comportamiento del sistema completo desde la recepción de la consulta hasta la generación de la respuesta.

Se analizarán las siguientes dimensiones:

- Corrección técnica de la respuesta.
- Utilidad para resolver la consulta.
- Uso adecuado de la información recuperada.
- Comportamiento ante preguntas sin respuesta documental.
- Integridad y precisión de las referencias.
- Consistencia entre diferentes ejecuciones.

La evaluación combinará resultados automáticos y revisión humana. Las métricas de cada dimensión se conservarán de forma independiente, evitando reducir la calidad global a una única puntuación.

### 11.6. Pipeline de evaluación

Se implementará un proceso de evaluación independiente del pipeline de producción.

Sus componentes serán:

1. **Evaluation Dataset:** conjunto de preguntas y resultados esperados.
2. **Evaluation Runner:** ejecutor encargado de lanzar las consultas contra una configuración determinada del sistema.
3. **Evaluation Metrics:** cálculo de las métricas de recuperación y evaluación de las respuestas.
4. **Evaluation Results:** almacenamiento de los resultados obtenidos.

Cada ejecución registrará, como mínimo:

- Identificador de la evaluación.
- Fecha de ejecución.
- Versión del dataset utilizado.
- Configuración del sistema evaluado.
- Resultados de las métricas.
- Resultados de la revisión humana, cuando exista.

Los resultados se almacenarán en formato JSON para facilitar su consulta y comparación entre diferentes ejecuciones.

### 11.7. Comparación de configuraciones

El sistema de evaluación permitirá comparar distintas configuraciones del RAG utilizando el mismo conjunto de preguntas.

Se podrán estudiar cambios en:

- Estrategias y parámetros de chunking.
- Modelos y configuraciones de embeddings.
- Búsqueda híbrida y combinación mediante RRF.
- Modelos y configuraciones de reranking.
- Estructura y contenido de los prompts.
- Presupuestos de historial y contexto RAG.
- Modelos generativos.

Para facilitar la interpretación de los resultados, los experimentos modificarán inicialmente una variable cada vez, manteniendo constantes el resto de los componentes.

Se conservarán los resultados anteriores para identificar mejoras, regresiones y posibles cambios en el comportamiento del sistema.

### 11.8. Tecnologías de evaluación

Inicialmente se priorizarán implementaciones propias para las métricas de recuperación y la gestión de los resultados.

No se incorporará obligatoriamente un framework externo de evaluación. Se podrán estudiar herramientas como Ragas o DeepEval para complementar la evaluación de generación cuando sea necesario.

La revisión humana se mantendrá como parte de la estrategia, especialmente para evaluar la corrección técnica, la utilidad de las respuestas y la correspondencia entre afirmaciones y fuentes.

La estrategia de evaluación permitirá validar progresivamente las decisiones arquitectónicas y ajustar los parámetros del RAG en función de los resultados experimentales.

## 12. Decisiones pendientes

Las siguientes cuestiones quedan fuera del alcance de este documento y deberán resolverse en sus correspondientes fases de desarrollo:

- Implementación del sistema de evaluación y preparación del conjunto inicial de pruebas.

Estas decisiones deberán documentarse cuando se adopten, evitando introducir dependencias o funcionalidades futuras sin una necesidad concreta.