from services.document_loader import extract_text_from_pdf
from services.clause_splitter import get_clauses
from services.llm_engine import analyze_clause
from services.risk_score import calculate_score, verdict
from RISK_MODULE.services.simple_report_generator import generate_report
from services.missing_clause_detector import detect_missing_clauses


class LegalRiskAgent:

    def __init__(self):
        pass

    def receive_request(self, pdf_path=None, clause=None):
        if pdf_path:
            return self.process_pdf(pdf_path)
        if clause:
            return self.process_clause(clause)
        return {"error": "No input provided."}

    def process_clause(self, clause):
        return analyze_clause(clause)

    def process_pdf(self, pdf_path):
        text = extract_text_from_pdf(pdf_path)
        clauses = get_clauses(text)

        results = []
        for i, clause in enumerate(clauses, 1):
            print(f"[{i}/{len(clauses)}] Analyzing...", end="\r")
            result = analyze_clause(clause)
            result["original_clause"] = clause
            results.append(result)

        # Missing clauses detect karo
        missing = detect_missing_clauses(text)

        score = calculate_score(results)
        risk = verdict(score)
        report = generate_report(results, score, risk)

        return {
            "total_clauses":   len(clauses),
            "high_risk":       sum(1 for r in results if r["risk_level"] == "HIGH"),
            "medium_risk":     sum(1 for r in results if r["risk_level"] == "MEDIUM"),
            "low_risk":        sum(1 for r in results if r["risk_level"] == "LOW"),
            "missing_clauses": missing,
            "score":           score,
            "verdict":         risk,
            "report":          report,
            "results":         results
        }