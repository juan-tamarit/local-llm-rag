"""Chunker basado en AST utilizando Tree-sitter para código fuente."""

from pathlib import Path
import uuid
from typing import List, Optional
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node

from src.ingestion.base import ExtractedDocument
from src.processing.base import BaseChunker, Chunk, ChunkMetadata


class CodeSplitter(BaseChunker):
    """Fragmentador de código fuente basado en AST (Árbol de Sintaxis Abstracta) con Tree-sitter."""

    def __init__(self, max_chunk_size: int = 1000):
        """Inicializa el chunker de código.

        Args:
            max_chunk_size: Tamaño máximo aproximado de caracteres por chunk de código.
        """
        self.py_language = Language(tspython.language())
        self.parser = Parser(self.py_language)
        self.max_chunk_size = max_chunk_size

    def chunk(self, document: ExtractedDocument) -> List[Chunk]:
        """Divide un ExtractedDocument de tipo código en chunks basados en estructuras sintácticas."""
        raw_code = document.raw_content
        if not raw_code.strip():
            return []

        tree = self.parser.parse(bytes(raw_code, "utf8"))
        root_node = tree.root_node

        chunks: List[Chunk] = []
        lines = raw_code.splitlines()

        # Recorremos el AST buscando definiciones de funciones, clases o bloques principales
        code_blocks = self._extract_ast_nodes(root_node, lines)

        if not code_blocks:
            # Si el AST no detecta bloques específicos, devolvemos el archivo entero como un chunk
            code_blocks = [{
                "content": raw_code,
                "start_line": 1,
                "end_line": len(lines),
                "parent": None,
                "section": "module_root"
            }]

        for idx, block in enumerate(code_blocks):
            chunk_uuid = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL, f"{document.document_id}_code_chunk_{idx}"
                )
            )

            metadata = ChunkMetadata(
                format=document.metadata.format,
                start_line=block["start_line"],
                end_line=block["end_line"],
                section=block["section"],
                parent=block["parent"],
                extra_info=document.metadata.extra_info.copy(),
            )

            chunk_obj = Chunk(
                chunk_id=chunk_uuid,
                document_id=document.document_id,
                content=block["content"],
                source=document.source,
                content_type=document.content_type,
                language=document.language,
                metadata=metadata,
            )
            chunks.append(chunk_obj)

        return chunks

    def _extract_ast_nodes(self, node: Node, lines: List[str], parent_name: Optional[str] = None) -> List[dict]:
        """Extrae de forma recursiva funciones, clases y métodos desde los nodos del AST."""
        blocks = []
        
        # En Python, buscamos 'function_definition' y 'class_definition'
        if node.type in ("function_definition", "class_definition"):
            start_row, start_col = node.start_point
            end_row, end_col = node.end_point
            
            # Extraer las líneas de código correspondientes a este nodo
            node_lines = lines[start_row:end_row + 1]
            content = "\n".join(node_lines)
            
            # Intentar extraer el nombre del nodo (clase o función)
            name = self._get_node_name(node, lines)
            section_name = f"{parent_name}.{name}" if parent_name else name

            blocks.append({
                "content": content,
                "start_line": start_row + 1,
                "end_line": end_row + 1,
                "parent": parent_name,
                "section": section_name
            })

            # Si es una clase, buscamos métodos internos de forma anidada
            if node.type == "class_definition":
                for child in node.children:
                    child_blocks = self._extract_ast_nodes(child, lines, parent_name=name)
                    blocks.extend(child_blocks)
            
            return blocks

        # Búsqueda recursiva en los hijos si no es un nodo objetivo directo
        for child in node.children:
            blocks.extend(self._extract_ast_nodes(child, lines, parent_name=parent_name))

        return blocks

    def _get_node_name(self, node: Node, lines: List[str]) -> str:
        """Obtiene el identificador (nombre) de una función o clase en Tree-sitter."""
        for child in node.children:
            if child.type == "identifier":
                start_row, start_col = child.start_point
                end_row, end_col = child.end_point
                if start_row == end_row:
                    return lines[start_row][start_col:end_col]
        return "anonymous"