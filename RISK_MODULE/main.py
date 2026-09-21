"""
AI Legal Risk Analyzer V2

Run FastAPI backend with:

python -m uvicorn services.api:app --reload

Swagger UI:
http://127.0.0.1:8000/docs
"""


def main():
    print("AI Legal Risk Analyzer V2")
    print("-" * 40)
    print("Run the backend using:")
    print("python -m uvicorn services.api:app --reload")
    print()
    print("Open Swagger UI:")
    print("http://127.0.0.1:8000/docs")
    print()
    print("Important endpoints:")
    print("GET  /health")
    print("POST /agent/clause")
    print("POST /agent/pdf")
    print("GET  /reports/{file_name}")


if __name__ == "__main__":
    main()