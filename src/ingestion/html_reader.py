"""Adaptador de ingesta para archivos HTML utilizando BeautifulSoup."""

from pathlib import Path
import uuid
from bs4 import BeautifulSoup

from .base import BaseReader, DocumentMetadata, ExtractedDocument


class HTMLReader(BaseReader):
  """Lector especializado en archivos HTML mediante BeautifulSoup."""

  def read(self, file_path: Path) -> ExtractedDocument:
    """Procesa un archivo HTML y devuelve un ExtractedDocument unificado."""
    path = Path(file_path)
    if not path.exists():
      raise FileNotFoundError(f"El archivo no existe: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
      html_content = f.read()

    # Parseamos con BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Eliminamos elementos no deseados para dejar el texto limpio
    for element in soup(["script", "style", "nav", "footer", "header"]):
      element.decompose()

    # Extraemos el texto plano o preservando saltos básicos
    raw_content = soup.get_text(separator="\n", strip=True)

    document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, path.as_uri()))

    metadata = DocumentMetadata(
        format=path.suffix.lower(),
        extra_info={
            "title": soup.title.string if soup.title else None,
        },
    )

    return ExtractedDocument(
        document_id=document_id,
        source=str(path.resolve()),
        content_type="documentation",
        raw_content=raw_content,
        language="html",
        metadata=metadata,
    )