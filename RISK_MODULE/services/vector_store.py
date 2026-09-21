import faiss
import json
import os
import numpy as np


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

VECTOR_DIR = os.path.join(
    BASE_DIR,
    "vector_store"
)

INDEX_PATH = os.path.join(
    VECTOR_DIR,
    "legal_clauses.index"
)

METADATA_PATH = os.path.join(
    VECTOR_DIR,
    "legal_clauses_metadata.json"
)


class LegalVectorStore:

    def __init__(self):
        self.index = None
        self.metadata = []
        self.load()

    def load(self):
        """
        Load FAISS index safely using Python file I/O.
        This avoids Windows Unicode path issues with FAISS native file loading.
        """

        if not os.path.exists(INDEX_PATH):
            print("Vector index not found. Run: python build_vector_store.py")
            return

        if not os.path.exists(METADATA_PATH):
            print("Vector metadata not found. Run: python build_vector_store.py")
            return

        try:
            with open(INDEX_PATH, "rb") as f:
                index_bytes = f.read()

            index_array = np.frombuffer(
                index_bytes,
                dtype="uint8"
            )

            self.index = faiss.deserialize_index(
                index_array
            )

            with open(
                METADATA_PATH,
                "r",
                encoding="utf-8"
            ) as f:
                self.metadata = json.load(f)

        except Exception as e:
            print(
                "Vector store load failed:",
                str(e)[:150]
            )

            self.index = None
            self.metadata = []

    def build(self, embeddings: np.ndarray, metadata: list):
        """
        Build and save FAISS index safely.
        """

        if embeddings is None or len(embeddings) == 0:
            raise ValueError("No embeddings provided.")

        embeddings = np.array(
            embeddings,
            dtype="float32"
        )

        if embeddings.ndim != 2:
            raise ValueError(
                "Embeddings must be a 2D array."
            )

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(
            dimension
        )

        self.index.add(
            embeddings.astype("float32")
        )

        self.metadata = metadata

        os.makedirs(
            VECTOR_DIR,
            exist_ok=True
        )

        # Safe FAISS save using Python file I/O
        serialized_index = faiss.serialize_index(
            self.index
        )

        with open(INDEX_PATH, "wb") as f:
            f.write(
                serialized_index.tobytes()
            )

        with open(
            METADATA_PATH,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                self.metadata,
                f,
                ensure_ascii=False,
                indent=2
            )

    def search(self, query_embedding: np.ndarray, top_k: int = 5):
        """
        Search similar legal clauses.
        """

        if self.index is None:
            self.load()

        if self.index is None:
            return []

        if not self.metadata:
            return []

        query = query_embedding.reshape(
            1,
            -1
        ).astype("float32")

        scores, indices = self.index.search(
            query,
            top_k
        )

        results = []

        for score, idx in zip(
            scores[0],
            indices[0]
        ):
            if idx == -1:
                continue

            if int(idx) >= len(self.metadata):
                continue

            item = self.metadata[int(idx)].copy()

            item["similarity_score"] = round(
                float(score),
                4
            )

            results.append(item)

        return results


vector_store = LegalVectorStore()