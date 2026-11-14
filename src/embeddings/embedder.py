import logging
from typing import List, Union

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MAX_SEQ_LENGTH = 512  # límite real de multilingual-e5-small


class Embedder:
    """Vectorización con intfloat/multilingual-e5-small (CPU por defecto)."""

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
        device: str = "cpu",
        batch_size: int = 32,
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size

        logger.info("Cargando '%s' en '%s'...", model_name, device)
        self.model = SentenceTransformer(model_name, device=device)
        self.model.max_seq_length = MAX_SEQ_LENGTH
        self.dimension: int = self.model.get_sentence_embedding_dimension()
        logger.info("Modelo cargado (dimensión %d).", self.dimension)

    def count_tokens(self, text: str, prefix: str = "passage: ") -> int:
        """Tokens que ocuparía el texto con su prefijo (para detectar truncamiento)."""
        return len(self.model.tokenizer.encode(prefix + text, add_special_tokens=True))

    def _encode(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()

    def embed_passages(self, texts: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(texts, str):
            texts = [texts]
        too_long = [t for t in texts if self.count_tokens(t) > MAX_SEQ_LENGTH]
        if too_long:
            logger.warning(
                "%d fragmento(s) superan %d tokens y se truncarán.",
                len(too_long), MAX_SEQ_LENGTH,
            )
        return self._encode([f"passage: {t}" for t in texts])

    def embed_queries(self, queries: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(queries, str):
            queries = [queries]
        return self._encode([f"query: {q}" for q in queries])