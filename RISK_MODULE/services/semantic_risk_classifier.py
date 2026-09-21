from openai import OpenAI
import json

from services.config import settings


client = OpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    timeout=settings.LLM_TIMEOUT
)


MODEL_NAME = settings.LLM_MODEL_NAME


_CACHE = {}


def extract_json(raw: str):
    """
    Extract JSON object from LLM response.
    """

    if not raw:
        return None

    raw = raw.strip()

    if "```" in raw:
        parts = raw.split("```")

        for part in parts:
            part = part.strip()

            if part.startswith("json"):
                part = part[4:].strip()

            if part.startswith("{"):
                raw = part
                break

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(
            raw[start:end + 1]
        )
    except Exception:
        return None


def normalize_semantic_result(
    result: dict,
    default_category: str
) -> dict:
    """
    Normalize semantic classifier output.
    """

    if not result:
        result = {}

    risk_level = str(
        result.get("risk_level", "MEDIUM")
    ).upper().strip()

    if risk_level not in [
        "HIGH",
        "MEDIUM",
        "LOW"
    ]:
        risk_level = "MEDIUM"

    risk_score_map = {
        "HIGH": 90,
        "MEDIUM": 60,
        "LOW": 20
    }

    confidence = result.get(
        "confidence",
        0.60
    )

    try:
        confidence = float(
            confidence
        )
    except Exception:
        confidence = 0.60

    confidence = max(
        0.0,
        min(1.0, confidence)
    )

    category = result.get(
        "category",
        default_category
    )

    detected_issue = result.get(
        "detected_issue",
        "Semantic legal risk review"
    )

    # If model is unsure, avoid LOW.
    if risk_level == "LOW" and confidence < 0.65:
        risk_level = "MEDIUM"
        detected_issue = "Uncertain legal risk requiring review"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score_map[risk_level],
        "category": category,
        "detected_issue": detected_issue,
        "classifier": "semantic_general_groq",
        "confidence": round(
            confidence,
            2
        )
    }

def fallback_keyword_risk(clause: str, default_category: str) -> dict:
    """
    Local fallback if semantic LLM fails or rate limit occurs.
    Prevents all clauses becoming generic MEDIUM.
    """

    text = clause.lower()

    high_patterns = {
        "Termination without notice": [
            "without notice",
            "immediate effect",
            "without giving any notice",
            "terminate any time",
            "dismissed forthwith"
        ],
        "Employee penalty": [
            "penalty",
            "rs. 2 lakhs",
            "liable to pay",
            "break of bond"
        ],
        "Long non-compete": [
            "not open similar",
            "three years",
            "non compete",
            "non-compete"
        ],
        "Unilateral amendment": [
            "modify the agreement",
            "from time to time",
            "applicable from the same day",
            "subject to change"
        ],
        "Broad authority": [
            "power of attorney",
            "irrevocable",
            "sell",
            "transfer",
            "mortgage",
            "sale deed",
            "all acts",
            "all deeds",
            "all documents"
        ],
        "Unlimited liability": [
            "unlimited liability",
            "without limitation",
            "all losses",
            "all damages"
        ]
    }

    medium_patterns = {
        "Ambiguous obligation": [
            "best efforts",
            "reasonable efforts",
            "sole discretion",
            "as decided by",
            "final and binding"
        ],
        "Broad confidentiality": [
            "during and after",
            "confidential",
            "trade secret"
        ],
        "Client restriction": [
            "client",
            "customer",
            "directly or indirectly"
        ]
    }

    for issue, patterns in high_patterns.items():
        if any(p in text for p in patterns):
            return {
                "risk_level": "HIGH",
                "risk_score": 90,
                "category": default_category,
                "detected_issue": issue,
                "classifier": "local_keyword_fallback",
                "confidence": 0.70
            }

    for issue, patterns in medium_patterns.items():
        if any(p in text for p in patterns):
            return {
                "risk_level": "MEDIUM",
                "risk_score": 60,
                "category": default_category,
                "detected_issue": issue,
                "classifier": "local_keyword_fallback",
                "confidence": 0.60
            }

    return {
        "risk_level": "LOW",
        "risk_score": 20,
        "category": default_category,
        "detected_issue": "No major unfair risk pattern detected",
        "classifier": "local_keyword_fallback",
        "confidence": 0.50
    }
def classify_semantic_risk(
    clause: str,
    default_category: str = "General Legal Clause"
) -> dict:
    """
    Universal semantic risk classifier.

    This classifier is designed to classify clauses from any legal document type,
    not only employment agreements.
    """

    clause = clause.strip()

    if not clause:
        return {
            "risk_level": "LOW",
            "risk_score": 0,
            "category": "Non-Legal Text",
            "detected_issue": "Empty clause",
            "classifier": "semantic_general_groq",
            "confidence": 0.0
        }

    if clause in _CACHE:
        return _CACHE[clause]

    prompt = f"""
You are a strict legal risk classification engine.

Return ONLY valid JSON.
Do not write markdown.
Do not explain outside JSON.

You are classifying one clause from a legal document.

The clause may come from any legal document type, including:
- Employment Agreement
- Power of Attorney
- Non-Disclosure Agreement
- Service Agreement
- Lease Agreement
- Sale Agreement
- Development Agreement
- Consultancy Agreement
- Partnership Agreement
- Property Agreement
- General Commercial Contract

Classify the clause into exactly one risk level:
HIGH, MEDIUM, or LOW.

Risk rubric:

HIGH risk means the clause clearly creates serious legal, financial, employment, property, privacy, operational, or contractual harm. Examples include:
- one party can terminate without reasonable notice
- salary, payment, refund, or compensation can be withheld unfairly
- monetary penalty, bond, or damages appear excessive or one-sided
- employee, customer, principal, tenant, buyer, or signer has unlimited liability
- indemnity is one-sided, broad, or uncapped
- rights or intellectual property are transferred too broadly
- confidentiality is unlimited or has no reasonable exceptions
- non-compete or non-solicit is broad, long, or restricts livelihood
- one party can change important terms unilaterally
- party waives legal rights or claims broadly
- dispute resolution is controlled by only one party
- personal data, biometric monitoring, surveillance, or sensitive data is used without safeguards
- Power of Attorney grants broad authority over property, money, documents, court matters, bank accounts, or legal rights without safeguards
- attorney or agent can sell, transfer, mortgage, gift, register, or dispose of property
- attorney or agent can execute sale deeds, mortgage deeds, agreements to sell, or property documents without clear limits
- attorney or agent can receive consideration or money on behalf of the principal without accountability
- attorney or agent can settle disputes, compromise claims, or represent the principal without consent
- authority is irrevocable without clear reason, time limit, accountability, or revocation process

MEDIUM risk means the clause needs careful review but is not clearly severe. Examples include:
- wording is vague or ambiguous
- one party has broad discretion but not complete control
- obligations are unclear
- policies may change without a clear process
- authority is broad but appears connected to a specific transaction
- risk depends on surrounding clauses

LOW risk means:
- standard administrative clause
- routine recital, address, identity, or schedule clause
- balanced mutual obligation
- clear and limited authority
- no major unfairness
- no unusual legal, financial, property, privacy, or employment burden

Important classification rules:
- Do not mark a clause LOW only because it does not match common examples.
- Do not mark ordinary administrative address, identity, schedule, or recital clauses as HIGH.
- If the clause grants broad legal authority over property, money, bank accounts, documents, court matters, or rights, do not mark it LOW.
- If unsure between HIGH and MEDIUM, choose MEDIUM.
- If unsure between MEDIUM and LOW, choose MEDIUM only when the clause contains real ambiguity or legal consequence.
- Consider risk to the weaker party, signer, employee, customer, principal, property owner, or client.
- Classify based on legal effect, not document title.
- Use short professional category names.
- Use short detected_issue names.

Clause:
{clause}

Return JSON exactly:

{{
  "risk_level": "HIGH or MEDIUM or LOW",
  "category": "short clause category",
  "detected_issue": "short issue name",
  "confidence": 0.0
}}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict legal risk classifier. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=250
        )

        raw = response.choices[0].message.content

        result = extract_json(
            raw
        )

        output = normalize_semantic_result(
            result,
            default_category
        )

        _CACHE[clause] = output

        return output

    except Exception as e:
        print(
            "Semantic classifier failed:",
            str(e)[:150]
        )

        fallback = fallback_keyword_risk(
            clause,
            default_category
        )

        _CACHE[clause] = fallback

        return fallback
def _batch_local_fallback(clause: str, default_category: str) -> dict:
    """
    Safe local fallback used only when batch LLM classification fails.
    It tries existing fallback_keyword_risk first, then existing single semantic classifier,
    then returns a conservative MEDIUM result.
    """

    try:
        if "fallback_keyword_risk" in globals():
            return fallback_keyword_risk(
                clause,
                default_category
            )
    except Exception:
        pass

    try:
        if "classify_semantic_risk" in globals():
            return classify_semantic_risk(
                clause,
                default_category
            )
    except Exception:
        pass

    return {
        "risk_level": "MEDIUM",
        "risk_score": 60,
        "category": default_category,
        "detected_issue": "Manual legal review required",
        "classifier": "batch_local_fallback",
        "confidence": 0.60
    }


def _normalize_batch_item(item: dict, default_category: str) -> dict:
    """
    Normalize one LLM classifier output item.
    """

    risk_level = str(
        item.get(
            "risk_level",
            "MEDIUM"
        )
    ).upper().strip()

    if risk_level not in [
        "HIGH",
        "MEDIUM",
        "LOW"
    ]:
        risk_level = "MEDIUM"

    try:
        risk_score = int(
            item.get(
                "risk_score",
                60
            )
        )
    except Exception:
        risk_score = 60

    if risk_level == "HIGH":
        risk_score = max(
            risk_score,
            80
        )
    elif risk_level == "MEDIUM":
        risk_score = min(
            max(
                risk_score,
                40
            ),
            79
        )
    else:
        risk_score = min(
            risk_score,
            39
        )

    try:
        confidence = float(
            item.get(
                "confidence",
                0.75
            )
        )
    except Exception:
        confidence = 0.75

    if confidence <= 0:
        if risk_level == "HIGH":
            confidence = 0.85
        elif risk_level == "MEDIUM":
            confidence = 0.65
        else:
            confidence = 0.75

    confidence = max(
        0.50,
        min(
            confidence,
            1.00
        )
    )

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "category": item.get(
            "category",
            default_category
        ),
        "detected_issue": item.get(
            "detected_issue",
            "Legal review required"
        ),
        "classifier": "semantic_general_groq_batch",
        "confidence": confidence
    }


def _parse_json_array_from_llm(content: str):
    """
    Parse JSON array safely from LLM response.
    """

    import json
    import re

    content = str(
        content
    ).strip()

    content = content.replace(
        "```json",
        ""
    ).replace(
        "```",
        ""
    ).strip()

    try:
        return json.loads(
            content
        )
    except Exception:
        pass

    match = re.search(
        r"\[[\s\S]*\]",
        content
    )

    if not match:
        raise ValueError(
            "No JSON array found in batch classifier response"
        )

    return json.loads(
        match.group(0)
    )


def classify_semantic_risk_batch(
    clauses,
    default_category="General Legal Clause",
    batch_size=10
):
    """
    Batch semantic risk classifier.

    Purpose:
    - Analyze full document.
    - Keep classification semantic/LLM-based.
    - Reduce many single LLM calls into fewer batch calls.
    - Fall back safely if Groq/rate-limit/parser fails.
    """

    import time

    results = []

    if not clauses:
        return results

    client_obj = globals().get(
        "client"
    )

    settings_obj = globals().get(
        "settings"
    )

    if client_obj is None or settings_obj is None:
        print(
            "Batch classifier could not find client/settings. Falling back to single classifier."
        )

        return [
            _batch_local_fallback(
                str(clause),
                default_category
            )
            for clause in clauses
        ]

    for start in range(
        0,
        len(clauses),
        batch_size
    ):
        batch = clauses[
            start:start + batch_size
        ]

        try:
            numbered_clauses = []

            for idx, clause in enumerate(
                batch,
                start=1
            ):
                numbered_clauses.append(
                    f"{idx}. {str(clause)}"
                )

            prompt = f"""
You are an Indian legal contract risk classifier.

Classify each clause independently.

Return ONLY a valid JSON array.
No markdown.
No explanation outside JSON.

For each clause return exactly:
- risk_level: HIGH, MEDIUM, or LOW
- risk_score: integer from 0 to 100
- category: short legal category
- detected_issue: short issue name
- confidence: number between 0.50 and 1.00

Risk rules:
HIGH = unfair termination, service suspension without notice or cure period, salary/payment withholding, employee/client penalty, bond penalty, long non-compete, unilateral modification, unlimited liability, broad lien over recovery or property, uncapped collection costs, waiver of legal rights, privilege waiver, no confidentiality in sensitive representation, immediate dismissal or withdrawal without safeguards, one-sided dispute decision, broad indemnity, file destruction without adequate notice, unilateral rate increase, unrestricted property authority, broad data use, broad warranty disclaimer, acceleration without cure period.

MEDIUM = vague obligation, broad confidentiality, discretionary power, unclear process, broad work location, unclear authority, broad policy compliance, professional service scope ambiguity, deemed acceptance of charges, short billing dispute window, additional services billed without clear approval, client cooperation obligations, document return delays, file retrieval fee, conflict disclosure requiring informed consent, joint and several payment liability, auto-renewal, assignment without consent, unclear acceptance process.

LOW = standard/admin/commercial clause with no major unfair legal risk, party identification, severability, mutual written modification, standard signature, standard effective date, reasonable notice and cure periods, standard disclaimer of guaranteed outcome, insurance disclosure, capped mutual liability, confidentiality with exceptions, neutral dispute resolution.
Return one JSON object per input clause in the same order.

Clauses:
{chr(10).join(numbered_clauses)}
"""

            response = client_obj.chat.completions.create(
                model=settings_obj.LLM_MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a strict legal risk classifier. Return only valid JSON array."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=3500,
                timeout=getattr(
                    settings_obj,
                    "LLM_TIMEOUT",
                    30
                )
            )

            content = response.choices[0].message.content

            parsed = _parse_json_array_from_llm(
                content
            )

            if not isinstance(
                parsed,
                list
            ):
                raise ValueError(
                    "Batch classifier did not return a JSON list"
                )

            for idx, clause in enumerate(
                batch
            ):
                if idx < len(parsed) and isinstance(
                    parsed[idx],
                    dict
                ):
                    results.append(
                        _normalize_batch_item(
                            parsed[idx],
                            default_category
                        )
                    )
                else:
                    results.append(
                        _batch_local_fallback(
                            str(clause),
                            default_category
                        )
                    )

        except Exception as e:
            print(
                f"Batch semantic classifier failed: {e}"
            )

            for clause in batch:
                results.append(
                    _batch_local_fallback(
                        str(clause),
                        default_category
                    )
                )

        time.sleep(
            0.5
        )

    return results