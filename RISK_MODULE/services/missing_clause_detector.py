from openai import OpenAI
import json
import re

from services.config import settings


client = OpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    timeout=settings.LLM_TIMEOUT
)


MODEL_NAME = settings.LLM_MODEL_NAME


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def clean_missing_clause_text(text: str) -> str:
    """
    Clean text returned by LLM.
    """

    if not text:
        return ""

    cleaned = str(text).strip()
    cleaned = cleaned.replace("\n", " ")
    cleaned = " ".join(cleaned.split())

    replacements = {
        "client's": "Client's",
        "law firm": "Law Firm",
        "client": "Client",
        "agreement": "Agreement",
        "governing law and jurisdiction": "governing law and jurisdiction",
        "dispute resolution": "dispute resolution"
    }

    for wrong, correct in replacements.items():
        cleaned = cleaned.replace(wrong, correct)

    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."

    return cleaned


def extract_missing_json(raw: str):
    """
    Extract JSON object from LLM output.
    Expected:
    {
      "missing_clauses": [
        {
          "missing_clause": "...",
          "reason": "...",
          "suggested_clause": "..."
        }
      ]
    }
    """

    if not raw:
        return None

    raw = str(raw).strip()

    raw = raw.replace("```json", "").replace("```", "").strip()

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        obj = json.loads(raw[start:end + 1])
        return obj.get("missing_clauses", [])
    except Exception:
        return None


def detect_document_type(full_text: str) -> str:
    """
    Lightweight semantic document type detection.
    Used only to choose a fallback checklist.
    """

    text = _norm(full_text)

    if any(x in text for x in [
        "employee",
        "employer",
        "employment agreement",
        "salary",
        "probation",
        "notice period"
    ]):
        return "employment"

    if any(x in text for x in [
        "law firm",
        "legal services agreement",
        "attorney",
        "client's file",
        "lawyer-client privilege",
        "estate plan",
        "billing error"
    ]):
        return "legal_services"

    if any(x in text for x in [
        "power of attorney",
        "principal",
        "attorney-in-fact",
        "agent",
        "execute sale deed"
    ]):
        return "power_of_attorney"

    if any(x in text for x in [
        "non-disclosure",
        "nda",
        "confidential information",
        "receiving party",
        "disclosing party"
    ]):
        return "nda"

    if any(x in text for x in [
        "lease",
        "landlord",
        "tenant",
        "premises",
        "rent",
        "security deposit"
    ]):
        return "lease"

    if any(x in text for x in [
        "loan",
        "borrower",
        "lender",
        "interest rate",
        "default",
        "repayment"
    ]):
        return "loan"

    if any(x in text for x in [
        "service provider",
        "customer",
        "vendor",
        "deliverables",
        "statement of work",
        "scope of services"
    ]):
        return "service_agreement"

    return "general_contract"


def has_substantially_similar_clause(full_text: str, missing_name: str) -> bool:
    """
    Prevent duplicate missing clauses where the document already contains
    a substantially similar clause.
    """

    text = _norm(full_text)
    name = _norm(missing_name)

    checks = {
        "client termination": [
            "client may discharge law firm",
            "client may terminate",
            "discharge of law firm"
        ],
        "law firm withdrawal": [
            "withdrawal of law firm",
            "law firm may withdraw",
            "rules permit such withdrawal",
            "withdraw as client's attorney"
        ],
        "document retention": [
            "document retention",
            "retain client's file",
            "destroy all files",
            "storage facility",
            "client's file"
        ],
        "facsimile signature": [
            "facsimile signature",
            "facsimile signature on this agreement",
            "original signature"
        ],
        "client cooperation": [
            "client will be truthful and cooperative",
            "client will be truthful",
            "provide on a timely basis all information",
            "client keeping law firm fully informed"
        ],
        "scope of services": [
            "legal services to be provided",
            "services to be provided",
            "preparation of the following documents"
        ],
        "withdrawal": [
            "withdrawal of law firm",
            "law firm may withdraw",
            "rules permit such withdrawal"
        ],
        "termination": [
            "client may discharge law firm",
            "discharge of law firm",
            "effective when received by law firm"
        ],
        "file return": [
            "release of client's papers",
            "relinquish client's original documents",
            "client's original documents",
            "five working days written notice"
        ],
        "severability": [
            "severability",
            "partial invalidity",
            "unenforceable for any reason"
        ],
        "entire agreement": [
            "entire agreement",
            "complete agreement",
            "supersedes all previous"
        ],
        "modification": [
            "modified by subsequent agreement",
            "instrument in writing signed by both",
            "modified by written agreement"
        ],
        "signature": [
            "facsimile signature",
            "original signature",
            "signed copy"
        ],
        "effective date": [
            "effective date",
            "agreement will be the date"
        ]
    }

    for topic, patterns in checks.items():
        if topic in name:
            if any(pattern in text for pattern in patterns):
                return True

    return False


def should_convert_to_inadequate(full_text: str, missing_name: str) -> bool:
    """
    Some clauses are present but weak/unfair.
    In that case, use 'Unclear or inadequate ...' instead of removing.
    """

    text = _norm(full_text)
    name = _norm(missing_name)

    if "confidential" in name:
        weak_confidentiality_signals = [
            "no information will be kept confidential",
            "neither of you will be able to invoke the lawyer-client privilege",
            "fully and freely disclosed to the other"
        ]

        if any(signal in text for signal in weak_confidentiality_signals):
            return True

    if "billing" in name or "invoice" in name:
        weak_billing_signals = [
            "deemed to have been accepted",
            "without adjustment of any kind",
            "billing error or dispute within 30 days"
        ]

        if any(signal in text for signal in weak_billing_signals):
            return True

    return False


def normalize_missing_clause(item: dict) -> dict:
    """
    Normalize output keys.
    """

    if not isinstance(item, dict):
        item = {}

    name = (
        item.get("missing_clause")
        or item.get("name")
        or item.get("clause_name")
        or item.get("title")
        or "Missing Important Clause"
    )

    reason = (
        item.get("reason")
        or item.get("why_important")
        or "This clause may be important for legal certainty and contractual protection."
    )

    suggested_clause = (
        item.get("suggested_clause")
        or item.get("recommended_clause")
        or "The parties shall include a clear and balanced clause addressing this issue in accordance with applicable law."
    )

    return {
        "missing_clause": clean_missing_clause_text(name),
        "reason": clean_missing_clause_text(reason),
        "suggested_clause": clean_missing_clause_text(suggested_clause)
    }


def filter_missing_clauses(full_text: str, missing_clauses: list) -> list:
    """
    Remove duplicates and clauses already present in the document.
    Convert weak present clauses to 'Unclear or inadequate ...' when appropriate.
    """

    filtered = []
    seen = set()

    for item in missing_clauses:
        normalized = normalize_missing_clause(item)

        name = normalized["missing_clause"]
        key = _norm(name)

        if not key:
            continue

        if key in seen:
            continue

        if should_convert_to_inadequate(full_text, name):
            if not key.startswith("unclear or inadequate"):
                normalized["missing_clause"] = f"Unclear or inadequate {name}"
                normalized["reason"] = (
                    "The document appears to contain a related clause, but the wording may be incomplete, weak, or one-sided and should be clarified."
                )

            key = _norm(normalized["missing_clause"])

        elif has_substantially_similar_clause(full_text, name):
            continue

        seen.add(key)
        filtered.append(normalized)

    return filtered[:8]


def fallback_missing_clauses(full_text: str) -> list:
    """
    Reliable local fallback if LLM fails.
    Returns generic but useful missing/unclear clauses based on document type.
    """

    doc_type = detect_document_type(full_text)

    if doc_type == "legal_services":
        items = [
            {
                "missing_clause": "Unclear or inadequate confidentiality and privilege clause",
                "reason": "Legal services may involve sensitive client information, and the agreement should clearly explain confidentiality and privilege treatment.",
                "suggested_clause": "Law Firm shall maintain the confidentiality of Client information except as required by law, applicable professional conduct rules, or informed written consent of Client."
            },
            {
                "missing_clause": "Limitation of Liability Clause",
                "reason": "A legal services agreement should define reasonable limits for liability while preserving remedies for gross negligence, fraud, or wilful misconduct.",
                "suggested_clause": "Law Firm shall not be liable for indirect or consequential losses, except to the extent caused by Law Firm's gross negligence, fraud, or wilful misconduct, and any limitation shall comply with applicable professional rules."
            },
            {
                "missing_clause": "Governing Law and Jurisdiction Clause",
                "reason": "The agreement should clearly state the law and forum that will govern disputes.",
                "suggested_clause": "This Agreement shall be governed by the laws applicable to the jurisdiction where Law Firm provides the legal services, and disputes shall be resolved by courts or forums having competent jurisdiction."
            },
            {
                "missing_clause": "Dispute Resolution Clause",
                "reason": "A dispute resolution clause provides a clear process for resolving fee or service-related disputes.",
                "suggested_clause": "The parties shall first attempt to resolve disputes in good faith, and unresolved disputes may be submitted to mediation, arbitration, fee dispute resolution, or a competent court as permitted by applicable law."
            },
            {
                "missing_clause": "Clear billing dispute escalation process",
                "reason": "The agreement should clearly explain how billing disputes will be raised, reviewed, and resolved.",
                "suggested_clause": "Client may dispute any invoice in writing within a reasonable period, and Law Firm shall review the dispute in good faith before imposing collection costs, interest, or service charges on the disputed amount."
            },
            {
                "missing_clause": "Data Protection and Privacy Clause",
                "reason": "Legal services may involve sensitive personal and financial information, which should be protected.",
                "suggested_clause": "Law Firm shall process and store Client personal information only for legitimate legal services purposes and shall apply reasonable administrative, technical, and organizational safeguards."
            }
        ]

        return filter_missing_clauses(full_text, items)

    if doc_type == "employment":
        items = [
            {
                "missing_clause": "Clear job responsibilities and performance standards",
                "reason": "Employment agreements should clearly define the employee's role and performance expectations.",
                "suggested_clause": "The Employee's duties, reporting structure, performance standards, and working arrangements shall be clearly communicated in writing and applied fairly."
            },
            {
                "missing_clause": "Governing Law and Jurisdiction Clause",
                "reason": "The agreement should specify applicable law and forum for disputes.",
                "suggested_clause": "This Agreement shall be governed by applicable Indian law, and disputes shall be subject to the jurisdiction of competent courts or forums as agreed by the parties."
            },
            {
                "missing_clause": "Dispute Resolution Clause",
                "reason": "Employment disputes should have a clear and fair resolution process.",
                "suggested_clause": "The parties shall first attempt to resolve disputes amicably, and unresolved disputes may be referred to mediation, arbitration, labour authorities, or courts as permitted by law."
            },
            {
                "missing_clause": "Data Protection and Privacy Clause",
                "reason": "Employee personal information should be handled with appropriate safeguards.",
                "suggested_clause": "Employer shall collect and process Employee personal data only for legitimate employment purposes and in accordance with applicable data protection requirements."
            }
        ]

        return filter_missing_clauses(full_text, items)

    if doc_type == "power_of_attorney":
        items = [
            {
                "missing_clause": "Revocation and Termination Clause",
                "reason": "A power of attorney should clearly explain when and how authority ends.",
                "suggested_clause": "This Power of Attorney may be revoked by the Principal by written notice and shall terminate upon completion of the specified purpose or as required by law."
            },
            {
                "missing_clause": "Attorney-in-Fact Duties and Records Clause",
                "reason": "The agent should be required to act in good faith and maintain transaction records.",
                "suggested_clause": "The Attorney-in-Fact shall act in good faith, within the scope of authority granted, and maintain accurate records of all acts performed under this Power of Attorney."
            },
            {
                "missing_clause": "Limitation of Authority Clause",
                "reason": "Broad authority can create misuse risk unless limited.",
                "suggested_clause": "The Attorney-in-Fact may perform only the specific acts expressly authorized in this instrument and shall not transfer or encumber property unless expressly permitted."
            },
            {
                "missing_clause": "Governing Law and Jurisdiction Clause",
                "reason": "The governing law and forum should be clear.",
                "suggested_clause": "This Power of Attorney shall be governed by applicable law, and disputes shall be resolved before competent courts having jurisdiction."
            }
        ]

        return filter_missing_clauses(full_text, items)

    items = [
        {
            "missing_clause": "Governing Law and Jurisdiction Clause",
            "reason": "Most contracts should specify governing law and dispute forum.",
            "suggested_clause": "This Agreement shall be governed by applicable law, and disputes shall be subject to the jurisdiction of competent courts or agreed dispute resolution forums."
        },
        {
            "missing_clause": "Dispute Resolution Clause",
            "reason": "A dispute resolution mechanism reduces uncertainty if disputes arise.",
            "suggested_clause": "The parties shall first attempt good-faith resolution, and unresolved disputes may be submitted to mediation, arbitration, or competent courts as agreed by the parties."
        },
        {
            "missing_clause": "Confidentiality Clause",
            "reason": "Contracts often involve confidential information that should be protected.",
            "suggested_clause": "Each party shall protect confidential information received from the other and use it only for legitimate contractual purposes, subject to customary legal exceptions."
        },
        {
            "missing_clause": "Limitation of Liability Clause",
            "reason": "A liability clause helps define fair responsibility and reduce excessive exposure.",
            "suggested_clause": "Each party's liability shall be limited to direct losses caused by proven breach, negligence, fraud, or wilful misconduct, subject to reasonable limits permitted by law."
        }
    ]

    return filter_missing_clauses(full_text, items)


def build_missing_clause_prompt(full_text: str) -> str:
    """
    Build prompt for semantic missing/unclear clause detection.
    """

    excerpt = str(full_text or "")

    if len(excerpt) > 12000:
        excerpt = excerpt[:12000]

    doc_type = detect_document_type(full_text)

    prompt = f"""
You are a professional legal contract review assistant.

You must detect only important clauses that are truly missing or materially unclear/inadequate.

Document type detected:
{doc_type}

Document text:
{excerpt}

Return ONLY valid JSON.
Do not use markdown.
Do not use code fences.
Do not include explanation outside JSON.

Output format:
{{
  "missing_clauses": [
    {{
      "missing_clause": "name of missing or unclear/inadequate clause",
      "reason": "one short reason why it matters",
      "suggested_clause": "one complete suggested clause"
    }}
  ]
}}

Important rules:
- Do not list a clause as missing if the document already contains a substantially similar clause.
- If a clause exists but is vague, unfair, one-sided, incomplete, or weak, label it as "Unclear or inadequate [clause name]" instead of "Missing [clause name]".
- Avoid recommending generic clauses that already exist in the document, such as client termination, law firm withdrawal, document retention, facsimile signature, client cooperation, confidentiality, scope of services, severability, entire agreement, or modification.
- Only return clauses that are truly absent or materially inadequate.
- Before returning each item, compare it against the document text and ask: "Is a substantially similar clause already present?" If yes, do not return it unless the issue is material inadequacy.
- Return at most 8 items.
- Prefer practical and important legal protections, not minor boilerplate.

For legal services agreements, focus only on truly missing or inadequate:
- confidentiality and privilege protection,
- limitation of liability,
- governing law and jurisdiction,
- dispute resolution or billing dispute process,
- data protection and privacy,
- client file return if absent or weak,
- fee dispute process if absent or weak.

For employment agreements, focus only on truly missing or inadequate:
- fair termination process,
- wage/salary protection,
- job responsibilities,
- dispute resolution,
- governing law,
- data protection,
- non-compete/non-solicitation fairness.

For power of attorney documents, focus only on truly missing or inadequate:
- revocation/termination,
- agent duties,
- accounting and records,
- limitation of authority,
- dispute resolution,
- governing law.

Return only JSON.
"""

    return prompt


def detect_missing_clauses(full_text: str) -> list:
    """
    Semantic missing/unclear clause detector.
    Works across document types and avoids duplicate missing clauses.
    """

    if not full_text or not str(full_text).strip():
        return []

    prompt = build_missing_clause_prompt(full_text)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict legal missing clause detector. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=2200
        )

        raw = response.choices[0].message.content

        parsed = extract_missing_json(raw)

        if parsed is None:
            raise ValueError("Missing clause detector did not return valid JSON")

        normalized = [
            normalize_missing_clause(item)
            for item in parsed
        ]

        filtered = filter_missing_clauses(
            full_text,
            normalized
        )

        if filtered:
            return filtered

        return fallback_missing_clauses(full_text)

    except Exception as e:
        print(
            "Missing clause detector failed:",
            str(e)[:150]
        )

        return fallback_missing_clauses(full_text)