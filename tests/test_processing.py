"""Pruebas unitarias para el módulo de procesamiento y chunking (Fase 2)."""

import uuid
from src.ingestion.base import DocumentMetadata, ExtractedDocument
from src.processing.code_splitter import CodeSplitter
from src.processing.text_splitter import RecursiveTextSplitter


def test_recursive_text_splitter():
  """Valida la fragmentación recursiva de documentos de prosa/Markdown."""
  markdown_content = (
      "# Título Principal\n\n"
      "Este es el primer párrafo de introducción para probar el chunker.\n\n"
      "## Sección 1\n\n"
      "Aquí tenemos más contenido dentro de la sección 1 para verificar que"
      " respeta los saltos.\n"
  )

  doc_id = str(uuid.uuid4())
  doc = ExtractedDocument(
      document_id=doc_id,
      source="/tmp/documento.md",
      content_type="documentation",
      raw_content=markdown_content,
      language="markdown",
      metadata=DocumentMetadata(format=".md"),
  )

  splitter = RecursiveTextSplitter(
      target_chunk_size=100, max_chunk_size=200, overlap=20
  )
  chunks = splitter.chunk(doc)

  assert len(chunks) > 0
  for chunk in chunks:
    assert chunk.document_id == doc_id
    assert chunk.content_type == "documentation"
    assert chunk.metadata.start_line is not None
    assert chunk.metadata.end_line is not None

  # Verificar que se capturó algún contexto de encabezado
  headings = [c.metadata.section for c in chunks if c.metadata.section]
  assert len(headings) > 0


def test_code_splitter_ast_functions():
  """Valida que CodeSplitter extraiga funciones y clases mediante AST (Tree-sitter)."""
  python_code = (
      "def sumar(a: int, b: int) -> int:\n"
      "    return a + b\n\n"
      "class Calculadora:\n"
      "    def multiplicar(self, x: int, y: int) -> int:\n"
      "        return x * y\n"
  )

  doc_id = str(uuid.uuid4())
  doc = ExtractedDocument(
      document_id=doc_id,
      source="/tmp/math_utils.py",
      content_type="code",
      raw_content=python_code,
      language="python",
      metadata=DocumentMetadata(format=".py"),
  )

  splitter = CodeSplitter(max_chunk_size=500)
  chunks = splitter.chunk(doc)

  assert len(chunks) >= 2

  sections = [c.metadata.section for c in chunks]
  assert "sumar" in sections
  assert any("Calculadora" in str(sec) for sec in sections)

  for chunk in chunks:
    assert chunk.document_id == doc_id
    assert chunk.content_type == "code"
    assert chunk.language == "python"
    assert chunk.metadata.start_line is not None
    assert chunk.metadata.end_line is not None