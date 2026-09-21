from openai import OpenAI
import json

from services.config import settings


client = OpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    timeout=settings.LLM_TIMEOUT
)


MODEL_NAME = settings.LLM_MODEL_NAME


def extract_json(raw: str):
    """
    Extract JSON from LLM response.
    Handles markdown/code-fence responses.
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


def clean_generated_text(text: str) -> str:
    """
    Clean minor formatting issues in generated legal text.
    """

    if not text:
        return ""

    cleaned = str(text).strip()

    replacements = {
        "allowsthe": "allows the",
        "canlead": "can lead",
        "orbond": "or bond",
        "systemwith": "system with",
        "apenalty": "a penalty",
        "rs.75": "Rs. 75",
        "rs.50": "Rs. 50",
        "rs.1": "Rs. 1",
        "otherwiserequired": "otherwise required",
        "shallrequire": "shall require",
        "calculatedbased": "calculated based",
        "withoutany": "without any",
        "dueto": "due to",
        "mayterminate": "may terminate",
        "caseno": "case no",
        "uponproviding": "upon providing",
        "priorto": "prior to",
        "writtennotice": "written notice",
        "withoutproviding": "without providing",
        "inwhich": "in which",
        "theemployee": "the employee",
        "employment of theemployee": "employment of the employee",
        "andneither": "and neither",
        "informationand": "information and",
        "withoutthe": "without the",
        "thecompany": "the company",
        "employmentterms": "employment terms",
        
        "agreementthat": "agreement that",
        "interestsof": "interests of",
        "employmentlaws": "employment laws",
        "theemployer": "the employer",
        "broadproperty": "broad property",
        "legalrights": "legal rights"
    }

    for wrong, correct in replacements.items():
        cleaned = cleaned.replace(
            wrong,
            correct
        )

    cleaned = cleaned.replace(
        "\n",
        " "
    )

    cleaned = " ".join(
        cleaned.split()
    )

    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."

    return cleaned


def infer_clause_context(
    clause: str,
    risk_result: dict
) -> str:
    """
    Infer document/clause context to prevent employment-specific safer clauses
    from being generated for non-employment documents.
    """

    text = str(clause or "").lower()

    category = str(
        risk_result.get("category", "")
    ).lower()

    combined = f"{text} {category}"

    if any(word in combined for word in [
        "employee",
        "employer",
        "employment",
        "salary",
        "notice period",
        "probation",
        "non-compete",
        "misconduct"
    ]):
        return "employment"

    if any(word in combined for word in [
        "law firm",
        "client",
        "attorney",
        "legal services",
        "lawyer-client privilege",
        "joint representation",
        "estate plan",
        "billing",
        "lien for services",
        "client's file"
    ]):
        return "legal_services"

    if any(word in combined for word in [
        "power of attorney",
        "attorney-in-fact",
        "principal",
        "agent",
        "sale deed",
        "mortgage the property"
    ]):
        return "power_of_attorney"

    if any(word in combined for word in [
        "landlord",
        "tenant",
        "lease",
        "premises",
        "rent",
        "security deposit"
    ]):
        return "lease"

    if any(word in combined for word in [
        "borrower",
        "lender",
        "loan",
        "interest",
        "default",
        "acceleration"
    ]):
        return "loan"

    if any(word in combined for word in [
        "service provider",
        "customer",
        "vendor",
        "deliverables",
        "statement of work",
        "scope of services"
    ]):
        return "service_agreement"

    return "general_contract"


def safer_clause_context_mismatch(
    original_clause: str,
    safer_clause: str,
    context: str
) -> bool:
    """
    Detect if generated safer clause uses wrong employment-specific language
    for non-employment documents.
    """

    if not safer_clause:
        return True

    safer = str(safer_clause).lower()

    employment_terms = [
        "employee",
        "employer",
        "employment",
        "salary",
        "benefits",
        "accrued dues",
        "gross misconduct"
    ]

    if context != "employment":
        if any(term in safer for term in employment_terms):
            return True

    return False


def build_reasoning_prompt(
    clause: str,
    risk_result: dict,
    similar_clauses=None
) -> str:
    """
    Build strict legal reasoning prompt.
    Risk level is already decided by classifier.
    """

    if similar_clauses is None:
        similar_clauses = []

    context = infer_clause_context(
        clause,
        risk_result
    )

    similar_text = ""

    for item in similar_clauses[:3]:
        if isinstance(item, dict):
            clause_text = (
                item.get("clause_text")
                or item.get("clause")
                or item.get("text")
                or ""
            )

            clause_type = item.get(
                "clause_type",
                "Unknown"
            )

            risk_label = item.get(
                "risk_label",
                "Unknown"
            )

            source = item.get(
                "source",
                "Unknown"
            )

            similarity = item.get(
                "similarity_score",
                ""
            )

            act_name = item.get(
                "act_name",
                ""
            )

            section_reference = item.get(
                "section_reference",
                ""
            )

            similar_text += (
                f"- Source: {source}; "
                f"Act: {act_name}; "
                f"Section/Reference: {section_reference}; "
                f"Clause Type: {clause_type}; "
                f"Risk Label: {risk_label}; "
                f"Similarity: {similarity}\n"
                f"  Text: {clause_text[:500]}\n"
            )

    if not similar_text:
        similar_text = "No similar clauses available."

    prompt = f"""
You are a professional legal contract review assistant.

You must return ONLY valid JSON.
Do not write markdown.
Do not write explanation outside JSON.
Do not use code fences.
Do not change the classifier risk level.
Do not use placeholders such as [X], [days], [amount], [party], or [jurisdiction].

The classifier has already decided the risk level.

Detected Document Context:
{context}

Classifier Output:
- Risk Level: {risk_result.get("risk_level")}
- Category: {risk_result.get("category")}
- Detected Issue: {risk_result.get("detected_issue")}

Original Clause:
{clause}

Retrieved Similar Legal Clauses and Legal References:
{similar_text}

Your task:
1. Provide exactly one professional legal reason.
2. Provide exactly one recommended action.
3. Provide exactly one negotiation advice.
4. Provide exactly one safer rewritten clause.

Context rules:
- Match the safer clause to the actual document context.
- Do not assume the document is an employment agreement unless the original clause clearly contains employment terms.
- If context is legal_services, use party labels such as "Law Firm" and "Client".
- If context is service_agreement, use "Service Provider" and "Customer" or neutral "parties".
- If context is power_of_attorney, use "Principal" and "Attorney-in-Fact" or "Agent".
- If context is lease, use "Landlord" and "Tenant".
- If context is loan, use "Lender" and "Borrower".
- If context is general_contract, use neutral "party" or "parties".
- Never generate employment-specific remedies such as salary, employee benefits, accrued dues, probation, or gross misconduct unless the context is employment.

Return exactly this JSON structure:

{{
  "reason": "one clear professional legal reason",
  "action": "one specific recommended action",
  "safer_clause": "one complete safer contract clause",
  "negotiation_advice": "one practical negotiation advice"
}}

General rules:
- Do not provide multiple reasons, actions, negotiation options, or safer clause alternatives.
- Do not use bullet points inside any JSON value.
- Keep each field as a single paragraph string.
- Use retrieved similar clauses and legal references only as reference. Do not copy them blindly.
- If retrieved clauses have UNKNOWN risk_label, treat them only as context, not as authority.
- Prefer risk-labelled examples and official Bare Act references when available.

Rules for safer_clause:
- Generate exactly one final safer_clause.
- The safer_clause must be one complete formal contract clause ready to insert into the agreement.
- It should be legally strong, balanced, and preserve the original commercial purpose.
- Do not invent or increase monetary amounts, penalties, fees, or compensation.
- If the issue is employee penalty, bond penalty, or liquidated damages, do not invent new fixed amounts or slabs.
- For employee bond or penalty clauses, do not create new penalty slabs such as 50,000, 1 lakh, or 1.5 lakhs unless such amounts are already present in the original clause.
- Prefer wording that limits recovery to reasonable, documented, legally recoverable actual costs, with prior written notice and an opportunity to respond.
- If the issue is termination or service suspension, include prior written notice, a reasonable cure period where appropriate, and compliance with applicable law or professional obligations.
- If the issue is employment termination without notice, include thirty (30) days prior written notice, a reasonable opportunity to cure, exception only for proven gross misconduct, written reasons, and payment of accrued salary, benefits, and dues.
- If the issue is legal services withdrawal or file closure, include reasonable prior written notice, opportunity to cure non-payment where appropriate, protection of client interests, return/transfer of client papers, and compliance with professional conduct obligations.
- If the issue is broad lien or payment security, limit the lien to undisputed earned fees and reasonable costs, subject to applicable professional rules and a fair dispute process.
- If the issue is uncapped collection costs or service charge, require reasonable documented collection costs, a stated lawful interest/service charge cap, and prior written notice.
- If the issue is privilege or confidentiality waiver, require informed written consent, clear disclosure of consequences, and preservation of confidentiality except where joint representation rules require sharing.
- If the issue is unlimited liability, add a reasonable liability cap.
- If the issue is uncapped indemnity, make the indemnity mutual and subject to a reasonable cap.
- If the issue is unilateral amendment or unilateral rate change, require prior written notice and limit changes to prospective work or require mutual written consent where appropriate.
- If the issue is broad or ambiguous legal wording, rewrite the clause using clear objective standards.
- For confidentiality clauses, prefer a reasonable period such as three (3) years, except trade secrets which may remain protected for as long as legally valid.
- For post-employment non-compete clauses, limit restrictions by time, geography, and scope, and prefer non-solicitation/confidentiality protection instead of a blanket employment restriction.
"""

    return prompt


def get_default_safer_clause(
    risk_result: dict,
    clause: str = ""
) -> str:
    """
    Strong fallback safer clause based on issue and document context.
    """

    issue = str(
        risk_result.get("detected_issue", "")
    ).lower()

    category = str(
        risk_result.get("category", "")
    ).lower()

    context = infer_clause_context(
        clause,
        risk_result
    )

    combined = f"{issue} {category}"

    if (
        "penalty" in combined
        or "bond" in combined
        or "liquidated damages" in combined
    ):
        return (
            "The Employee shall not be required to pay any fixed penalty merely because employment ends before a specified period. "
            "Any recovery by the Employer shall be limited to reasonable, documented, and legally recoverable costs actually incurred "
            "for training or onboarding, if any, and only after providing the Employee with prior written notice, supporting details, "
            "and a reasonable opportunity to respond. No amount shall be recovered if the termination is caused by the Employer's breach, "
            "unlawful conduct, or circumstances beyond the Employee's reasonable control."
        )

    if context == "legal_services":
        if (
            "termination" in combined
            or "suspension" in combined
            or "withdraw" in combined
            or "file closure" in combined
        ):
            return (
                "Law Firm may suspend non-urgent work or withdraw from the engagement only after providing Client with reasonable prior written notice, "
                "a reasonable opportunity to cure any non-payment or remediable breach, and sufficient time to protect Client's interests, subject at all times "
                "to applicable professional conduct obligations. Upon withdrawal or file closure, Law Firm shall cooperate reasonably in transferring the matter "
                "and returning Client papers and property, while preserving any lawful rights to collect undisputed earned fees and reasonable costs."
            )

        if (
            "lien" in combined
            or "payment security" in combined
        ):
            return (
                "Any lien or payment security claimed by Law Firm shall be limited to undisputed earned fees and reasonable documented costs, shall apply only "
                "to the extent permitted by applicable professional conduct rules, and shall not prevent Client from disputing charges in good faith or obtaining "
                "Client papers and property required to protect Client's legal interests."
            )

        if (
            "collection" in combined
            or "service charge" in combined
            or "delinquent" in combined
        ):
            return (
                "Client shall be responsible only for reasonable and documented collection costs and any lawful service charge expressly stated in this Agreement, "
                "after Law Firm provides written notice of the overdue amount and a reasonable opportunity to cure. Any disputed amount shall be handled through "
                "a good-faith billing dispute process before collection costs or service charges are imposed."
            )

        if (
            "privilege" in combined
            or "confidentiality waiver" in combined
            or "confidential" in combined
        ):
            return (
                "In any joint representation, Law Firm shall explain in writing the confidentiality and privilege consequences of joint representation, and Client's "
                "consent shall be informed and written. Confidential information shall be protected except to the extent disclosure between jointly represented clients "
                "is necessary for the representation or required by applicable professional rules or law."
            )

        if (
            "rate change" in combined
            or "fee increase" in combined
            or "fees" in combined
        ):
            return (
                "Any change to hourly rates or charges shall apply only prospectively after reasonable prior written notice to Client. Client may decline the changed "
                "rates for future work, and Law Firm shall cooperate reasonably in transitioning the matter in accordance with applicable professional conduct obligations."
            )

    if context == "employment":
        if "termination" in combined or "notice" in combined:
            return (
                "The Employer may terminate the Employee's employment only by providing at least thirty (30) days prior written notice "
                "specifying the grounds for termination and allowing the Employee a reasonable opportunity to cure any remediable breach. "
                "Immediate termination shall be permitted only in cases of proven gross misconduct, fraud, or wilful breach, provided that "
                "written reasons are supplied to the Employee. The Employee shall remain entitled to all salary, benefits, and accrued dues "
                "up to the effective date of termination."
            )

    if "termination" in combined or "suspension" in combined or "notice" in combined:
        return (
            "Either party may terminate or suspend performance only after providing reasonable prior written notice specifying the grounds for such action "
            "and allowing a reasonable opportunity to cure any remediable breach, except where immediate action is required by law, fraud, wilful misconduct, "
            "or urgent risk of material harm."
        )

    if "lien" in combined or "payment security" in combined:
        return (
            "Any lien or payment security shall be limited to undisputed amounts that are lawfully due and reasonable documented costs, and shall remain subject "
            "to applicable law, a good-faith dispute process, and the rights of the other party to access property or documents necessary to protect its legal interests."
        )

    if "collection" in combined or "service charge" in combined or "delinquent" in combined:
        return (
            "The defaulting party shall be responsible only for reasonable documented collection costs and any lawful service charge expressly stated in this Agreement, "
            "after receiving written notice of the overdue amount and a reasonable opportunity to cure or dispute the amount in good faith."
        )

    if "privilege" in combined or "confidentiality waiver" in combined:
        return (
            "Confidential information and privileged communications shall remain protected except to the extent disclosure is required by applicable law, professional obligations, "
            "or informed written consent of the affected parties after clear disclosure of the consequences of such waiver."
        )

    if "liability" in combined:
        return (
            "Each party shall be liable only for direct losses caused by its proven breach, negligence, fraud, or wilful misconduct, "
            "and such liability shall be subject to a reasonable and mutually agreed cap, except where limitation is prohibited by applicable law."
        )

    if "indemn" in combined:
        return (
            "Each party shall indemnify the other only for direct losses arising from its own breach, negligence, fraud, or wilful misconduct, "
            "subject to a reasonable liability cap and applicable law."
        )

    if (
        "amend" in combined
        or "modify" in combined
        or "rate change" in combined
        or "fee increase" in combined
    ):
        return (
            "Any amendment, modification, fee increase, or material change to this Agreement shall apply only after reasonable prior written notice and, where it affects "
            "material rights or obligations, written agreement of both parties before taking effect."
        )

    if "confidential" in combined:
        return (
            "The receiving party shall protect confidential information with reasonable care and shall not disclose it except as required by law, "
            "for legitimate contractual purposes, or with prior written consent. This obligation shall continue for three (3) years after termination, "
            "except for trade secrets which shall remain protected for as long as legally valid."
        )

    return (
        "The parties shall act reasonably and in good faith, and any material action affecting rights, obligations, liability, termination, "
        "or payment shall require prior written notice, a reasonable opportunity to cure where applicable, and compliance with applicable law."
    )


def normalize_reasoning(
    result: dict,
    risk_result: dict,
    clause: str = ""
) -> dict:
    """
    Ensure all required keys exist and return one clean value for each field.
    Also prevents wrong employment-specific safer clauses for non-employment documents.
    """

    if not result:
        result = {}

    reason = result.get(
        "reason",
        f"The classifier identified this clause as {risk_result.get('risk_level')} risk because of {risk_result.get('detected_issue')}."
    )

    action = result.get(
        "action",
        "The signer should negotiate this clause before signing."
    )

    safer_clause = result.get(
        "safer_clause",
        get_default_safer_clause(
            risk_result,
            clause
        )
    )

    context = infer_clause_context(
        clause,
        risk_result
    )

    if safer_clause_context_mismatch(
        clause,
        safer_clause,
        context
    ):
        safer_clause = get_default_safer_clause(
            risk_result,
            clause
        )

    negotiation_advice = result.get(
        "negotiation_advice",
        "The signer should request clearer, fairer, and mutually balanced wording before signing."
    )

    return {
        "reason": clean_generated_text(reason),
        "action": clean_generated_text(action),
        "safer_clause": clean_generated_text(safer_clause),
        "negotiation_advice": clean_generated_text(negotiation_advice)
    }


def generate_reasoning(
    clause: str,
    risk_result: dict,
    similar_clauses=None
) -> dict:
    """
    Generate legal reasoning and safer clause.
    LLM does not classify risk.
    """

    prompt = build_reasoning_prompt(
        clause=clause,
        risk_result=risk_result,
        similar_clauses=similar_clauses
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional legal contract review assistant. You always return only valid JSON with one reason, one action, one negotiation_advice, and one safer_clause."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=650
        )

        raw = response.choices[0].message.content

        result = extract_json(
            raw
        )

        return normalize_reasoning(
            result,
            risk_result,
            clause
        )

    except Exception as e:
        print(
            "LLM reasoning failed:",
            str(e)[:150]
        )

        fallback = {
            "reason": f"The classifier identified this clause as {risk_result.get('risk_level')} risk because of {risk_result.get('detected_issue')}.",
            "action": "The signer should negotiate this clause before signing.",
            "safer_clause": get_default_safer_clause(
                risk_result,
                clause
            ),
            "negotiation_advice": "The signer should request clearer, fairer, and mutually balanced wording before signing."
        }

        return normalize_reasoning(
            fallback,
            risk_result,
            clause
        )