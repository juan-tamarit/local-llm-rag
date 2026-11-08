# ARQUITECTURA.md

# Arquitectura del repositorio

El repositorio separa la documentación, el entorno Python, la aplicación web, el motor RAG, los datos y las pruebas.

## Estructura

```text
local-llm-rag/
├── .venv/                  # Entorno virtual local (no versionar)
├── .python-version         # Versión de Python fijada para el proyecto (si está creada)
├── .gitignore
├── pyproject.toml          # Metadatos y dependencias del proyecto
├── uv.lock                 # Resolución reproducible de dependencias
├── README.md
├── TECH_STACK.md
├── ARQUITECTURA.md
├── PLAN_IMPLEMENTACION.md
├── frontend/               # Aplicación web React + Vite
├── src/
│   ├── ingestion/           # Lectura y extracción de documentos
│   ├── processing/          # Normalización y chunking
│   ├── embeddings/          # Generación de embeddings
│   ├── retrieval/           # Búsqueda híbrida y reranking
│   ├── generation/          # Prompt, contexto e inferencia del LLM
│   ├── api/                 # API FastAPI
│   └── evaluation/          # Evaluación del pipeline RAG
├── data/
│   ├── documents/           # Documentos fuente
│   └── indexes/             # Índices y datos persistentes
└── tests/                   # Pruebas automatizadas y casos de evaluación
```

La estructura representa la organización prevista del proyecto. Los directorios de módulos podrán incorporarse progresivamente al implementar cada fase. Los archivos `.python-version` y `.gitignore` aparecen como parte de la estructura objetivo; conviene comprobar que ambos están creados en el repositorio local.

## Gestión del entorno Python

- `pyproject.toml` es la fuente de verdad para los metadatos y las dependencias declaradas.
- `uv.lock` registra las versiones resueltas para reproducir el entorno.
- `.python-version` fija la versión de Python utilizada por `uv`.
- `.venv/` contiene el entorno virtual local y debe permanecer fuera del control de versiones.
- `.gitignore` debe excluir, como mínimo, `.venv/`, cachés, secretos y artefactos locales que no deban versionarse.

Comandos habituales:

```powershell
uv sync       # Sincronizar el entorno con pyproject.toml y uv.lock
uv add <paquete>  # Añadir una dependencia al proyecto
uv run <comando>  # Ejecutar un comando dentro del entorno
```

No se utilizará `requirements.txt` como mecanismo principal de gestión de dependencias. Si en el futuro se necesita exportar dependencias para otra herramienta, se tratará como un artefacto derivado y no como fuente de verdad.

## Separación de responsabilidades

- **Frontend (`frontend/`):** interfaz de usuario React + Vite.
- **API (`src/api/`):** comunicación con los clientes mediante FastAPI, REST y SSE.
- **Motor RAG (`src/`):** ingesta, procesamiento, embeddings, recuperación, reranking y generación. Su lógica debe mantenerse desacoplada de la API y del frontend.
- **Datos (`data/`):** documentos originales e índices locales.
- **Pruebas (`tests/`):** pruebas automatizadas y conjunto de evaluación.

La API no dependerá de una interfaz concreta. El motor RAG podrá ser utilizado por la aplicación web y por futuros clientes compatibles con los contratos de la API.
