"""Orquestador principal del pipeline de ingesta documental."""

from pathlib import Path
from typing import Dict, List, Union
from .base import BaseReader, ExtractedDocument


class IngestionPipeline:
  """Pipeline para la detección automática y procesamiento de archivos o directorios."""

  def __init__(self, readers: Dict[str, BaseReader] = None):
    """Inicializa el pipeline registrando los adaptadores por extensión.

    Args:
        readers: Diccionario opcional que mapea extensiones (ej. '.pdf') a su lector BaseReader.
    """
    self.readers: Dict[str, BaseReader] = readers or {}

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

    return reader.read(path)

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