import json
import re
import time
from services.semantic_risk_classifier import classify_semantic_risk, fallback_keyword_risk

def classify_semantic_risk_batch(clauses, default_category="General Legal Clause", batch_size=10):
    """
    Classify multiple clauses in fewer LLM calls.
    Full document analysis remains complete, but classification becomes efficient.
    """

    results = []

    if not clauses:
        return results

    for start in range(0, len(clauses), batch_size):
        batch = clauses[start:start + batch_size]

        try:
            numbered_clauses = []
            for i, clause in enumerate(batch, start=1):
                numbered_clauses.append(f"{i}. {clause}")

            prompt = f"""
You are an Indian legal contract risk classifier.

Classify each clause independently.

Return ONLY valid JSON array. No markdown. No explanation outside JSON.

For each clause return:
- risk_level: HIGH, MEDIUM, or LOW
- risk_score: integer 0-100
- category: short legal category
- detected_issue: short issue name
- confidence: number between 0.50 and 1.00

Risk rules:
HIGH = unfair termination, penalty, salary withholding, long non-compete, unilateral modification, unlimited liability, waiver of legal rights, one-sided dispute decision, broad indemnity, immediate dismissal without due process.
MEDIUM = vague obligation, broad confidentiality, discretionary power, unclear process, broad work location, unclear authority.
LOW = standard/admin/commercial clause with no major unfairness.

Clauses:
{chr(10).join(numbered_clauses)}
"""

            response = client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
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
                temperature=0.1,
                max_tokens=3000,
                timeout=settings.LLM_TIMEOUT
            )

            content = response.choices[0].message.content.strip()

            # remove markdown fences if any
            content = content.replace("```json", "").replace("```", "").strip()

            parsed = json.loads(content)

            if not isinstance(parsed, list):
                raise ValueError("Batch classifier did not return a JSON list")

            # ensure same length
            for idx, clause in enumerate(batch):
                if idx < len(parsed) and isinstance(parsed[idx], dict):
                    item = parsed[idx]

                    risk_level = str(item.get("risk_level", "MEDIUM")).upper().strip()
                    if risk_level not in ["HIGH", "MEDIUM", "LOW"]:
                        risk_level = "MEDIUM"

                    try:
                        risk_score = int(item.get("risk_score", 60))
                    except Exception:
                        risk_score = 60

                    if risk_level == "HIGH":
                        risk_score = max(risk_score, 80)
                    elif risk_level == "MEDIUM":
                        risk_score = min(max(risk_score, 40), 79)
                    else:
                        risk_score = min(risk_score, 39)

                    try:
                        confidence = float(item.get("confidence", 0.75))
                    except Exception:
                        confidence = 0.75

                    if confidence <= 0:
                        if risk_level == "HIGH":
                            confidence = 0.85
                        elif risk_level == "MEDIUM":
                            confidence = 0.65
                        else:
                            confidence = 0.75

                    results.append({
                        "risk_level": risk_level,
                        "risk_score": risk_score,
                        "category": item.get("category", default_category),
                        "detected_issue": item.get("detected_issue", "Legal review required"),
                        "classifier": "semantic_general_groq_batch",
                        "confidence": confidence
                    })
                else:
                    results.append(fallback_keyword_risk(clause, default_category))

        except Exception as e:
            print(f"Batch semantic classifier failed: {e}")

            for clause in batch:
                results.append(fallback_keyword_risk(clause, default_category))

        # small pause to avoid rate limit
        time.sleep(0.5)

    return results
def is_non_legal_or_garbage(clause: str) -> bool:
    if not clause:
        return True

    text = clause.strip()

    if len(text.split()) < 6:
        return True

    alpha_count = sum(
        ch.isalpha()
        for ch in text
    )

    if len(text) > 20 and alpha_count < len(text) * 0.30:
        return True

    return False


def classify_risk(clause: str) -> dict:
    """
    Final semantic-first risk classifier.
    Every meaningful legal clause is sent to the semantic classifier.
    """

    if is_non_legal_or_garbage(clause):
        return {
            "risk_level": "LOW",
            "risk_score": 0,
            "category": "Non-Legal Text",
            "detected_issue": "Not enough legal content",
            "classifier": "semantic_input_filter",
            "confidence": 0.0
        }

    return classify_semantic_risk(
        clause,
        default_category="General Legal Clause"
    )