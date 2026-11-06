# Local LLM & RAG

Asistente de programación basado en un modelo de lenguaje ejecutado
localmente y complementado con un sistema Retrieval-Augmented Generation
(RAG). El sistema permite consultar documentación técnica y código
fuente propios para generar respuestas fundamentadas en ese contenido.

## Documentación del proyecto

La documentación se divide en tres documentos, cada uno con una
responsabilidad concreta:

-   **[Plan de implementación](PLAN_IMPLEMENTACION.md):** define las
    fases de desarrollo y el orden en el que deben abordarse.
-   **[Arquitectura](ARQUITECTURA.txt):** describe la organización del
    sistema, sus componentes y las relaciones entre ellos.
-   **[Stack tecnológico](TECH_STACK.md):** recoge las tecnologías,
    modelos, bibliotecas y decisiones técnicas del proyecto.

El plan indica qué construir a continuación; la arquitectura, dónde
encaja cada componente; y el stack, qué tecnologías utilizar. Estos
documentos deben mantenerse coordinados cuando cambien las decisiones
del proyecto.

## Objetivo

Construir un asistente técnico local capaz de:

-   Ingerir documentación y código fuente.
-   Procesar el contenido preservando su estructura y procedencia.
-   Recuperar información mediante búsqueda semántica y léxica.
-   Reordenar los resultados mediante reranking.
-   Generar respuestas utilizando el contexto recuperado y el modelo
    local.
-   Evaluar la calidad del sistema de recuperación y generación.

## Principios

-   **Local first:** ejecución local de modelos y procesamiento.
-   **Open source:** priorizar tecnologías y bibliotecas de código
    abierto.
-   **Modularidad:** separar ingesta, procesamiento, recuperación,
    generación e interfaz.
-   **Desacoplamiento:** mantener el motor RAG independiente de la API y
    de los clientes.
-   **Control:** evitar abstracciones innecesarias que oculten el
    funcionamiento del sistema.
-   **Especialización:** optimizar la recuperación para código fuente y
    documentación técnica.

## Arquitectura de interacción

El sistema se organiza en tres componentes principales:

-   **Motor RAG:** ingesta, procesamiento, indexación, recuperación y
    generación.
-   **Backend:** API para gestionar solicitudes y coordinar el acceso al
    motor.
-   **Frontend:** aplicación web para gestionar proyectos y
    conversaciones e interactuar con el asistente.

La interfaz se comunica con el backend mediante REST y Server-Sent
Events (SSE). El backend debe poder utilizarse desde otros clientes sin
depender del frontend.

## Estado del desarrollo

El diseño inicial del stack, la arquitectura y el orden de
implementación están documentados. El desarrollo debe continuar
siguiendo las fases definidas en
[PLAN_IMPLEMENTACION.md](PLAN_IMPLEMENTACION.md).
