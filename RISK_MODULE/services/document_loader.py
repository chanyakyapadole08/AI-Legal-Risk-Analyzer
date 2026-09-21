import fitz
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
import io
import os


TESSERACT_DEFAULT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


if os.path.exists(TESSERACT_DEFAULT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_DEFAULT_PATH


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF.

    If a page has selectable digital text, PyMuPDF extracts it directly.
    If a page has little or no text, OCR is applied using Tesseract.
    """

    pages = []

    doc = fitz.open(
        pdf_path
    )

    try:
        for page_no, page in enumerate(
            doc,
            start=1
        ):
            text = page.get_text(
                "text"
            ).strip()

            # Digital text page
            if len(text) > 100:
                pages.append(text)
                continue

            # OCR fallback for scanned/image pages
            print(
                f"OCR page {page_no}..."
            )

            pix = page.get_pixmap(
                dpi=300,
                alpha=False
            )

            img = Image.open(
                io.BytesIO(
                    pix.tobytes("png")
                )
            )

            img = img.convert(
                "L"
            )

            img = ImageEnhance.Contrast(
                img
            ).enhance(2.0)

            img = img.filter(
                ImageFilter.SHARPEN
            )

            ocr_text = pytesseract.image_to_string(
                img,
                lang="eng",
                config="--oem 3 --psm 6"
            )

            pages.append(
                ocr_text
            )

    finally:
        doc.close()

    return "\n\n".join(
        pages
    )