import json
import os
from itertools import islice

from datasets import load_dataset


OUTPUT_PATH = "datasets/LEDGAR/ledgar_rag_clauses.json"
MAX_ITEMS = 500


def main():
    os.makedirs(
        "datasets/LEDGAR",
        exist_ok=True
    )

    print("Loading LEDGAR subset...")

    try:
        ds = load_dataset(
            "lex_glue",
            "ledgar",
            split="train",
            streaming=True
        )

    except Exception as e:
        print("LEDGAR download failed:", str(e))
        print("Skipping LEDGAR. You can keep CUAD + IndianContracts.")
        return

    items = []
    seen = set()

    for row in islice(ds, MAX_ITEMS):
        text = (
            row.get("text")
            or row.get("clause")
            or ""
        )

        if not text or len(text.split()) < 8:
            continue

        label = row.get(
            "label",
            "Unknown"
        )

        if isinstance(label, list):
            label = ",".join(map(str, label))

        key = " ".join(text.lower().split())

        if key in seen:
            continue

        seen.add(key)

        items.append({
            "clause_text": text.strip(),
            "clause_type": str(label),
            "risk_label": "UNKNOWN",
            "issue": "",
            "source": "LEDGAR"
        })

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            items,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Saved LEDGAR subset to {OUTPUT_PATH}")
    print(f"Total LEDGAR clauses added: {len(items)}")


if __name__ == "__main__":
    main()
    