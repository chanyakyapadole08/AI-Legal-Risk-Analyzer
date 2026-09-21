import re
from collections import Counter


def remove_repeated_headers_footers(lines):
    """
    Remove repeated short headers and footers.
    Example: agreement title repeated on every page.
    """

    normalized_lines = []

    for line in lines:
        clean_line = re.sub(
            r"\s+",
            " ",
            line.strip().lower()
        )

        if clean_line:
            normalized_lines.append(clean_line)

    counts = Counter(
        normalized_lines
    )

    cleaned_lines = []

    for line in lines:
        key = re.sub(
            r"\s+",
            " ",
            line.strip().lower()
        )

        if key and counts[key] >= 3 and len(key) < 80:
            continue

        cleaned_lines.append(line)

    return cleaned_lines


def remove_page_numbers(text: str) -> str:
    """
    Remove common page number formats.
    """

    text = re.sub(
        r"page\s+\d+\s*(of|/)?\s*\d*",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\n\s*\d+\s*/\s*\d+\s*\n",
        "\n",
        text
    )

    # Remove standalone page numbers but avoid touching numbered clauses like 1. Termination
    text = re.sub(
        r"\n\s*\d+\s*\n",
        "\n",
        text
    )

    return text


def remove_signature_blocks(text: str) -> str:
    """
    Remove signature/witness blocks generally found at the end of agreements.
    """

    patterns = [
        r"(?is)IN WITNESS WHEREOF.*$",
        r"(?is)SIGNED BY.*$",
        r"(?is)SIGNED AND DELIVERED.*$",
        r"(?is)WITNESS.*SIGNATURE.*$",
        r"(?is)SIGNATURE OF.*$"
    ]

    for pattern in patterns:
        text = re.sub(
            pattern,
            "",
            text
        )

    return text


def remove_table_like_lines(text: str) -> str:
    """
    Remove obvious table rows while keeping normal legal sentences.
    """

    final_lines = []

    for line in text.split("\n"):
        stripped = line.strip()

        if not stripped:
            final_lines.append("")
            continue

        if stripped.count("|") >= 2:
            continue

        if len(re.findall(r"\s{2,}", stripped)) >= 3:
            continue

        alpha_count = sum(
            ch.isalpha()
            for ch in stripped
        )

        if len(stripped) > 20 and alpha_count < len(stripped) * 0.35:
            continue

        final_lines.append(stripped)

    return "\n".join(
        final_lines
    )


def normalize_whitespace(text: str) -> str:
    """
    Normalize spaces and line breaks.
    """

    text = text.replace(
        "\r",
        "\n"
    )

    text = text.replace(
        "\f",
        "\n"
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s+\n",
        "\n\n",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def clean_legal_text(raw_text: str) -> str:
    """
    Main cleaning function.

    Input  : raw extracted PDF text
    Output : cleaned legal text
    """

    if not raw_text:
        return ""

    text = raw_text

    text = remove_page_numbers(
        text
    )

    text = normalize_whitespace(
        text
    )

    lines = text.split("\n")

    lines = [
        line.strip()
        for line in lines
    ]

    lines = remove_repeated_headers_footers(
        lines
    )

    text = "\n".join(
        lines
    )

    text = remove_signature_blocks(
        text
    )

    text = remove_table_like_lines(
        text
    )

    text = normalize_whitespace(
        text
    )

    return text