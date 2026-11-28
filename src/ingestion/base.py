"""Modelo de datos común e interfaz abstracta para la ingesta documental."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union


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
  source: str  # Ruta relativa (posix) a la raíz de ingesta cuando el pipeline tiene base_dir
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


def relative_source(file_path: Union[str, Path], base_dir: Union[str, Path]) -> str:
  """Ruta de `file_path` relativa a `base_dir`, siempre con separador '/'.

  Usar siempre '/' hace que el mismo archivo tenga el mismo `source` en
  Windows y en Linux.

  Raises:
      ValueError: si el archivo está fuera de `base_dir`.
  """
  resolved = Path(file_path).resolve()
  base = Path(base_dir).resolve()
  try:
    return resolved.relative_to(base).as_posix()
  except ValueError:
    raise ValueError(f"{resolved} está fuera de la raíz de ingesta {base}") from None


def document_id_from_source(source: str) -> str:
  """`document_id` determinista a partir de la ruta relativa.

  No depende de la carpeta donde viva el proyecto: mover la raíz de datos no
  cambia el identificador, así que `delete_by_document` limpia lo anterior.
  """
  return str(uuid.uuid5(uuid.NAMESPACE_URL, f"local-llm-rag:{source}"))