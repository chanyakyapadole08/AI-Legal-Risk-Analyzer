import os
import glob
import json
import re
from tqdm import tqdm
from huggingface_hub import snapshot_download

import fitz


OUTPUT_PATH = "datasets/CUAD/cuad_rag_clauses.json"
LOCAL_DIR = "datasets/CUAD/raw_snapshot"

MAX_PDFS = 25
MAX_CLAUSES_TOTAL = 300


def extract_text_from_pdf_simple(pdf_path: str) -> str:
    text_parts = []

    try:
        doc = fitz.open(pdf_path)

        for page in doc:
            text_parts.append(
                page.get_text("text")
            )

        doc.close()

    except Exception as e:
        print("PDF read failed:", pdf_path, str(e)[:100])

    return "\n\n".join(text_parts)


def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")

    text = re.sub(
        r"page\s+\d+\s*(of|/)?\s*\d*",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def split_into_candidate_clauses(text: str) -> list:
    """
    Lightweight splitter for CUAD raw PDFs.
    Good enough for RAG dataset creation.
    """

    candidates = []

    parts = re.split(
        r"\n\s*\n+",
        text
    )

    for part in parts:
        part = part.strip()

        words = part.split()

        if len(words) < 25:
            continue

        if len(words) > 220:
            part = " ".join(words[:220])

        lower = part.lower()

        legal_signals = [
            "shall",
            "agreement",
            "party",
            "parties",
            "terminate",
            "confidential",
            "liability",
            "indemn",
            "governing law",
            "warranty",
            "license",
            "payment",
            "notice"
        ]

        if any(signal in lower for signal in legal_signals):
            candidates.append(part)

    return candidates


def infer_clause_type(text: str, file_name: str) -> str:
    lower = text.lower()

    if "terminate" in lower or "termination" in lower:
        return "Termination"

    if "confidential" in lower:
        return "Confidentiality"

    if "indemn" in lower:
        return "Indemnity"

    if "liability" in lower or "liable" in lower:
        return "Liability"

    if "governing law" in lower or "jurisdiction" in lower:
        return "Governing Law"

    if "payment" in lower or "fees" in lower:
        return "Payment"

    if "license" in lower:
        return "License"

    if "warranty" in lower:
        return "Warranty"

    return "CUAD Clause"


def main():
    os.makedirs(
        "datasets/CUAD",
        exist_ok=True
    )

    print("Downloading CUAD raw PDFs if not already present...")

    snapshot_download(
        repo_id="theatticusproject/cuad",
        repo_type="dataset",
        local_dir=LOCAL_DIR,
        allow_patterns=["**/*.pdf"],
        local_dir_use_symlinks=False
    )

    pdf_files = glob.glob(
        os.path.join(LOCAL_DIR, "**", "*.pdf"),
        recursive=True
    )

    pdf_files = pdf_files[:MAX_PDFS]

    print(f"Found PDFs: {len(pdf_files)}")

    dataset = []
    seen = set()

    for pdf_path in tqdm(pdf_files):
        if len(dataset) >= MAX_CLAUSES_TOTAL:
            break

        file_name = os.path.basename(pdf_path)

        raw_text = extract_text_from_pdf_simple(pdf_path)
        text = clean_text(raw_text)

        clauses = split_into_candidate_clauses(text)

        for clause in clauses:
            if len(dataset) >= MAX_CLAUSES_TOTAL:
                break

            key = " ".join(
                clause.lower().split()
            )

            if key in seen:
                continue

            seen.add(key)

            dataset.append({
                "clause_text": clause,
                "clause_type": infer_clause_type(clause, file_name),
                "risk_label": "UNKNOWN",
                "issue": "",
                "source": "CUAD"
            })

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            dataset,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Saved CUAD subset to {OUTPUT_PATH}")
    print(f"Total CUAD clauses added: {len(dataset)}")


if __name__ == "__main__":
    main()
    