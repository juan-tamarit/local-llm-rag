"""Pruebas unitarias para el módulo de ingesta documental (Fase 1)."""

from pathlib import Path
import pytest

from src.ingestion.base import ExtractedDocument
from src.ingestion.code_reader import CodeReader
from src.ingestion.html_reader import HTMLReader
from src.ingestion.markdown_reader import MarkdownReader
from src.ingestion.pipeline import IngestionPipeline


def test_markdown_reader(tmp_path: Path):
  """Valida que el lector de Markdown extraiga correctamente el contenido y metadatos."""
  md_file = tmp_path / "test.md"
  md_file.write_text(
      "# Título de prueba\n\nEste es un párrafo en Markdown.", encoding="utf-8"
  )

  reader = MarkdownReader()
  doc = reader.read(md_file)

  assert isinstance(doc, ExtractedDocument)
  assert doc.content_type == "documentation"
  assert doc.language == "markdown"
  assert "Título de prueba" in doc.raw_content
  assert doc.metadata.format == ".md"


def test_html_reader(tmp_path: Path):
  """Valida que el lector de HTML limpie scripts/estilos y extraiga el texto principal."""
  html_file = tmp_path / "test.html"
  html_file.write_text(
      "<html><head><title>Página Web</title></head>"
      "<body><script>console.log('oculto');</script>"
      "<h1>Cabecera HTML</h1><p>Texto visible.</p></body></html>",
      encoding="utf-8",
  )

  reader = HTMLReader()
  doc = reader.read(html_file)

  assert isinstance(doc, ExtractedDocument)
  assert doc.content_type == "documentation"
  assert doc.language == "html"
  assert "Cabecera HTML" in doc.raw_content
  assert "Texto visible." in doc.raw_content
  # Comprobamos que el script no deseado fue eliminado por el filtro
  assert "console.log" not in doc.raw_content
  assert doc.metadata.extra_info.get("title") == "Página Web"


def test_code_reader(tmp_path: Path):
  """Valida que el lector de código fuente procese archivos Python correctamente."""
  py_file = tmp_path / "sample.py"
  py_file.write_text(
      "def sumar(a, b):\n    return a + b\n",
      encoding="utf-8",
  )

  reader = CodeReader()
  doc = reader.read(py_file)

  assert isinstance(doc, ExtractedDocument)
  assert doc.content_type == "code"
  assert doc.language == "python"
  assert "def sumar(a, b):" in doc.raw_content
  assert doc.metadata.format == ".py"


def test_ingestion_pipeline_registry(tmp_path: Path):
  """Valida el funcionamiento del pipeline registrando y procesando archivos."""
  md_file = tmp_path / "documento.md"
  md_file.write_text("# Contenido Pipeline", encoding="utf-8")

  pipeline = IngestionPipeline()
  pipeline.register_reader(".md", MarkdownReader())

  # Prueba de ingesta de archivo individual
  doc = pipeline.ingest_file(md_file)
  assert doc is not None
  assert "Contenido Pipeline" in doc.raw_content

  # Prueba de ingesta de directorio completo
  docs = pipeline.ingest_directory(tmp_path)
  assert len(docs) == 1
  assert docs[0].document_id == doc.document_id