"""Modelo de datos común e interfaz abstracta para la ingesta documental."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class DocumentMetadata:
  """Metadatos de procedencia y estructura de un documento."""

  format: str  # Extensión o tipo de formato original (p. ej., '.pdf', '.py')
  extra_info: Dict[str, Any] = field(
      default_factory=dict
  )  # Metadatos adicionales específicos del extractor


@dataclass
class ExtractedDocument:
  """Representación estandarizada de un documento extraído."""

  document_id: str
  source: str  # Ruta relativa o absoluta del archivo fuente
  content_type: str  # 'documentation' o 'code'
  raw_content: str  # Texto original completo o procesado por el parser
  language: Optional[str] = (
      None  # Lenguaje de programación o idioma del texto
  )
  metadata: DocumentMetadata = field(default_factory=DocumentMetadata)


class BaseReader(ABC):
  """Interfaz base que debe implementar todo lector/adaptador de documentos."""

  @abstractmethod
  def read(self, file_path: Path) -> ExtractedDocument:
    """Lee y procesa un archivo devolviendo un ExtractedDocument unificado.

    Args:
        file_path: Ruta al archivo que se desea ingerir.

    Returns:
        ExtractedDocument: Representación estándar del documento.
    """
    pass