"""Fábrica del pipeline de ingesta con todos los lectores registrados."""

from pathlib import Path
from typing import Optional, Union

from .code_reader import CodeReader
from .html_reader import HTMLReader
from .markdown_reader import MarkdownReader
from .office_reader import OfficeReader
from .pdf_reader import PDFReader
from .pipeline import IngestionPipeline


def build_default_pipeline(
    base_dir: Optional[Union[str, Path]] = None,
) -> IngestionPipeline:
  """Crea un IngestionPipeline con los lectores de todos los formatos admitidos.

  Args:
      base_dir: raíz de ingesta; `source` y `document_id` se derivan de la ruta
          relativa a ella (ver IngestionPipeline).
  """
  pipeline = IngestionPipeline(base_dir=base_dir)
  pipeline.register_reader(".py", CodeReader())
  markdown = MarkdownReader()
  for ext in (".md", ".markdown"):
    pipeline.register_reader(ext, markdown)
  html = HTMLReader()
  for ext in (".html", ".htm"):
    pipeline.register_reader(ext, html)
  office = OfficeReader()
  for ext in (".docx", ".pptx"):
    pipeline.register_reader(ext, office)
  pipeline.register_reader(".pdf", PDFReader())
  return pipeline