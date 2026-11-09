"""Adaptador de ingesta para documentos Office (.docx y .pptx) utilizando python-docx y python-pptx."""

from pathlib import Path
import uuid
from docx import Document as DocxDocument
from pptx import Presentation

from .base import BaseReader, DocumentMetadata, ExtractedDocument


class OfficeReader(BaseReader):
  """Lector especializado en archivos Word (.docx) y PowerPoint (.pptx)."""

  def read(self, file_path: Path) -> ExtractedDocument:
    """Procesa un archivo Office y devuelve un ExtractedDocument unificado."""
    path = Path(file_path)
    if not path.exists():
      raise FileNotFoundError(f"El archivo no existe: {path}")

    ext = path.suffix.lower()
    raw_content = ""
    extra_info = {}

    if ext == ".docx":
      doc = DocxDocument(path)
      paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
      raw_content = "\n".join(paragraphs)
      extra_info["paragraph_count"] = len(paragraphs)

    elif ext == ".pptx":
      prs = Presentation(path)
      slide_texts = []
      for slide_idx, slide in enumerate(prs.slides):
        slide_text = []
        for shape in slide.shapes:
          if shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
              slide_text.append(paragraph.text)
        slide_texts.append(
            f"--- Diapositiva {slide_idx + 1} ---\n"
            + "\n".join(slide_text)
        )
      raw_content = "\n\n".join(slide_texts)
      extra_info["slide_count"] = len(prs.slides)
    else:
      raise ValueError(f"Formato Office no soportado: {ext}")

    document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, path.as_uri()))

    metadata = DocumentMetadata(
        format=ext,
        extra_info=extra_info,
    )

    return ExtractedDocument(
        document_id=document_id,
        source=str(path.resolve()),
        content_type="documentation",
        raw_content=raw_content,
        language=None,
        metadata=metadata,
    )