"""Adaptador de ingesta para código fuente utilizando Tree-sitter."""

from pathlib import Path
import uuid
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from .base import BaseReader, DocumentMetadata, ExtractedDocument


class CodeReader(BaseReader):
  """Lector especializado en código fuente mediante Tree-sitter."""

  def __init__(self):
    # Inicialización del parser de Tree-sitter (ejemplo para Python por defecto)
    self.py_language = Language(tspython.language())
    self.parser = Parser(self.py_language)

  def read(self, file_path: Path) -> ExtractedDocument:
    """Procesa un archivo de código fuente y devuelve un ExtractedDocument unificado."""
    path = Path(file_path)
    if not path.exists():
      raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
      raw_content = f.read()

    # Ejecutamos el análisis sintáctico de Tree-sitter
    tree = self.parser.parse(bytes(raw_content, "utf8"))

    document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, path.as_uri()))

    # Determinamos el lenguaje según la extensión
    ext = path.suffix.lower()
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
    }
    lang_name = language_map.get(ext, "unknown")

    metadata = DocumentMetadata(
        format=ext,
        extra_info={
            "has_error": (
                hasattr(tree.root_node, "has_error")
                and tree.root_node.has_error
            ),
        },
    )

    return ExtractedDocument(
        document_id=document_id,
        source=str(path.resolve()),
        content_type="code",
        raw_content=raw_content,
        language=lang_name,
        metadata=metadata,
    )