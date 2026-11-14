import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from src.processing.base import Chunk

from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)

# Campos del contrato de chunk (TECH_STACK.md, sección 3)
PAYLOAD_FIELDS = [
    "chunk_id", "document_id", "source", "content_type",
    "language", "start_line", "end_line", "section", "parent",
]

def chunk_to_payload(chunk: Chunk) -> Dict[str, Any]:
    if not chunk.chunk_id:
        raise ValueError("El chunk no tiene chunk_id.")
    meta = chunk.metadata
    return {
        "chunk_id": str(chunk.chunk_id),
        "document_id": chunk.document_id,
        "content": chunk.content,
        "source": chunk.source,
        "content_type": chunk.content_type,
        "language": chunk.language,
        "format": meta.format,
        "start_line": meta.start_line,
        "end_line": meta.end_line,
        "section": meta.section,
        "parent": meta.parent,
        "extra_info": dict(meta.extra_info),
    }

def _point_id(chunk_id: str) -> str:
    """UUID determinista: el mismo chunk_id siempre produce el mismo punto (upsert idempotente)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class VectorStore:
    """Qdrant en modo local persistente."""

    def __init__(
        self,
        collection_name: str = "rag_collection",
        persist_dir: str = "data/indexes/qdrant_db",
        vector_size: int = 384,
    ):
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Abriendo Qdrant local en '%s'", self.persist_dir)
        self.client = QdrantClient(path=str(self.persist_dir))
        self._init_collection()

    def _init_collection(self) -> None:
        names = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size, distance=models.Distance.COSINE
                ),
            )
            logger.info("Colección '%s' creada.", self.collection_name)
            return

        info = self.client.get_collection(self.collection_name)
        existing = info.config.params.vectors.size
        if existing != self.vector_size:
            raise ValueError(
                f"La colección '{self.collection_name}' tiene dimensión {existing} "
                f"y se esperaba {self.vector_size}. ¿Cambió el modelo de embeddings?"
            )

    def add_chunks(self, chunks: List[Any], embeddings: List[List[float]], batch_size: int = 128) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("El número de chunks y de embeddings debe coincidir.")

        points = []
        for chunk, vector in zip(chunks, embeddings):
            payload = chunk_to_payload(chunk)
            points.append(
                models.PointStruct(id=_point_id(payload["chunk_id"]), vector=vector, payload=payload)
            )

        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i : i + batch_size],
            )
        logger.info("%d puntos insertados.", len(points))

    def delete_by_document(self, document_id: str) -> None:
        """Elimina todos los chunks de un documento (llamar antes de reingestarlo)."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(
                        key="document_id", match=models.MatchValue(value=document_id)
                    )]
                )
            ),
        )

    @staticmethod
    def _build_filter(filters: Optional[Dict[str, Any]]) -> Optional[models.Filter]:
        if not filters:
            return None
        return models.Filter(
            must=[
                models.FieldCondition(key=k, match=models.MatchValue(value=v))
                for k, v in filters.items()
            ]
        )

    def search(
        self,
        query_vector: List[float],
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=self._build_filter(filters),
            with_payload=True,
        )
        return [
            {"id": p.id, "score": p.score, "payload": p.payload}
            for p in response.points
        ]

    def scroll_all(self, batch_size: int = 256) -> Iterator[Dict[str, Any]]:
        """Recorre todos los payloads (útil para construir el índice BM25 en la Fase 4)."""
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                yield {"id": p.id, "payload": p.payload}
            if offset is None:
                break

    def count(self) -> int:
        return self.client.count(collection_name=self.collection_name, exact=True).count

    def close(self) -> None:
        """Libera el bloqueo de la carpeta (necesario en Windows)."""
        self.client.close()