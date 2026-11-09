"""Adaptador de ingesta para documentos PDF y Office utilizando Docling."""

from pathlib import Path
import uuid

from docling.document_converter import DocumentConverter

from .base import BaseReader, DocumentMetadata, ExtractedDocument


class DoclingReader(BaseReader):
  """Lector especializado en PDF y archivos Office mediante Docling."""

  def __init__(self):
    # Inicializamos el conversor de Docling
    self.converter = DocumentConverter()

  def read(self, file_path: Path) -> ExtractedDocument:
    """Procesa un archivo PDF u Office y devuelve un ExtractedDocument unificado."""
    path = Path(file_path)
    if not path.exists():
      raise FileNotFoundError(f"El archivo no existe: {path}")

    # Ejecutamos la conversión con Docling
    conversion_result = self.converter.convert(path)
    document = conversion_result.document

    # Exportamos el contenido estructurado a formato Markdown o texto plano
    # Docling permite exportar directamente a markdown preservando la estructura
    raw_content = document.export_to_markdown()

    # Generamos un identificador único para el documento basado en su ruta
    document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, path.as_uri()))

    # Recopilamos metadatos adicionales específicos de Docling si los hay
    extra_info = {
        "page_count": (
            len(document.pages) if hasattr(document, "pages") else None
        ),
    }

    metadata = DocumentMetadata(
        format=path.suffix.lower(),
        extra_info=extra_info,
    )

    return ExtractedDocument(
        document_id=document_id,
        source=str(path.resolve()),
        content_type="documentation",  # Los PDF y Office se consideran documentación técnica general
        raw_content=raw_content,
        language=None,  # Docling o etapas posteriores pueden refinar el idioma
        metadata=metadata,
    )