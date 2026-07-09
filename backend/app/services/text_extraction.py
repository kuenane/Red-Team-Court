"""Extracts plain text from uploaded pdf/docx/txt files."""
import io
from pypdf import PdfReader
from docx import Document as DocxDocument


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    # fallback: treat as plain text
    return content.decode("utf-8", errors="ignore")
