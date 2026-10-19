from io import BytesIO
from pypdf import PdfReader
import re


def extract_pdf_text(uploaded_file):
    reader = PdfReader(BytesIO(uploaded_file.getvalue()))

    pages = [
        page.extract_text() or ""
        for page in reader.pages
    ]

    return "\n".join(pages).strip()


def make_pdf_questions(text, count=5):
    sentences = re.split(r"(?<=[.!?])\s+", text)

    sentences = [
        s.strip()
        for s in sentences
        if len(s.strip().split()) >= 5
    ]

    sentences = list(dict.fromkeys(sentences))

    return [
        {
            "Question": "Explain this statement in your own words:",
            "Study note": sentence
        }
        for sentence in sentences[:count]
    ]
