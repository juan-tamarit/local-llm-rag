"""Adaptador de ingesta para archivos Markdown utilizando markdown-it-py."""

from pathlib import Path
import uuid
from markdown_it import MarkdownIt

from .base import BaseReader, DocumentMetadata, ExtractedDocument


class MarkdownReader(BaseReader):
  """Lector especializado en archivos Markdown mediante markdown-it-py."""

  def __init__(self):
    self.md = MarkdownIt("commonmark")

  def read(self, file_path: Path) -> ExtractedDocument:
    """Procesa un archivo Markdown y devuelve un ExtractedDocument unificado."""
    path = Path(file_path)
    if not path.exists():
      raise FileNotFoundError(f"El archivo no existe: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
      raw_content = f.read()

    # Parseamos tokens con markdown-it-py para extraer la estructura si es necesario
    tokens = self.md.parse(raw_content)

    document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, path.as_uri()))

    metadata = DocumentMetadata(
        format=path.suffix.lower(),
        extra_info={
            "token_count_md": len(tokens),
        },
    )

    return ExtractedDocument(
        document_id=document_id,
        source=str(path.resolve()),
        content_type="documentation",
        raw_content=raw_content,
        language="markdown",
        metadata=metadata,
    )