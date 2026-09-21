import json
import os

from services.embedder import generate_embeddings_batch
from services.vector_store import vector_store


UNIFIED_DATASET_PATH = "datasets/unified/unified_legal_clauses.json"


def load_dataset():
    """
    Load only unified dataset to avoid duplicate clauses.
    This prevents loading both original dataset files and unified file together.
    """

    if not os.path.exists(UNIFIED_DATASET_PATH):
        print("Unified dataset not found.")
        print("Run: python build_unified_dataset.py")
        return []

    with open(
        UNIFIED_DATASET_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    items = []
    seen = set()

    for row in data:
        clause_text = row.get(
            "clause_text",
            ""
        ).strip()

        if not clause_text:
            continue

        key = " ".join(
            clause_text.lower().split()
        )

        if key in seen:
            continue

        seen.add(key)

        risk_label = str(
            row.get("risk_label", "UNKNOWN")
        ).upper().strip()

        if risk_label not in [
            "HIGH",
            "MEDIUM",
            "LOW",
            "UNKNOWN"
        ]:
            risk_label = "UNKNOWN"

        items.append({
            "clause_text": clause_text,
            "clause_type": row.get(
                "clause_type",
                "Unknown"
            ),
            "risk_label": risk_label,
            "issue": row.get(
                "issue",
                ""
            ),
            "source": row.get(
                "source",
                "UnifiedDataset"
            )
        })

    return items


if __name__ == "__main__":
    items = load_dataset()

    if not items:
        print("No dataset clauses found.")
        exit()

    texts = [
        item["clause_text"]
        for item in items
    ]

    print(
        f"Generating embeddings for {len(texts)} unique clauses..."
    )

    embeddings = generate_embeddings_batch(
        texts
    )

    vector_store.build(
        embeddings=embeddings,
        metadata=items
    )

    print(
        f"Vector store built successfully with {len(items)} unique clauses."
    )