import json
import os


DATASET_ROOT = "datasets"


SKIP_FILES = [
    "unified_legal_clauses.json"
]


def normalize_record(row: dict, default_source: str) -> dict:
    """
    Normalize different dataset formats into one common schema.
    """

    clause_text = (
        row.get("clause_text")
        or row.get("text")
        or row.get("clause")
        or ""
    )

    clause_type = (
        row.get("clause_type")
        or row.get("category")
        or row.get("label")
        or "Unknown"
    )

    risk_label = (
        row.get("risk_label")
        or row.get("risk")
        or "UNKNOWN"
    )

    issue = (
        row.get("issue")
        or row.get("detected_issue")
        or ""
    )

    source = (
        row.get("source")
        or default_source
    )

    risk_label = str(
        risk_label
    ).upper().strip()

    if risk_label not in [
        "HIGH",
        "MEDIUM",
        "LOW",
        "UNKNOWN"
    ]:
        risk_label = "UNKNOWN"

    return {
        "clause_text": str(clause_text).strip(),
        "clause_type": str(clause_type).strip(),
        "risk_label": risk_label,
        "issue": str(issue).strip(),
        "source": str(source).strip()
    }


def load_all_legal_clauses(dataset_root: str = DATASET_ROOT) -> list:
    """
    Load all JSON legal clause datasets and remove duplicates.
    """

    items = []

    for root, dirs, files in os.walk(dataset_root):
        for file in files:
            if not file.endswith(".json"):
                continue

            if file in SKIP_FILES:
                continue

            path = os.path.join(
                root,
                file
            )

            source = os.path.basename(
                root
            )

            try:
                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    data = data.get(
                        "data",
                        []
                    )

                if not isinstance(data, list):
                    continue

                for row in data:
                    if not isinstance(row, dict):
                        continue

                    item = normalize_record(
                        row,
                        source
                    )

                    if len(item["clause_text"].split()) >= 5:
                        items.append(item)

            except Exception as e:
                print(
                    "Dataset load error:",
                    path,
                    str(e)[:100]
                )

    unique_items = []
    seen = set()

    for item in items:
        key = " ".join(
            item["clause_text"].lower().split()
        )

        if key in seen:
            continue

        seen.add(key)
        unique_items.append(item)

    return unique_items


def save_unified_dataset(
    output_path: str = "datasets/unified/unified_legal_clauses.json"
):
    """
    Save unified legal clause dataset.
    """

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    items = load_all_legal_clauses()

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            items,
            f,
            ensure_ascii=False,
            indent=2
        )

    return output_path, len(items)