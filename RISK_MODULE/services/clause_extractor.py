import re


LEGAL_INDICATORS = [
    "shall",
    "must",
    "agree",
    "agrees",
    "liable",
    "liability",
    "terminate",
    "termination",
    "payment",
    "notice",
    "indemnify",
    "indemnity",
    "indemnification",
    "breach",
    "default",
    "arbitration",
    "jurisdiction",
    "confidential",
    "force majeure",
    "governing law",
    "obligation",
    "obligations",
    "rights",
    "warranty",
    "representations",
    "covenant",
    "consent",
    "assignment",
    "intellectual property",
    "employment",
    "employee",
    "employer",
    "salary",
    "penalty",
    "non-compete",
    "non compete"
]


LEGAL_HEADINGS = [
    "confidentiality",
    "termination",
    "term of contract",
    "payment",
    "salary",
    "fees",
    "indemnity",
    "indemnification",
    "limitation of liability",
    "liability",
    "force majeure",
    "governing law",
    "jurisdiction",
    "dispute resolution",
    "arbitration",
    "intellectual property",
    "assignment",
    "notices",
    "warranty",
    "representations",
    "obligations",
    "rights",
    "default",
    "breach",
    "remedies",
    "probationary period",
    "other terms"
]


# Important:
# Roman numerals are allowed only when they are clear headings like "IV." or "VIII".
# This prevents "Company" from being treated as Roman numeral "C".
HEADING_PATTERN = re.compile(
    r"(?im)^\s*((?:article|section|clause)\s+\d+[A-Z]?|\d+(?:\.\d+)*)(?:[\).:-]|\s)\s*([A-Z][A-Za-z0-9 &,/\\-]{2,100})?\s*:?\s*$"
    r"|^\s*((?:[IVXLC]{2,}|[IVXLC]+[\).:-]))\s*([A-Z][A-Za-z0-9 &,/\\-]{2,100})?\s*:?\s*$"
)


def looks_like_legal_clause(text: str) -> bool:
    """
    Validate whether text looks like a legal clause.
    """

    if not text:
        return False

    words = text.split()

    if len(words) < 8:
        return False

    lower = text.lower()

    legal_count = 0

    for indicator in LEGAL_INDICATORS:
        if indicator in lower:
            legal_count += 1

    return legal_count >= 1


def detect_heading(clause_text: str) -> str:
    """
    Detect heading from first line or legal keywords.
    """

    if not clause_text:
        return "Unknown"

    lines = [
        line.strip()
        for line in clause_text.strip().split("\n")
        if line.strip()
    ]

    if not lines:
        return "Unknown"

    first_line = lines[0]

    # If first line is just a number like "8.", use next line as heading.
    if re.match(r"^\d+(?:\.\d+)*\.?$", first_line) and len(lines) > 1:
        possible_heading = lines[1].strip()

        if len(possible_heading.split()) <= 10:
            return possible_heading.strip(": ")

    # Remove real numbering only.
    # Do NOT remove single Roman letter from words like "Company".
    clean_heading = re.sub(
        r"^\s*(?:(?:article|section|clause)\s+\d+[A-Z]?|\d+(?:\.\d+)*)\s*[\).:-]?\s+",
        "",
        first_line,
        flags=re.I
    ).strip()

    clean_heading = re.sub(
        r"^\s*(?:[IVXLC]{2,}|[IVXLC]+[\).:-])\s+",
        "",
        clean_heading,
        flags=re.I
    ).strip()

    if clean_heading and len(clean_heading.split()) <= 10:
        return clean_heading.strip(": ")

    lower = clause_text.lower()

    for heading in LEGAL_HEADINGS:
        if heading in lower:
            return heading.title()

    return "General Clause"


def split_by_headings(text: str) -> list:
    """
    Split document using numbered or titled legal headings.
    """

    matches = list(
        HEADING_PATTERN.finditer(text)
    )

    if len(matches) < 2:
        return []

    clauses = []

    for index, match in enumerate(matches):
        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        chunk = text[start:end].strip()

        if looks_like_legal_clause(chunk):
            clauses.append(chunk)

    return clauses


def split_by_numbered_clauses(text: str) -> list:
    """
    Fallback for patterns like:
    1) THAT ...
    2) THAT ...
    """

    parts = re.split(
        r"(?=\n\s*\d+\)\s+(?:THAT|The|Each|Either|Party|Purchaser|Seller|Employee|Employer))",
        text,
        flags=re.I
    )

    clauses = []

    for part in parts:
        part = part.strip()

        if looks_like_legal_clause(part):
            clauses.append(part)

    return clauses


def split_by_paragraphs(text: str) -> list:
    """
    Final fallback using paragraphs.
    """

    paragraphs = re.split(
        r"\n\s*\n+",
        text
    )

    clauses = []

    for para in paragraphs:
        para = para.strip()

        if looks_like_legal_clause(para):
            clauses.append(para)

    return clauses


def split_long_clause(clause: str, max_words: int = 250) -> list:
    """
    Split long clauses into smaller chunks.
    """

    words = clause.split()

    if len(words) <= max_words:
        return [clause]

    sentences = re.split(
        r"(?<=[.;])\s+",
        clause
    )

    chunks = []
    current = ""

    for sentence in sentences:
        candidate = (
            current + " " + sentence
        ).strip()

        if len(candidate.split()) <= max_words:
            current = candidate

        else:
            if len(current.split()) >= 8:
                chunks.append(
                    current.strip()
                )

            current = sentence

    if len(current.split()) >= 8:
        chunks.append(
            current.strip()
        )

    return chunks


def remove_duplicates(clauses: list) -> list:
    """
    Remove duplicate or near duplicate clauses.
    """

    final = []
    seen = set()

    for clause in clauses:
        key = re.sub(
            r"\s+",
            " ",
            clause[:150].lower()
        )

        if key in seen:
            continue

        seen.add(key)
        final.append(clause)

    return final
def normalize_spacing_artifacts(text: str) -> str:
    """
    Fix common spacing artifacts caused by PDF extraction.
    This is generic and document-independent, but conservative enough
    to avoid breaking normal English words like 'within' or 'maintain'.
    """

    text = str(text or "")

    text = " ".join(
        text.split()
    )

    # Split camelCase / lowerUpper joins.
    # Example: employeeWithout -> employee Without
    text = re.sub(
        r"([a-z])([A-Z])",
        r"\1 \2",
        text
    )

    # Common legal nouns/party words that can get joined with connector words.
    # This is not document-specific; it covers common legal document vocabulary.
    legal_prefixes = [
        "employee",
        "employer",
        "company",
        "client",
        "customer",
        "party",
        "parties",
        "tenant",
        "landlord",
        "borrower",
        "lender",
        "principal",
        "agent",
        "vendor",
        "contractor",
        "serviceprovider",
        "provider",
        "lawfirm",
        "firm",
        "agreement",
        "contract",
        "clause",
        "document",
        "notice",
        "payment",
        "salary",
        "wages",
        "liability",
        "obligation",
        "authority"
    ]

    connectors = [
        "without",
        "with",
        "shall",
        "will",
        "must",
        "may",
        "can",
        "should",
        "would",
        "could",
        "if",
        "then",
        "where",
        "whereas",
        "unless",
        "provided",
        "because",
        "before",
        "after",
        "during",
        "under",
        "upon",
        "within",
        "against",
        "between",
        "through"
    ]

    # Split only known legal word + connector combinations.
    # Example:
    # employeewithout -> employee without
    # companyshall -> company shall
    # partyshall -> party shall
    for prefix in legal_prefixes:
        for connector in connectors:
            text = re.sub(
                rf"\b({prefix})({connector})\b",
                rf"\1 {connector}",
                text,
                flags=re.IGNORECASE
            )

    # Start-of-sentence joins.
    text = re.sub(
        r"\bIf(the)\b",
        r"If \1",
        text
    )

    text = re.sub(
        r"\bif(the)\b",
        r"if \1",
        text
    )

    text = re.sub(
        r"\bThen(the)\b",
        r"Then \1",
        text
    )

    text = re.sub(
        r"\bthen(the)\b",
        r"then \1",
        text
    )

    # Common legal phrase joins.
    phrase_replacements = {
        "lawfirm": "law firm",
        "serviceprovider": "service provider",
        "writtennotice": "written notice",
        "priornotice": "prior notice",
        "priorwritten": "prior written",
        "reasonableopportunity": "reasonable opportunity",
        "opportunitytocure": "opportunity to cure",
        "tocure": "to cure",
        "torespond": "to respond",
        "actualcosts": "actual costs",
        "legalrights": "legal rights",
        "broadproperty": "broad property"
    }

    for wrong, correct in phrase_replacements.items():
        text = re.sub(
            rf"\b{wrong}\b",
            correct,
            text,
            flags=re.IGNORECASE
        )

    text = " ".join(
        text.split()
    )

    return text
def _starts_with_clause_number(text: str) -> bool:
    """
    Detect numbered legal clauses like:
    1.
    4.5
    8.9.1
    10.2
    """

    return bool(
        re.match(
            r"^\s*\d+(\.\d+)*[\.\)]?\s+",
            str(text or "")
        )
    )


def _looks_like_heading(text: str) -> bool:
    """
    Detect headings so they are not merged incorrectly.
    """

    text = str(text or "").strip()

    if not text:
        return False

    words = text.split()

    if len(words) > 12:
        return False

    lower = text.lower().strip(": ")

    if lower in LEGAL_HEADINGS:
        return True

    alpha_count = sum(
        1 for ch in text
        if ch.isalpha()
    )

    if alpha_count == 0:
        return False

    upper_count = sum(
        1 for ch in text
        if ch.isupper()
    )

    upper_ratio = upper_count / alpha_count

    if upper_ratio > 0.65:
        return True

    return False


def _previous_clause_incomplete(text: str) -> bool:
    """
    Detect if previous clause likely continues into next extracted fragment.
    """

    text = str(text or "").strip().lower()

    if not text:
        return False

    incomplete_endings = [
        " then the",
        " if",
        " if any",
        " in case",
        " in case if",
        " and",
        " or",
        " but",
        " which",
        " that",
        " the",
        " of",
        " to",
        " by",
        " for",
        " with",
        " without",
        " as",
        " shall be",
        " shall",
        " will be",
        " may be",
        " liable to",
        " entitled to"
    ]

    if text.endswith(",") or text.endswith(";") or text.endswith(":"):
        return True

    return any(
        text.endswith(end)
        for end in incomplete_endings
    )


def _current_is_continuation(text: str) -> bool:
    """
    Detect if current fragment is likely continuation of previous clause.
    """

    raw = str(text or "").strip()

    if not raw:
        return False

    lower = raw.lower()

    continuation_starts = [
        "company shall",
        "employer shall",
        "employee shall",
        "client shall",
        "law firm shall",
        "provided that",
        "unless",
        "therefore",
        "consequently",
        "then",
        "then the",
        "and",
        "or",
        "but",
        "which",
        "that",
        "where",
        "whereas",
        "in such case",
        "in case",
        "in the event"
    ]

    if lower.startswith(tuple(continuation_starts)):
        return True

    if raw and raw[0].islower():
        return True

    return False
def _looks_like_heading(text: str) -> bool:
    """
    Detect headings so they are not merged incorrectly.
    """

    text = str(text or "").strip()

    if not text:
        return False

    words = text.split()

    if len(words) > 12:
        return False

    lower = text.lower().strip(": ")

    if lower in LEGAL_HEADINGS:
        return True

    alpha_count = sum(
        1 for ch in text
        if ch.isalpha()
    )

    if alpha_count == 0:
        return False

    upper_count = sum(
        1 for ch in text
        if ch.isupper()
    )

    upper_ratio = upper_count / alpha_count

    if upper_ratio > 0.65:
        return True

    return False


def _previous_clause_incomplete(text: str) -> bool:
    """
    Detect if previous clause likely continues into next extracted fragment.
    """

    text = str(text or "").strip().lower()

    if not text:
        return False

    incomplete_endings = [
        " then the",
        " if",
        " if any",
        " in case",
        " in case if",
        " and",
        " or",
        " but",
        " which",
        " that",
        " the",
        " of",
        " to",
        " by",
        " for",
        " with",
        " without",
        " as",
        " shall be",
        " shall",
        " will be",
        " may be",
        " liable to",
        " entitled to"
    ]

    if text.endswith(",") or text.endswith(";") or text.endswith(":"):
        return True

    return any(
        text.endswith(end)
        for end in incomplete_endings
    )


def _current_is_continuation(text: str) -> bool:
    """
    Detect if current fragment is likely continuation of previous clause.
    """

    raw = str(text or "").strip()

    if not raw:
        return False

    lower = raw.lower()

    continuation_starts = [
        "company shall",
        "employer shall",
        "employee shall",
        "client shall",
        "law firm shall",
        "provided that",
        "unless",
        "therefore",
        "consequently",
        "then",
        "then the",
        "and",
        "or",
        "but",
        "which",
        "that",
        "where",
        "whereas",
        "in such case",
        "in case",
        "in the event"
    ]

    if lower.startswith(tuple(continuation_starts)):
        return True

    # If first character is lowercase, usually continuation.
    # But we still check other conditions before merging.
    if raw and raw[0].islower():
        return True

    return False


def split_embedded_numbered_clauses(clauses: list) -> list:
    """
    Split cases where two numbered clauses accidentally merged into one.
    Only splits on line-start numbered clauses to avoid splitting section references.
    """

    if not clauses:
        return []

    output = []

    number_pattern = re.compile(
        r"(?m)^\s*\d+(\.\d+)+\s+"
    )

    for clause in clauses:
        text = str(
            clause.get("text", "")
        ).strip()

        if not text:
            continue

        matches = list(
            number_pattern.finditer(text)
        )

        if len(matches) <= 1:
            output.append(clause)
            continue

        positions = [
            match.start()
            for match in matches
        ]

        split_texts = []

        for idx, pos in enumerate(positions):
            end = positions[idx + 1] if idx + 1 < len(positions) else len(text)
            part = text[pos:end].strip()

            if part:
                split_texts.append(part)

        for part in split_texts:
            new_clause = dict(clause)
            new_clause["text"] = part
            new_clause["heading"] = detect_heading(part)
            output.append(new_clause)

    for idx, clause in enumerate(output, start=1):
        clause["clause_id"] = idx

    return output


def merge_clause_continuations(clauses: list) -> list:
    """
    Conservatively merge fragments that are likely continuation of previous clause.
    Avoids merging separate numbered clauses or headings.
    """

    if not clauses:
        return []

    merged = []

    for clause in clauses:
        text = str(
            clause.get("text", "")
        ).strip()

        heading = clause.get(
            "heading",
            "General Clause"
        )

        if not text:
            continue

        starts_number = _starts_with_clause_number(text)
        looks_heading = _looks_like_heading(text)

        should_merge = False

        if merged:
            previous_text = merged[-1].get(
                "text",
                ""
            )

            should_merge = (
                not starts_number
                and not looks_heading
                and (
                    _previous_clause_incomplete(previous_text)
                    or _current_is_continuation(text)
                )
            )

        if should_merge:
            merged[-1]["text"] = (
                merged[-1]["text"].rstrip()
                + " "
                + text
            )

            if merged[-1].get("heading") == "General Clause" and heading != "General Clause":
                merged[-1]["heading"] = heading

        else:
            merged.append(clause)

    for idx, clause in enumerate(merged, start=1):
        clause["clause_id"] = idx

    return merged


def post_process_clauses(clauses: list) -> list:
    """
    Final clause cleanup:
    1. Split wrongly merged numbered clauses.
    2. Merge continuation fragments.
    3. Normalize PDF spacing artifacts using generic rules.
    """

    clauses = split_embedded_numbered_clauses(clauses)
    clauses = merge_clause_continuations(clauses)

    for idx, clause in enumerate(clauses, start=1):
        clause["clause_id"] = idx

        clause["text"] = normalize_spacing_artifacts(
            clause.get("text", "")
        )

        clause["heading"] = detect_heading(
            clause["text"]
        )

    return clauses

def extract_clauses(text: str) -> list:
    """
    Main V2 clause extraction function.
    """

    if not text:
        return []

    raw_clauses = split_by_headings(
        text
    )

    if len(raw_clauses) < 3:
        raw_clauses = split_by_numbered_clauses(
            text
        )

    if len(raw_clauses) < 3:
        raw_clauses = split_by_paragraphs(
            text
        )

    raw_clauses = remove_duplicates(
        raw_clauses
    )

    final = []
    clause_id = 1

    for clause in raw_clauses:
        smaller_chunks = split_long_clause(
            clause
        )

        for chunk in smaller_chunks:
            if not looks_like_legal_clause(chunk):
                continue

            final.append({
                "clause_id": clause_id,
                "heading": detect_heading(chunk),
                "text": chunk
            })

            clause_id += 1

    final = post_process_clauses(
        final
    )

    return final