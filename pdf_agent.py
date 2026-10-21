from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(uploaded_file):
    """
    Extract readable text from an uploaded PDF.
    Supports Streamlit UploadedFile objects and PDF bytes.
    """

    if hasattr(uploaded_file, "getvalue"):
        pdf_bytes = uploaded_file.getvalue()
    elif isinstance(uploaded_file, bytes):
        pdf_bytes = uploaded_file
    else:
        raise TypeError(
            "Expected a Streamlit uploaded file or PDF bytes."
        )

    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")

    extracted_text = ""

    # First try PyMuPDF.
    try:
        import fitz

        with fitz.open(
            stream=pdf_bytes,
            filetype="pdf",
        ) as document:
            extracted_text = "\n\n".join(
                page.get_text("text", sort=True) or ""
                for page in document
            )
    except Exception:
        extracted_text = ""

    # Fall back to pypdf.
    if not extracted_text.strip():
        try:
            reader = PdfReader(BytesIO(pdf_bytes))

            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception as exc:
                    raise ValueError(
                        "This PDF is password-protected."
                    ) from exc

            extracted_text = "\n\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(
                f"Could not read the PDF: {exc}"
            ) from exc

    extracted_text = extracted_text.strip()

    if not extracted_text:
        raise ValueError(
            "No readable text found. "
            "This may be a scanned PDF requiring OCR."
        )

    return extracted_text
