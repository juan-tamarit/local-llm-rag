"""Pruebas unitarias completas para el módulo de ingesta documental (Fase 1)."""

from pathlib import Path
import pytest
from docx import Document as DocxDocument
from pptx import Presentation

from src.ingestion.base import ExtractedDocument
from src.ingestion.code_reader import CodeReader
from src.ingestion.html_reader import HTMLReader
from src.ingestion.markdown_reader import MarkdownReader
from src.ingestion.office_reader import OfficeReader
from src.ingestion.pdf_reader import PDFReader
from src.ingestion.pipeline import IngestionPipeline


def test_markdown_reader(tmp_path: Path):
  """Valida la lectura de archivos Markdown."""
  md_file = tmp_path / "test.md"
  md_file.write_text("# Título Markdown\n\nContenido de prueba.", encoding="utf-8")

  reader = MarkdownReader()
  doc = reader.read(md_file)

  assert isinstance(doc, ExtractedDocument)
  assert doc.content_type == "documentation"
  assert doc.language == "markdown"
  assert "Título Markdown" in doc.raw_content
  assert doc.metadata.format == ".md"


def test_html_reader(tmp_path: Path):
  """Valida la lectura y limpieza de archivos HTML."""
  html_file = tmp_path / "test.html"
  html_file.write_text(
      "<html><head><title>Web Test</title></head>"
      "<body><script>alert('no');</script>"
      "<h1>Cabecera</h1><p>Texto limpio.</p></body></html>",
      encoding="utf-8",
  )

  reader = HTMLReader()
  doc = reader.read(html_file)

  assert isinstance(doc, ExtractedDocument)
  assert doc.content_type == "documentation"
  assert doc.language == "html"
  assert "Cabecera" in doc.raw_content
  assert "Texto limpio." in doc.raw_content
  assert "alert" not in doc.raw_content
  assert doc.metadata.extra_info.get("title") == "Web Test"


def test_code_reader(tmp_path: Path):
  """Valida la lectura de código fuente Python."""
  py_file = tmp_path / "script.py"
  py_file.write_text("def multiplicar(a, b):\n    return a * b\n", encoding="utf-8")

  reader = CodeReader()
  doc = reader.read(py_file)

  assert isinstance(doc, ExtractedDocument)
  assert doc.content_type == "code"
  assert doc.language == "python"
  assert "def multiplicar" in doc.raw_content
  assert doc.metadata.format == ".py"


def test_office_docx_reader(tmp_path: Path):
  """Valida la lectura de archivos Word (.docx)."""
  docx_file = tmp_path / "documento.docx"
  doc_obj = DocxDocument()
  doc_obj.add_paragraph("Párrafo de prueba en Word.")
  doc_obj.save(docx_file)

  reader = OfficeReader()
  doc = reader.read(docx_file)

  assert isinstance(doc, ExtractedDocument)
  assert doc.content_type == "documentation"
  assert "Párrafo de prueba en Word." in doc.raw_content
  assert doc.metadata.format == ".docx"
  assert doc.metadata.extra_info.get("paragraph_count") == 1


def test_office_pptx_reader(tmp_path: Path):
  """Valida la lectura de presentaciones PowerPoint (.pptx)."""
  pptx_file = tmp_path / "presentacion.pptx"
  prs = Presentation()
  slide_layout = prs.slide_layouts[0]  # Título y subtítulo
  slide = prs.slides.add_slide(slide_layout)
  title = slide.shapes.title
  title.text = "Diapositiva Inicial"
  prs.save(pptx_file)

  reader = OfficeReader()
  doc = reader.read(pptx_file)

  assert isinstance(doc, ExtractedDocument)
  assert doc.content_type == "documentation"
  assert "Diapositiva Inicial" in doc.raw_content
  assert doc.metadata.format == ".pptx"
  assert doc.metadata.extra_info.get("slide_count") == 1


def test_ingestion_pipeline(tmp_path: Path):
  """Valida el orquestador IngestionPipeline registrando múltiples lectores."""
  md_file = tmp_path / "doc.md"
  md_file.write_text("# Pipeline Test", encoding="utf-8")

  py_file = tmp_path / "code.py"
  py_file.write_text("x = 10", encoding="utf-8")

  pipeline = IngestionPipeline()
  pipeline.register_reader(".md", MarkdownReader())
  pipeline.register_reader(".py", CodeReader())

  # Ingesta por directorio completo
  docs = pipeline.ingest_directory(tmp_path)
  assert len(docs) == 2
  contents = [d.raw_content for d in docs]
  assert any("Pipeline Test" in c for c in contents)
  assert any("x = 10" in c for c in contents)