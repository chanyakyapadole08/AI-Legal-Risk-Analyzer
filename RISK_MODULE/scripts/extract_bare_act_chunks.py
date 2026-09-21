import json
import re
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "source_docs" / "legal_references"
OUTPUT_PATH = ROOT / "datasets" / "IndianContracts" / "legal_bare_act_chunks.json"


ACT_METADATA = {
    "Indian_Contract_Act_1872.pdf": {
        "act_name": "Indian Contract Act, 1872",
        "official_source": "India Code",
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/2187/2/A187209.pdf"
    },
    "Arbitration_and_Conciliation_Act_1996.pdf": {
        "act_name": "Arbitration and Conciliation Act, 1996",
        "official_source": "India Code",
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/21922/1/the_arbitration_and_conciliation_act,_1996_act_no._26_of_1996.pdf"
    },
    "Information_Technology_Act_2000.pdf": {
        "act_name": "Information Technology Act, 2000",
        "official_source": "India Code",
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf"
    },
    "DPDP_Act_2023.pdf": {
        "act_name": "Digital Personal Data Protection Act, 2023",
        "official_source": "e-Gazette of India",
        "source_url": "https://egazette.gov.in/WriteReadData/2023/248045.pdf"
    },
    "Transfer_of_Property_Act_1882.pdf": {
        "act_name": "Transfer of Property Act, 1882",
        "official_source": "India Code",
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/14037/1/transfer_of_property_act8_(1).pdf"
    },
    "Companies_Act_2013.pdf": {
        "act_name": "Companies Act, 2013",
        "official_source": "India Code / MCA",
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/2114/5/A2013-18.pdf"
    },
    "Industrial_Disputes_Act_1947.pdf": {
        "act_name": "Industrial Disputes Act, 1947",
        "official_source": "India Code",
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/14040/1/id_act_1947.pdf"
    },
    "Payment_of_Wages_Act_1936.pdf": {
        "act_name": "Payment of Wages Act, 1936",
        "official_source": "India Code",
        "source_url": "https://www.indiacode.nic.in/bitstream/123456789/20359/1/payment_of_wages_act_1936.pdf"
    }
}


LEGAL_KEYWORDS = [
    "contract",
    "agreement",
    "consent",
    "consideration",
    "lawful",
    "void",
    "penalty",
    "compensation",
    "damages",
    "breach",
    "indemnity",
    "guarantee",
    "agent",
    "agency",
    "arbitration",
    "conciliation",
    "dispute",
    "award",
    "jurisdiction",
    "electronic record",
    "electronic signature",
    "digital signature",
    "personal data",
    "data fiduciary",
    "data principal",
    "processing",
    "lease",
    "lessor",
    "lessee",
    "rent",
    "mortgage",
    "transfer",
    "property",
    "injunction",
    "specific performance",
    "company",
    "director",
    "board",
    "authority",
    "employment",
    "workman",
    "dismissal",
    "termination",
    "retrenchment",
    "wages",
    "deduction",
    "salary",
    "payment",
    "working hours",
    "leave",
    "overtime"
]


def clean_text(text: str) -> str:
    text = str(text or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[0-9]+\n", "\n", text)
    return text.strip()


def extract_pdf_text(path: Path) -> str:
    doc = fitz.open(str(path))
    parts = []

    for page in doc:
        parts.append(page.get_text())

    return clean_text("\n".join(parts))


def split_into_chunks(text: str, max_chars: int = 1400, overlap: int = 180):
    paragraphs = [
        p.strip()
        for p in re.split(r"\n+", text)
        if p.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= max_chars:
            current = f"{current} {paragraph}".strip()
        else:
            if current:
                chunks.append(current)

            tail = current[-overlap:] if current else ""
            current = f"{tail} {paragraph}".strip()

    if current:
        chunks.append(current)

    return chunks


def is_relevant_chunk(text: str) -> bool:
    lower = text.lower()

    if len(lower) < 180:
        return False

    return any(keyword in lower for keyword in LEGAL_KEYWORDS)


def classify_reference_chunk(text: str):
    lower = text.lower()

    if "penalty" in lower or "damages" in lower or "compensation" in lower:
        return "Penalty", "HIGH", "Penalty or damages principle", "Damages and Penalty"

    if "arbitration" in lower or "conciliation" in lower or "dispute" in lower:
        return "Dispute Resolution", "MEDIUM", "Dispute resolution principle", "Dispute Resolution"

    if "personal data" in lower or "data fiduciary" in lower or "data principal" in lower:
        return "Data Protection", "MEDIUM", "Data protection principle", "Data Protection"

    if "wages" in lower or "deduction" in lower or "salary" in lower:
        return "Payment", "HIGH", "Wage payment or deduction principle", "Employment Law"

    if "termination" in lower or "dismissal" in lower or "retrenchment" in lower:
        return "Termination", "HIGH", "Employment termination principle", "Employment Law"

    if "lease" in lower or "lessor" in lower or "lessee" in lower or "rent" in lower:
        return "Lease", "MEDIUM", "Lease and possession principle", "Property Law"

    if "mortgage" in lower or "transfer of property" in lower or "property" in lower:
        return "Property Transfer", "MEDIUM", "Property transfer principle", "Property Law"

    if "director" in lower or "board" in lower or "company" in lower:
        return "Corporate Authority", "MEDIUM", "Company authority principle", "Corporate Law"

    if "electronic record" in lower or "electronic signature" in lower or "digital signature" in lower:
        return "Electronic Contract", "LOW", "Electronic records principle", "Technology Law"

    if "specific performance" in lower or "injunction" in lower:
        return "Legal Remedies", "MEDIUM", "Remedy and injunction principle", "Remedies"

    if "indemnity" in lower or "guarantee" in lower:
        return "Indemnity", "MEDIUM", "Indemnity or guarantee principle", "Contract Law"

    if "agent" in lower or "agency" in lower:
        return "Agency", "MEDIUM", "Agency authority principle", "Contract Law"

    return "Legal Reference", "UNKNOWN", "General legal reference", "General Law"


def build_dataset():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    items = []
    seen = set()

    pdf_files = sorted(SOURCE_DIR.glob("*.pdf"))

    if not pdf_files:
        raise RuntimeError(f"No PDFs found in {SOURCE_DIR}")

    for pdf_path in pdf_files:
        meta = ACT_METADATA.get(
            pdf_path.name,
            {
                "act_name": pdf_path.stem.replace("_", " "),
                "official_source": "Official Legal Source",
                "source_url": ""
            }
        )

        print(f"Extracting: {pdf_path.name}")

        try:
            text = extract_pdf_text(pdf_path)
        except Exception as e:
            print(f"Failed to extract {pdf_path.name}: {e}")
            continue

        chunks = split_into_chunks(text)

        relevant_chunks = [
            chunk
            for chunk in chunks
            if is_relevant_chunk(chunk)
        ]

        # Limit to avoid noisy vector store.
        relevant_chunks = relevant_chunks[:80]

        for idx, chunk in enumerate(relevant_chunks, start=1):
            key = " ".join(chunk.lower().split())

            if key in seen:
                continue

            seen.add(key)

            clause_type, risk_label, issue, legal_area = classify_reference_chunk(chunk)

            items.append({
                "clause_text": chunk,
                "clause_type": clause_type,
                "risk_label": risk_label,
                "issue": issue,
                "source": meta["official_source"],
                "source_type": "Bare Act Extracted Chunk",
                "act_name": meta["act_name"],
                "section_reference": f"Extracted chunk {idx}",
                "legal_area": legal_area,
                "source_url": meta["source_url"],
                "source_file": pdf_path.name
            })

        print(f"  relevant chunks added: {len(relevant_chunks)}")

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Saved legal bare act chunks to: {OUTPUT_PATH}")
    print(f"Total chunks: {len(items)}")


if __name__ == "__main__":
    build_dataset()