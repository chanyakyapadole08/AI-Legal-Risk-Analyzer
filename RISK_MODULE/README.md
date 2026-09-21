# AI Legal Document Risk Analyzer V2

## Project Overview

AI Legal Document Risk Analyzer V2 is a backend system that analyzes legal PDF documents and identifies risky clauses. It extracts text from legal documents, cleans the text, splits the document into clauses, classifies each clause into HIGH, MEDIUM, or LOW risk, detects missing important clauses, generates negotiation suggestions, and produces a structured JSON report for frontend dashboard display.

The system is designed for legal-tech use cases such as employment agreements, power of attorney documents, service agreements, legal service agreements, NDAs, property documents, and commercial contracts.

---

## Main Features

- PDF upload and analysis
- OCR support for scanned PDFs
- Document text cleaning
- Clause extraction
- Semantic-first legal risk classification
- FAISS-based RAG retrieval
- Groq LLM based legal reasoning
- Safer clause generation
- Missing clause detection
- Negotiation assistant
- Frontend-ready dashboard response
- Full JSON report saving
- Report download endpoint
- Configurable through `.env`

---

## Current Backend Capabilities

The backend can:

1. Accept a PDF document.
2. Extract readable text from digital or scanned PDFs.
3. Clean noisy document text.
4. Extract legal clauses.
5. Classify each clause into HIGH, MEDIUM, or LOW risk.
6. Detect important missing clauses.
7. Generate legal reasoning and safer clause suggestions.
8. Provide negotiation points.
9. Return a frontend-friendly dashboard report.
10. Save full JSON reports in the `reports` folder.

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI |
| Server | Uvicorn |
| PDF Processing | PyMuPDF |
| OCR | Tesseract OCR, Pytesseract |
| Image Processing | Pillow |
| LLM Provider | Groq |
| LLM Client | OpenAI-compatible SDK |
| Risk Classification | Semantic LLM classifier |
| RAG | FAISS |
| Embeddings | Sentence Transformers, BGE |
| Report Format | JSON |
| Configuration | python-dotenv |

---

## Dataset Used

The system currently uses a unified legal clause dataset.

### Dataset Sources

1. Custom IndianContracts dataset
2. CUAD subset extracted from public contract PDFs

### Dataset Location

```text
datasets/unified/unified_legal_clauses.json