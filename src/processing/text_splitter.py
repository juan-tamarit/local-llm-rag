"""Chunker recursivo para fragmentación de documentación y texto plano."""

from pathlib import Path
import uuid
from typing import List, Optional

from src.ingestion.base import ExtractedDocument
from src.processing.base import BaseChunker, Chunk, ChunkMetadata


class RecursiveTextSplitter(BaseChunker):
  """Fragmentador recursivo adaptado a la estructura documental."""

  def __init__(
      self,
      target_chunk_size: int = 500,
      max_chunk_size: int = 800,
      overlap: int = 80,
      separators: Optional[List[str]] = None,
  ):
    """Inicializa el divisor recursivo de texto.

    Args:
        target_chunk_size: Tamaño objetivo aproximado del chunk en caracteres/tokens.
        max_chunk_size: Tamaño máximo permitido para un chunk.
        overlap: Cantidad de caracteres/tokens de solapamiento entre chunks consecutivos.
        separators: Lista ordenada de separadores para división jerárquica.
    """
    self.target_chunk_size = target_chunk_size
    self.max_chunk_size = max_chunk_size
    self.overlap = overlap
    self.separators = separators or [
        "\n# ",
        "\n## ",
        "\n### ",
        "\n#### ",
        "\n\n",
        "\n",
        " ",
        "",
    ]

  def chunk(self, document: ExtractedDocument) -> List[Chunk]:
    """Divide un ExtractedDocument de tipo documentación en chunks semánticamente coherentes."""
    raw_text = document.raw_content
    if not raw_text.strip():
      return []

    text_splits = self._split_text(raw_text, self.separators)
    chunks: List[Chunk] = []

    current_line = 1
    for idx, text_block in enumerate(text_splits):
      line_count = text_block.count("\n") + 1
      start_line = current_line
      end_line = start_line + line_count - 1
      current_line = end_line + 1

      # Generación de UUID determinista basado en el ID del documento y el índice del chunk
      chunk_uuid = str(
          uuid.uuid5(
              uuid.NAMESPACE_URL, f"{document.document_id}_chunk_{idx}"
          )
      )

      metadata = ChunkMetadata(
          format=document.metadata.format,
          start_line=start_line,
          end_line=end_line,
          section=self._extract_heading_context(text_block),
          extra_info=document.metadata.extra_info.copy(),
      )

      chunk_obj = Chunk(
          chunk_id=chunk_uuid,
          document_id=document.document_id,
          content=text_block,
          source=document.source,
          content_type=document.content_type,
          language=document.language,
          metadata=metadata,
      )
      chunks.append(chunk_obj)

    return chunks

  def _split_text(self, text: str, separators: List[str]) -> List[str]:
    """Divide recursivamente el texto según la jerarquía de separadores."""
    final_chunks: List[str] = []
    separator = separators[-1]
    new_separators = []

    for i, s in enumerate(separators):
      if s == "":
        separator = s
        break
      if s in text:
        separator = s
        new_separators = separators[i + 1 :]
        break

    splits = text.split(separator) if separator != "" else list(text)

    good_splits: List[str] = []
    for s in splits:
      if len(s) < self.target_chunk_size:
        good_splits.append(s)
      else:
        if good_splits:
          merged = self._merge_splits(good_splits, separator)
          final_chunks.extend(merged)
          good_splits = []
        if new_separators:
          other_splits = self._split_text(s, new_separators)
          final_chunks.extend(other_splits)
        else:
          final_chunks.append(s)

    if good_splits:
      merged = self._merge_splits(good_splits, separator)
      final_chunks.extend(merged)

    return final_chunks

  def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
    """Combina fragmentos pequeños manteniendo el límite de tamaño y aplicando overlap."""
    merged: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for s in splits:
      split_len = len(s)
      if current_len + split_len + len(separator) > self.max_chunk_size:
        if current_chunk:
          doc_text = separator.join(current_chunk)
          merged.append(doc_text)

          # Aplicar overlap reteniendo partes del final del chunk actual
          overlap_len = 0
          overlap_splits: List[str] = []
          for item in reversed(current_chunk):
            if overlap_len + len(item) <= self.overlap:
              overlap_splits.insert(0, item)
              overlap_len += len(item)
            else:
              break
          current_chunk = overlap_splits
          current_len = overlap_len

      current_chunk.append(s)
      current_len += split_len + len(separator)

    if current_chunk:
      merged.append(separator.join(current_chunk))

    return merged

  def _extract_heading_context(self, text: str) -> Optional[str]:
    """Extrae el primer encabezado Markdown presente en el bloque para mantener contexto."""
    lines = text.splitlines()
    for line in lines:
      stripped = line.strip()
      if stripped.startswith("#"):
        return stripped.lstrip("#").strip()
    return None