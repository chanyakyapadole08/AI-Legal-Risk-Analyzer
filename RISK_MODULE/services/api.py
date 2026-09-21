from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil
import os

from services.analyzer_v2 import analyze_document_v2, analyze_clause_v2
from services.json_report_writer import save_json_report
from services.simple_report_generator import (
    build_simple_report,
    simplify_clause_result
)
from services.config import settings


app = FastAPI(
    title="AI Legal Risk Analyzer V2",
    description="Hybrid legal document risk analyzer using classifier, semantic risk, FAISS RAG and configurable LLM",
    version="2.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClauseInput(BaseModel):
    clause: str


@app.get("/")
def home():
    return {
        "message": "AI Legal Risk Analyzer V2 Running",
        "architecture": {
            "risk_classification": "Hybrid rule-based + semantic classifier",
            "retrieval": "FAISS RAG",
            "llm_role": "Reasoning and safer clause generation only",
            "summary_module": "Not integrated in risk module",
            "translation_module": "Not integrated yet",
            "frontend_output": "Professional dashboard report",
            "full_report": "Saved in reports folder"
        },
        "endpoints": {
            "clause": "POST /analyze/clause",
            "clause_alias": "POST /agent/clause",
            "pdf": "POST /analyze/pdf",
            "pdf_alias": "POST /agent/pdf",
            "download_report": "GET /reports/{file_name}",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }


@app.post("/analyze/clause")
def analyze_clause_endpoint(data: ClauseInput):
    if not data.clause.strip():
        raise HTTPException(
            status_code=400,
            detail="Clause cannot be empty"
        )

    full_result = analyze_clause_v2(
        data.clause
    )

    simple_result = simplify_clause_result(
        full_result
    )

    if settings.RETURN_FULL_REPORT:
        return {
            "status": "success",
            "result": simple_result,
            "full_result": full_result
        }

    return {
        "status": "success",
        "result": simple_result
    }


@app.post("/agent/clause")
def analyze_clause_agent_alias(data: ClauseInput):
    return analyze_clause_endpoint(data)


@app.post("/analyze/pdf")
async def analyze_pdf_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    os.makedirs(
        "temp",
        exist_ok=True
    )

    safe_filename = os.path.basename(
        file.filename
    )

    file_path = os.path.join(
        "temp",
        safe_filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    try:
        full_report = analyze_document_v2(
            file_path
        )

        report_path = save_json_report(
            full_report
        )

        full_report["report_path"] = report_path

        simple_report = build_simple_report(
            full_report
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document analysis failed: {str(e)}"
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    response = {
        "status": "success",
        "message": "Document analyzed successfully",
        "report": simple_report,
        "report_path": report_path
    }

    if settings.RETURN_FULL_REPORT:
        response["full_report"] = full_report

    return response


@app.post("/agent/pdf")
async def analyze_pdf_agent_alias(file: UploadFile = File(...)):
    return await analyze_pdf_endpoint(file)


@app.get("/reports/{file_name}")
def download_report(file_name: str):
    safe_name = os.path.basename(
        file_name
    )

    file_path = os.path.join(
        "reports",
        safe_name
    )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    return FileResponse(
        file_path,
        media_type="application/json",
        filename=safe_name
    )


@app.post("/translate")
def translate_placeholder():
    return {
        "status": "not_available",
        "message": "Translation module is not integrated yet."
    }


@app.post("/summary")
def summary_placeholder():
    return {
        "status": "not_available",
        "message": "Summary module is not integrated in this risk module."
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.0",
        "llm_model": settings.LLM_MODEL_NAME,
        "semantic_risk": settings.ENABLE_SEMANTIC_RISK,
        "rag_enabled": settings.ENABLE_RAG,
        "rag_backend": settings.RAG_BACKEND,
        "max_analysis_clauses": settings.MAX_ANALYSIS_CLAUSES
    }