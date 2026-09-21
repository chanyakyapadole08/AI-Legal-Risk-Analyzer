from services.document_loader import extract_text_from_pdf
from services.document_cleaner import clean_legal_text
from services.clause_extractor import extract_clauses
from services.risk_classifier import classify_risk
from services.llm_reasoner import generate_reasoning
from services.negotiation_engine import suggest_negotiation
from services.missing_clause_detector import detect_missing_clauses
from services.risk_score import verdict
from services.config import settings
from services.semantic_risk_classifier import classify_semantic_risk_batch
from services.legal_risk_calibrator import calibrate_risk


SIMILARITY_THRESHOLD = 0.50
TOP_K = 3


def calculate_overall_score(results: list, missing_clauses: list) -> int:
    """
    Calculate overall document risk score using:
    - average clause risk,
    - high-risk concentration boost,
    - missing/unclear clause penalty.

    This keeps scoring professional:
    documents with multiple HIGH clauses should not remain MEDIUM RISK.
    """

    if not results:
        return 0

    total_score = 0

    high_count = 0
    medium_count = 0
    low_count = 0

    for result in results:
        score = result.get(
            "risk_score",
            20
        )

        total_score += score

        level = str(
            result.get(
                "risk_level",
                "LOW"
            )
        ).upper()

        if level == "HIGH":
            high_count += 1
        elif level == "MEDIUM":
            medium_count += 1
        else:
            low_count += 1

    total_clauses = len(results)

    average_score = total_score / total_clauses

    high_ratio = high_count / total_clauses

    high_risk_boost = 0

    if high_count >= 10:
        high_risk_boost += 10
    elif high_count >= 5:
        high_risk_boost += 8
    elif high_count >= 3:
        high_risk_boost += 5

    if high_ratio >= 0.30:
        high_risk_boost += 8
    elif high_ratio >= 0.15:
        high_risk_boost += 5

    critical_missing_keywords = [
        "termination",
        "dispute resolution",
        "governing law",
        "jurisdiction",
        "limitation of liability",
        "confidentiality",
        "data protection",
        "privacy"
    ]

    missing_penalty = 0

    for missing in missing_clauses:
        name = (
            missing.get("missing_clause")
            or missing.get("name")
            or missing.get("clause_name")
            or missing.get("title")
            or "Missing Clause"
        )

        name_lower = str(name).lower()

        if any(keyword in name_lower for keyword in critical_missing_keywords):
            missing_penalty += 4
        else:
            missing_penalty += 2

    missing_penalty = min(
        missing_penalty,
        15
    )

    final_score = round(
        average_score + high_risk_boost + missing_penalty
    )

    return min(
        final_score,
        100
    )

def get_similar_clauses_for_risk(
    clause_text: str,
    category: str = None
) -> list:
    """
    Retrieve similar clauses for risky clauses.

    Supports:
    - FAISS semantic RAG
    - BM25 lightweight RAG

    RAG output is mainly backend context for LLM reasoning.
    Frontend simple report does not display this field.
    """

    if not settings.ENABLE_RAG:
        return []

    # Lightweight BM25 RAG mode
    if settings.RAG_BACKEND.lower() == "bm25":
        from services.bm25_rag import search_similar_clauses_bm25

        return search_similar_clauses_bm25(
            clause_text,
            top_k=TOP_K,
            category=category
        )

    # FAISS semantic RAG mode
    from services.embedder import generate_embedding
    from services.vector_store import vector_store

    embedding = generate_embedding(
        clause_text
    )

    retrieved = vector_store.search(
        embedding,
        top_k=TOP_K * 4
    )

    filtered = []
    seen = set()

    for item in retrieved:
        score = item.get(
            "similarity_score",
            0
        )

        if score < SIMILARITY_THRESHOLD:
            continue

        clause = item.get(
            "clause_text",
            ""
        )

        key = " ".join(
            clause.lower().split()
        )

        if key in seen:
            continue

        seen.add(key)

        item_category = item.get(
            "clause_type",
            ""
        )

        item_risk = item.get(
            "risk_label",
            "UNKNOWN"
        )

        category_match = True

        if category and category.lower() not in [
            "general clause",
            "unknown",
            ""
        ]:
            category_match = category.lower() in item_category.lower()

        item["retrieval_backend"] = "faiss"
        item["category_match"] = category_match
        item["risk_label_available"] = item_risk != "UNKNOWN"

        filtered.append(item)

    # Ranking:
    # 1. same category
    # 2. labelled clauses before UNKNOWN
    # 3. higher similarity
    filtered.sort(
        key=lambda x: (
            x.get("category_match", False),
            x.get("risk_label_available", False),
            x.get("similarity_score", 0)
        ),
        reverse=True
    )

    return filtered[:TOP_K]


def low_risk_reasoning(clause_text: str) -> dict:
    """
    Local professional response for LOW risk clauses.
    Avoids unnecessary LLM calls.
    """

    return {
        "reason": "This clause appears to be standard and does not contain any major unfair risk pattern.",
        "action": "Review the commercial terms before signing.",
        "safer_clause": clause_text,
        "negotiation_advice": "No major negotiation is required unless the commercial terms are unfavorable."
    }


def medium_risk_reasoning(
    clause_text: str,
    risk_result: dict
) -> dict:
    """
    Local professional response for MEDIUM risk clauses during full PDF analysis.
    This keeps PDF analysis fast while still giving useful frontend output.
    """

    detected_issue = risk_result.get(
        "detected_issue",
        "potential legal ambiguity"
    )

    detected_issue = str(detected_issue).strip()

    return {
        "reason": f"This clause requires legal review because it may involve {detected_issue.lower()}.",
        "action": "Clarify the scope, conditions, timelines, and approval process before signing.",
        "safer_clause": clause_text,
        "negotiation_advice": "Ask for objective standards, prior written notice, and mutual consent where obligations may change."
    }


def analyze_clause_v2(clause: str) -> dict:
    """
    Analyze a single clause.

    For single-clause analysis:
    - LOW uses local response.
    - MEDIUM and HIGH use RAG + LLM reasoning.
    """

    risk_result = classify_risk(
        clause
    )

    risk_result = calibrate_risk(
        clause,
        risk_result
    )

    negotiation = suggest_negotiation(
        risk_result
    )

    if risk_result["risk_level"] == "LOW":
        reasoning = low_risk_reasoning(
            clause
        )

        similar_clauses = []

    else:
        similar_clauses = get_similar_clauses_for_risk(
            clause,
            category=risk_result.get("category")
        )

        reasoning = generate_reasoning(
            clause=clause,
            risk_result=risk_result,
            similar_clauses=similar_clauses
        )

    return {
        "original_clause": clause,
        "risk_level": risk_result["risk_level"],
        "risk_score": risk_result["risk_score"],
        "category": risk_result["category"],
        "detected_issue": risk_result["detected_issue"],
        "classifier": risk_result["classifier"],
        "confidence": risk_result.get("confidence"),
        "reason": reasoning["reason"],
        "action": reasoning["action"],
        "safer_clause": reasoning["safer_clause"],
        "negotiation_advice": reasoning.get(
            "negotiation_advice",
            negotiation
        ),
        "similar_clauses": similar_clauses
    }


def analyze_document_v2(pdf_path: str) -> dict:
    """
    Full PDF analysis pipeline.

    Final optimized PDF mode:
    - Full document clauses are analyzed.
    - Risk classification is done in LLM batches for efficiency.
    - Universal legal risk calibration improves consistency across document types.
    - LOW clauses use local response.
    - MEDIUM clauses use local concise response for speed.
    - HIGH clauses use FAISS RAG + LLM reasoning.
    """

    extracted = extract_text_from_pdf(
        pdf_path
    )

    if isinstance(extracted, dict):
        raw_text = extracted.get(
            "raw_text",
            ""
        )

        extraction_method = extracted.get(
            "extraction_method",
            "unknown"
        )

    else:
        raw_text = extracted
        extraction_method = "pymupdf_or_ocr"

    clean_text = clean_legal_text(
        raw_text
    )

    all_clauses = extract_clauses(
        clean_text
    )

    total_clauses_extracted = len(
        all_clauses
    )

    max_clauses = getattr(
        settings,
        "MAX_ANALYSIS_CLAUSES",
        0
    )

    # MAX_ANALYSIS_CLAUSES=0 means full document analysis.
    if max_clauses and max_clauses > 0:
        clauses = all_clauses[:max_clauses]
    else:
        clauses = all_clauses

    analysis_limited = len(clauses) < total_clauses_extracted

    clause_texts = [
        clause_obj["text"]
        for clause_obj in clauses
    ]

    # Batch semantic risk classification for all clauses.
    # This reduces many individual classification calls into fewer LLM batch calls.
    # After classification, a universal legal risk calibration layer is applied
    # to improve consistency across Employment, Legal Services, NDA, Lease,
    # Loan, Power of Attorney, Service Agreements, and other contract types.
    try:
        risk_results = classify_semantic_risk_batch(
            clause_texts,
            default_category="General Legal Clause",
            batch_size=10
        )

        if len(risk_results) != len(clause_texts):
            raise ValueError(
                "Batch classifier returned different number of results"
            )

        risk_results = [
            calibrate_risk(
                clause_texts[index],
                risk_results[index]
            )
            for index in range(
                len(risk_results)
            )
        ]

    except Exception as e:
        print(
            f"Batch classification failed, falling back to single-clause classifier: {e}"
        )

        risk_results = [
            calibrate_risk(
                clause_text,
                classify_risk(clause_text)
            )
            for clause_text in clause_texts
        ]

    results = []

    for index, clause_obj in enumerate(clauses):
        clause_text = clause_obj["text"]

        risk_result = risk_results[index]

        negotiation = suggest_negotiation(
            risk_result
        )

        if risk_result["risk_level"] == "LOW":
            reasoning = low_risk_reasoning(
                clause_text
            )

            similar_clauses = []

        elif risk_result["risk_level"] == "MEDIUM":
            reasoning = medium_risk_reasoning(
                clause_text,
                risk_result
            )

            similar_clauses = []

        else:
            # HIGH risk clauses get full RAG + LLM reasoning.
            similar_clauses = get_similar_clauses_for_risk(
                clause_text,
                category=risk_result.get("category")
            )

            reasoning = generate_reasoning(
                clause=clause_text,
                risk_result=risk_result,
                similar_clauses=similar_clauses
            )

        result = {
            "clause_id": clause_obj["clause_id"],
            "heading": clause_obj["heading"],
            "original_clause": clause_text,
            "risk_level": risk_result["risk_level"],
            "risk_score": risk_result["risk_score"],
            "category": risk_result["category"],
            "detected_issue": risk_result["detected_issue"],
            "classifier": risk_result["classifier"],
            "confidence": risk_result.get("confidence"),
            "reason": reasoning["reason"],
            "action": reasoning["action"],
            "safer_clause": reasoning["safer_clause"],
            "negotiation_advice": reasoning.get(
                "negotiation_advice",
                negotiation
            ),
            "similar_clauses": similar_clauses
        }

        results.append(
            result
        )

    missing_clauses = detect_missing_clauses(
        clean_text
    )

    overall_score = calculate_overall_score(
        results,
        missing_clauses
    )

    overall_verdict = verdict(
        overall_score
    )

    return {
        "version": "2.0",
        "architecture": "Hybrid classifier + batch semantic risk + universal calibration + FAISS RAG + LLM reasoning",
        "extraction_method": extraction_method,
        "total_clauses": len(clauses),
        "total_clauses_extracted": total_clauses_extracted,
        "analysis_limited": analysis_limited,
        "high_risk": sum(
            1 for r in results
            if r["risk_level"] == "HIGH"
        ),
        "medium_risk": sum(
            1 for r in results
            if r["risk_level"] == "MEDIUM"
        ),
        "low_risk": sum(
            1 for r in results
            if r["risk_level"] == "LOW"
        ),
        "overall_risk_score": overall_score,
        "overall_risk_level": overall_verdict,
        "clauses": results,
        "missing_clauses": missing_clauses
    }