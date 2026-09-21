import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

from services.document_loader import load_pdf


text = load_pdf("sample.pdf")

print(text[:1000])