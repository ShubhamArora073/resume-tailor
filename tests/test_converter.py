import os
import shutil
import tempfile
import pytest

from converter import pdf_to_docx, docx_to_pdf

HAS_LIBREOFFICE = shutil.which("libreoffice") is not None or shutil.which("soffice") is not None

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_PDF = os.path.join(FIXTURES_DIR, "sample.pdf")


def test_pdf_to_docx_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        result = pdf_to_docx(SAMPLE_PDF, tmp)
        assert result.endswith(".docx")
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0


def test_pdf_to_docx_raises_on_missing_file():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(FileNotFoundError):
            pdf_to_docx("/nonexistent/file.pdf", tmp)


@pytest.mark.skipif(not HAS_LIBREOFFICE, reason="LibreOffice not installed")
def test_docx_to_pdf_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        docx_path = pdf_to_docx(SAMPLE_PDF, tmp)
        result = docx_to_pdf(docx_path, tmp)
        assert result.endswith(".pdf")
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0
