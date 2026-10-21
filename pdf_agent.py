from io import BytesIO
import re
import unicodedata

from pypdf import PdfReader


def clean_pdf_text(text):
    # Remove invisible control characters.
    text = "".join(
        ch for ch in text
        if ch in "\n\t"
        or unicodedata.category(ch)[0] != "C"
    )

    # Preserve paragraph boundaries.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_pdf_text(uploaded_file):
    pdf_bytes = uploaded_file.getvalue()
    candidates = []

    # Try pypdf first.
    try:
        reader = PdfReader(BytesIO(pdf_bytes))

        if reader.is_encrypted:
            raise ValueError(
                "This PDF is password-protected."
            )

        text = "\n\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

        candidates.append(("pypdf", clean_pdf_text(text)))

    except ValueError:
        raise
    except Exception:
        pass

    # Try PyMuPDF as an alternative.
    try:
        import fitz

        with fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        ) as document:
            text = "\n\n".join(
                page.get_text("text", sort=True)
                for page in document
            )

        candidates.append(("PyMuPDF", clean_pdf_text(text)))

    except Exception:
        pass

    if not candidates:
        raise ValueError(
            "Could not read this PDF with either extractor."
        )

    # Prefer readable-looking text, then the longer result.
    def quality(text):
        visible = [ch for ch in text if not ch.isspace()]
        if not visible:
            return 0

        readable = sum(
            ch.isalnum()
            or unicodedata.category(ch)[0] in ("P", "S")
            for ch in visible
        )

        return readable / len(visible)

    candidates.sort(
        key=lambda item: (quality(item[1]), len(item[1])),
        reverse=True,
    )

    method, best_text = candidates[0]

    if len(best_text) < 50:
        raise ValueError(
            "Too little text was extracted. "
            "Check whether the PDF contains selectable text."
        )

    if quality(best_text) < 0.80:
        raise ValueError(
            "The extracted text looks corrupted. "
            "Try exporting the original document as a new PDF."
        )

    return best_text
