"""Pruebas unitarias del módulo de ingesta documental (Fase 1 y rutas relativas de la Fase 6.0)."""

import shutil
from pathlib import Path

import pytest
from docx import Document as DocxDocument
from pptx import Presentation

from src.ingestion.base import (
    ExtractedDocument,
    document_id_from_source,
    relative_source,
)
from src.ingestion.code_reader import CodeReader
from src.ingestion.factory import build_default_pipeline
from src.ingestion.html_reader import HTMLReader
from src.ingestion.markdown_reader import MarkdownReader
from src.ingestion.office_reader import OfficeReader
from src.ingestion.pdf_reader import PDFReader
from src.ingestion.pipeline import IngestionPipeline


# --------------------------------------------------------------------------
# Lectores
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def _make_tree(root: Path) -> None:
  """Crea un árbol pequeño: <root>/doc.md, <root>/code.py y <root>/guias/a.md."""
  (root / "guias").mkdir(parents=True)
  (root / "doc.md").write_text("# Pipeline Test", encoding="utf-8")
  (root / "code.py").write_text("x = 10", encoding="utf-8")
  (root / "guias" / "a.md").write_text("# A\n\ntexto", encoding="utf-8")


def _pipeline(base_dir: Path) -> IngestionPipeline:
  pipeline = IngestionPipeline(base_dir=base_dir)
  pipeline.register_reader(".md", MarkdownReader())
  pipeline.register_reader(".py", CodeReader())
  return pipeline


def test_ingestion_pipeline(tmp_path: Path):
  """Valida el orquestador registrando varios lectores e ingiriendo un directorio."""
  _make_tree(tmp_path)

  docs = _pipeline(tmp_path).ingest_directory(tmp_path)

  assert len(docs) == 3
  contents = [d.raw_content for d in docs]
  assert any("Pipeline Test" in c for c in contents)
  assert any("x = 10" in c for c in contents)
  # source relativo a la raíz y con '/', sin importar el sistema operativo
  assert {d.source for d in docs} == {"doc.md", "code.py", "guias/a.md"}


def test_source_is_relative_posix(tmp_path: Path):
  _make_tree(tmp_path)
  doc = _pipeline(tmp_path).ingest_file(tmp_path / "guias" / "a.md")
  assert doc.source == "guias/a.md"


def test_document_id_independent_of_location(tmp_path: Path):
  """Mover la raíz de datos no cambia el document_id (evita duplicar chunks al reindexar)."""
  root_a = tmp_path / "uno"
  root_b = tmp_path / "otra" / "carpeta"
  _make_tree(root_a)
  shutil.copytree(root_a, root_b)

  id_a = _pipeline(root_a).ingest_file(root_a / "guias" / "a.md").document_id
  id_b = _pipeline(root_b).ingest_file(root_b / "guias" / "a.md").document_id

  assert id_a == id_b


def test_different_files_have_different_ids(tmp_path: Path):
  _make_tree(tmp_path)
  docs = _pipeline(tmp_path).ingest_directory(tmp_path)
  assert len({d.document_id for d in docs}) == len(docs)


def test_same_name_in_different_folders_has_different_ids(tmp_path: Path):
  """Dos archivos con el mismo nombre en carpetas distintas no deben colisionar."""
  (tmp_path / "x").mkdir()
  (tmp_path / "y").mkdir()
  (tmp_path / "x" / "readme.md").write_text("# X", encoding="utf-8")
  (tmp_path / "y" / "readme.md").write_text("# Y", encoding="utf-8")

  pipeline = _pipeline(tmp_path)
  id_x = pipeline.ingest_file(tmp_path / "x" / "readme.md").document_id
  id_y = pipeline.ingest_file(tmp_path / "y" / "readme.md").document_id

  assert id_x != id_y


def test_file_outside_base_dir_is_rejected(tmp_path: Path):
  base = tmp_path / "base"
  base.mkdir()
  outside = tmp_path / "fuera.md"
  outside.write_text("# X", encoding="utf-8")

  with pytest.raises(ValueError):
    _pipeline(base).ingest_file(outside)


def test_without_base_dir_keeps_reader_output(tmp_path: Path):
  """Sin base_dir el pipeline conserva lo que devuelve el lector (ruta absoluta)."""
  _make_tree(tmp_path)
  pipeline = IngestionPipeline()
  pipeline.register_reader(".md", MarkdownReader())

  doc = pipeline.ingest_file(tmp_path / "doc.md")

  assert doc.source == str((tmp_path / "doc.md").resolve())


def test_path_helpers(tmp_path: Path):
  assert document_id_from_source("x/y.md") == document_id_from_source("x/y.md")
  assert document_id_from_source("x/y.md") != document_id_from_source("x/z.md")
  with pytest.raises(ValueError):
    relative_source(tmp_path / "a.md", tmp_path / "otra")


# --------------------------------------------------------------------------
# Fábrica
# --------------------------------------------------------------------------

def test_default_pipeline_registers_all_formats(tmp_path: Path):
  pipeline = build_default_pipeline(base_dir=tmp_path)

  assert set(pipeline.readers) == {
      ".py", ".md", ".markdown", ".html", ".htm", ".docx", ".pptx", ".pdf",
  }
  assert isinstance(pipeline.readers[".pdf"], PDFReader)
  assert pipeline.base_dir == tmp_path.resolve()