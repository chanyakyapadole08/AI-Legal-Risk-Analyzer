import os
from pathlib import Path


try:
    from dotenv import load_dotenv

    BASE_DIR = Path(__file__).resolve().parent.parent
    ENV_PATH = BASE_DIR / ".env"

    load_dotenv(
        dotenv_path=ENV_PATH,
        override=True
    )

except Exception:
    pass


class Settings:
    """
    Central configuration for the AI Legal Document Analysis System.

    Supports:
    - Groq cloud LLM
    - Local LM Studio if needed
    - FAISS semantic RAG
    - Fast demo mode
    - Full research mode
    """

    LLM_BASE_URL = os.getenv(
        "LLM_BASE_URL",
        "https://api.groq.com/openai/v1"
    )

    LLM_API_KEY = os.getenv(
        "LLM_API_KEY",
        os.getenv("GROQ_API_KEY", "lm-studio")
    )

    LLM_MODEL_NAME = os.getenv(
        "LLM_MODEL_NAME",
        "llama-3.1-8b-instant"
    )

    LLM_TIMEOUT = float(
        os.getenv(
            "LLM_TIMEOUT",
            "30"
        )
    )

    ENABLE_SEMANTIC_RISK = os.getenv(
        "ENABLE_SEMANTIC_RISK",
        "false"
    ).lower() == "true"

    SEMANTIC_RISK_MODE = os.getenv(
        "SEMANTIC_RISK_MODE",
        "fast"
    )

    ENABLE_RAG = os.getenv(
        "ENABLE_RAG",
        "true"
    ).lower() == "true"

    RAG_BACKEND = os.getenv(
        "RAG_BACKEND",
        "faiss"
    )

    MAX_ANALYSIS_CLAUSES = int(
        os.getenv(
            "MAX_ANALYSIS_CLAUSES",
            "30"
        )
    )

    RETURN_FULL_REPORT = os.getenv(
        "RETURN_FULL_REPORT",
        "false"
    ).lower() == "true"


settings = Settings()