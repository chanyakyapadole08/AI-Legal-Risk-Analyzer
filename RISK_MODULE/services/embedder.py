from sentence_transformers import SentenceTransformer
import numpy as np


MODEL_NAME = "BAAI/bge-base-en-v1.5"

_model = None


def get_model():
    """
    Lazy-load embedding model only when needed.
    """

    global _model

    if _model is None:
        _model = SentenceTransformer(
            MODEL_NAME
        )

    return _model


def generate_embedding(text: str):
    """
    Generate embedding for a single text.
    """

    model = get_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    return np.array(
        embedding,
        dtype="float32"
    )


def generate_embeddings_batch(texts: list):
    """
    Generate embeddings for a batch of texts.
    """

    model = get_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=True
    )

    return np.array(
        embeddings,
        dtype="float32"
    )