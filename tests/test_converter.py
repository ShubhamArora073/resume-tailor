import os
import tempfile
import pytest

from converter import extract_text_from_pdf

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_PDF = os.path.join(FIXTURES_DIR, "sample.pdf")


def test_extract_text_from_pdf_returns_content():
    text = extract_text_from_pdf(SAMPLE_PDF)
    assert len(text) > 0
    assert "John Doe" in text


def test_extract_text_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("/nonexistent/file.pdf")
