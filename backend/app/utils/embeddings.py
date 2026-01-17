from typing import List, Optional
import threading

from sentence_transformers import SentenceTransformer
import numpy as np
from numpy.typing import NDArray

from app.config import settings


class EmbeddingModel:
    """
    Thread-safe singleton wrapper for sentence-transformers model.

    Ensures model is loaded only once and reused across the application.
    """

    _instance: Optional["EmbeddingModel"] = None
    _lock: threading.Lock = threading.Lock()
    _model: Optional[SentenceTransformer] = None

    def __new__(cls, model_name: Optional[str] = None) -> "EmbeddingModel":
        """
        Create or return the singleton instance.

        Args:
            model_name: Model name (only used on first instantiation).

        Returns:
            The singleton EmbeddingModel instance.
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: Optional[str] = None) -> None:
        """
        Initialize the embedding model.

        Args:
            model_name: Sentence-transformers model name.
        """
        # Prevent re-initialization
        if getattr(self, "_initialized", False):
            return

        self._model_name = model_name or settings.MODEL_NAME
        self._model = None
        self._embedding_dim: Optional[int] = None
        self._initialized = True

    def _load_model(self) -> SentenceTransformer:
        """
        Lazily load the model on first use.

        Returns:
            Loaded SentenceTransformer model.
        """
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = SentenceTransformer(self._model_name)
                    # Cache embedding dimension
                    self._embedding_dim = self._model.get_sentence_embedding_dimension()
        return self._model

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name

    @property
    def embedding_dimension(self) -> int:
        """
        Get the embedding dimension.

        Returns:
            Dimension of embedding vectors.
        """
        if self._embedding_dim is None:
            self._load_model()
        return self._embedding_dim  # type: ignore

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text string.

        Returns:
            Embedding vector as list of floats.
        """
        model = self._load_model()
        embedding: NDArray[np.float32] = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embedding.tolist()

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input text strings.
            batch_size: Batch size for encoding.
            show_progress: Whether to show progress bar.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        model = self._load_model()
        embeddings: NDArray[np.float32] = model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
        )
        return embeddings.tolist()

    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.

        Args:
            text1: First text.
            text2: Second text.

        Returns:
            Cosine similarity score (0.0 to 1.0 for normalized vectors).
        """
        emb1 = np.array(self.embed(text1))
        emb2 = np.array(self.embed(text2))
        return float(np.dot(emb1, emb2))

    def similarity_matrix(self, texts: List[str]) -> NDArray[np.float32]:
        """
        Compute pairwise similarity matrix for a list of texts.

        Args:
            texts: List of texts.

        Returns:
            NxN similarity matrix.
        """
        embeddings = np.array(self.embed_batch(texts))
        return np.dot(embeddings, embeddings.T)


# Module-level singleton accessor
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model(model_name: Optional[str] = None) -> EmbeddingModel:
    """
    Get the singleton embedding model instance.

    Args:
        model_name: Model name (only used on first call).

    Returns:
        EmbeddingModel singleton instance.
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel(model_name)
    return _embedding_model
