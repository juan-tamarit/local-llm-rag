"""Adaptador de ingesta para archivos PDF utilizando PyMuPDF."""

from pathlib import Path
import uuid
import pymupdf  # PyMuPDF

from .base import BaseReader, DocumentMetadata, ExtractedDocument


class PDFReader(BaseReader):
  """Lector especializado en PDF mediante PyMuPDF."""

  def read(self, file_path: Path) -> ExtractedDocument:
    """Procesa un archivo PDF y devuelve un ExtractedDocument unificado."""
    path = Path(file_path)
    if not path.exists():
      raise FileNotFoundError(f"El archivo no existe: {path}")

    # Abrimos el PDF con PyMuPDF y extraemos el texto página por página
    doc = pymupdf.open(path)
    text_chunks = []
    for page_num in range(len(doc)):
      page = doc[page_num]
      text_chunks.append(page.get_text())

    raw_content = "\n".join(text_chunks)
    document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, path.as_uri()))

    metadata = DocumentMetadata(
        format=path.suffix.lower(),
        extra_info={"page_count": len(doc)},
    )

    return ExtractedDocument(
        document_id=document_id,
        source=str(path.resolve()),
        content_type="documentation",
        raw_content=raw_content,
        language=None,
        metadata=metadata,
    )