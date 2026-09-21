import json
import sys
import shutil
import tempfile
from pathlib import Path

import faiss
import numpy as np
from tqdm import tqdm


# IMPORTANT:
# Run this script from RISK_MODULE folder:
# python .\scripts\rebuild_legal_knowledge_base.py
ROOT = Path.cwd().resolve()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.embedder import generate_embedding


DATASET_DIRS = [
    ROOT / "datasets" / "IndianContracts",
    ROOT / "datasets" / "CUAD"
]

UNIFIED_DIR = ROOT / "datasets" / "unified"
VECTOR_DIR = ROOT / "vector_store"

UNIFIED_PATH = UNIFIED_DIR / "unified_legal_clauses.json"
INDEX_PATH = VECTOR_DIR / "legal_clauses.index"
METADATA_PATH = VECTOR_DIR / "legal_clauses_metadata.json"


def load_json_file(path: Path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def normalize_item(item: dict, source_file: str) -> dict:
    text = (
        item.get("clause_text")
        or item.get("text")
        or item.get("principle")
        or item.get("summary")
        or item.get("content")
        or ""
    )

    text = " ".join(str(text).split())

    if not text:
        return {}

    if len(text) < 40:
        return {}

    clause_type = (
        item.get("clause_type")
        or item.get("type")
        or item.get("category")
        or item.get("legal_area")
        or "General Legal Clause"
    )

    risk_label = (
        item.get("risk_label")
        or item.get("risk_level")
        or "UNKNOWN"
    )

    risk_label = str(risk_label).upper().strip()

    if risk_label not in [
        "HIGH",
        "MEDIUM",
        "LOW",
        "UNKNOWN"
    ]:
        risk_label = "UNKNOWN"

    return {
        "clause_text": text,
        "clause_type": clause_type,
        "risk_label": risk_label,
        "issue": item.get("issue", item.get("detected_issue", "")),
        "source": item.get("source", source_file),
        "source_type": item.get("source_type", "Dataset Clause"),
        "act_name": item.get("act_name", ""),
        "section_reference": item.get("section_reference", ""),
        "legal_area": item.get("legal_area", ""),
        "source_url": item.get("source_url", ""),
        "source_file": source_file
    }


def collect_dataset_items():
    items = []

    for dataset_dir in DATASET_DIRS:
        if not dataset_dir.exists():
            print(f"Dataset folder not found: {dataset_dir}")
            continue

        for path in sorted(dataset_dir.glob("*.json")):
            if path.name in [
                "unified_legal_clauses.json",
                "legal_sources_manifest.json"
            ]:
                continue

            print(f"Loading: {path}")

            try:
                data = load_json_file(path)
            except Exception as e:
                print(f"Skipping {path}: {e}")
                continue

            if isinstance(data, dict):
                if "clauses" in data:
                    data = data["clauses"]
                elif "data" in data:
                    data = data["data"]
                elif "items" in data:
                    data = data["items"]
                else:
                    data = [data]

            if not isinstance(data, list):
                continue

            loaded_count = 0

            for raw_item in data:
                if not isinstance(raw_item, dict):
                    continue

                normalized = normalize_item(
                    raw_item,
                    source_file=path.name
                )

                if normalized:
                    items.append(normalized)
                    loaded_count += 1

            print(f"  loaded items: {loaded_count}")

    return items


def deduplicate_items(items):
    seen = set()
    unique = []

    for item in items:
        key = " ".join(
            item["clause_text"].lower().split()
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


def build_faiss_index(items):
    embeddings = []

    for item in tqdm(items, desc="Generating embeddings"):
        emb = generate_embedding(
            item["clause_text"]
        )

        emb = np.array(
            emb,
            dtype="float32"
        ).reshape(-1)

        embeddings.append(emb)

    matrix = np.vstack(
        embeddings
    ).astype("float32")

    faiss.normalize_L2(matrix)

    index = faiss.IndexFlatIP(
        matrix.shape[1]
    )

    index.add(matrix)

    return index


def safe_write_faiss_index(index, final_index_path: Path):
    """
    FAISS on Windows can fail when writing directly to a path containing
    Unicode characters or special OneDrive folders. So we first write to
    a simple temp path, then copy using Python.
    """

    final_index_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_dir = Path(
        tempfile.gettempdir()
    ) / "risk_module_faiss_temp"

    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_index_path = temp_dir / "legal_clauses.index"

    if temp_index_path.exists():
        temp_index_path.unlink()

    print(f"Writing FAISS index to temp path: {temp_index_path}")

    faiss.write_index(
        index,
        str(temp_index_path)
    )

    print(f"Copying FAISS index to final path: {final_index_path}")

    shutil.copy2(
        temp_index_path,
        final_index_path
    )


def main():
    print(f"ROOT: {ROOT}")
    print(f"UNIFIED_PATH: {UNIFIED_PATH}")
    print(f"INDEX_PATH: {INDEX_PATH}")
    print(f"METADATA_PATH: {METADATA_PATH}")

    UNIFIED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    VECTOR_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print(f"vector_store exists: {VECTOR_DIR.exists()}")

    items = collect_dataset_items()
    items = deduplicate_items(items)

    if not items:
        raise RuntimeError(
            "No dataset items found."
        )

    with UNIFIED_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            items,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Unified dataset saved: {UNIFIED_PATH}")
    print(f"Total unique clauses/principles: {len(items)}")

    index = build_faiss_index(items)

    safe_write_faiss_index(
        index,
        INDEX_PATH
    )

    METADATA_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with METADATA_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            items,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"FAISS index saved: {INDEX_PATH}")
    print(f"Metadata saved: {METADATA_PATH}")
    print("Legal knowledge base rebuild completed successfully.")


if __name__ == "__main__":
    main()