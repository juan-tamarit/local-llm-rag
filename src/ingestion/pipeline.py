"""Orquestador principal del pipeline de ingesta documental."""

from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional, Union

from .base import (
    BaseReader,
    ExtractedDocument,
    document_id_from_source,
    relative_source,
)


class IngestionPipeline:
  """Pipeline para la detección automática y procesamiento de archivos o directorios."""

  def __init__(
      self,
      readers: Optional[Dict[str, BaseReader]] = None,
      base_dir: Optional[Union[str, Path]] = None,
  ):
    """Inicializa el pipeline registrando los adaptadores por extensión.

    Args:
        readers: Diccionario opcional que mapea extensiones (ej. '.pdf') a su lector BaseReader.
        base_dir: Raíz de ingesta. Si se indica, `source` y `document_id` de cada
            documento se calculan a partir de la ruta relativa a esta raíz, de modo
            que no dependen de la ubicación del proyecto. Si es None se conserva lo
            que devuelva cada lector (ruta absoluta).
    """
    self.readers: Dict[str, BaseReader] = readers or {}
    self.base_dir: Optional[Path] = Path(base_dir).resolve() if base_dir else None

  def register_reader(self, extension: str, reader: BaseReader) -> None:
    """Registra o reemplaza un lector para una extensión específica."""
    ext = extension.lower()
    if not ext.startswith("."):
      ext = f".{ext}"
    self.readers[ext] = reader

  def ingest_file(self, file_path: Union[str, Path]) -> ExtractedDocument:
    """Procesa un archivo individual seleccionando el lector adecuado según su extensión."""
    path = Path(file_path)
    if not path.exists():
      raise FileNotFoundError(f"El archivo no existe: {path}")

    ext = path.suffix.lower()
    reader = self.readers.get(ext)

    if not reader:
      raise ValueError(
          f"No hay un lector registrado para archivos con extensión '{ext}'."
      )

    doc = reader.read(path)

    if self.base_dir is not None:
      source = relative_source(path, self.base_dir)
      doc = replace(doc, source=source, document_id=document_id_from_source(source))

    return doc

  def ingest_directory(
      self, dir_path: Union[str, Path], recursive: bool = True
  ) -> List[ExtractedDocument]:
    """Recorre un directorio e ingiere todos los archivos soportados."""
    path = Path(dir_path)
    if not path.is_dir():
      raise NotADirectoryError(f"La ruta especificada no es un directorio: {path}")

    pattern = "**/*" if recursive else "*"
    documents: List[ExtractedDocument] = []

    for item in path.glob(pattern):
      if item.is_file() and item.suffix.lower() in self.readers:
        documents.append(self.ingest_file(item))

    return documents