"""Modelo de datos común e interfaz abstracta para el procesamiento y chunking."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from src.ingestion.base import ExtractedDocument


@dataclass
class ChunkMetadata:
  """Metadatos de procedencia, contexto estructural y ubicación de un chunk."""

  format: str
  start_line: Optional[int] = None
  end_line: Optional[int] = None
  section: Optional[str] = None
  parent: Optional[str] = None
  extra_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
  """Representación estandarizada de un fragmento (chunk) de documento o código."""

  chunk_id: str
  document_id: str
  content: str
  source: str
  content_type: str  # 'documentation' o 'code'
  language: Optional[str] = None
  metadata: ChunkMetadata = field(
      default_factory=lambda: ChunkMetadata(format="")
  )


class BaseChunker(ABC):
  """Interfaz base que debe implementar todo divisor/chunker de documentos."""

  @abstractmethod
  def chunk(self, document: ExtractedDocument) -> list[Chunk]:
    """Divide un ExtractedDocument en una lista de fragmentos (chunks) estandarizados.

    Args:
        document: Objeto ExtractedDocument procedente de la fase de ingesta.

    Returns:
        list[Chunk]: Lista de fragmentos generados con su contexto y metadatos.
    """
    pass