import os
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from dataclasses import dataclass

from main import app

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_PDF = os.path.join(FIXTURES_DIR, "sample.pdf")


@dataclass
class MockRewriteResult:
    rewrites: list
    keywords_added: list
    match_score: int


@pytest.mark.asyncio
async def test_tailor_endpoint_rejects_non_pdf():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tailor",
            files={"file": ("resume.txt", b"not a pdf", "text/plain")},
            data={"job_description": "x" * 60},
        )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tailor_endpoint_rejects_short_jd():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tailor",
            files={"file": ("resume.pdf", b"%PDF-fake", "application/pdf")},
            data={"job_description": "too short"},
        )
    assert response.status_code == 400
    assert "50 characters" in response.json()["detail"]


@pytest.mark.asyncio
@patch("main.rewrite_resume")
@patch("main.docx_to_pdf")
@patch("main.apply_rewrites")
@patch("main.extract_paragraphs")
@patch("main.pdf_to_docx")
async def test_tailor_endpoint_success(
    mock_pdf_to_docx,
    mock_extract,
    mock_apply,
    mock_docx_to_pdf,
    mock_rewrite,
    tmp_path,
):
    fake_docx = str(tmp_path / "fake.docx")
    fake_output = str(tmp_path / "output.docx")
    fake_pdf = str(tmp_path / "output.pdf")

    open(fake_docx, "w").close()
    open(fake_output, "w").close()
    with open(fake_pdf, "wb") as f:
        f.write(b"%PDF-1.4 fake pdf content")

    mock_pdf_to_docx.return_value = fake_docx
    mock_extract.return_value = [{"index": 0, "text": "hello", "heading_level": None}]
    mock_rewrite.return_value = MockRewriteResult(
        rewrites=[{"index": 0, "rewritten": "tailored hello"}],
        keywords_added=["Python"],
        match_score=85,
    )
    mock_apply.return_value = fake_output
    mock_docx_to_pdf.return_value = fake_pdf

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tailor",
            files={"file": ("resume.pdf", b"%PDF-fake", "application/pdf")},
            data={"job_description": "x" * 60},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-match-score"] == "85"


@pytest.mark.asyncio
async def test_root_redirects_to_static():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        response = await client.get("/")
    assert response.status_code == 307  # RedirectResponse default
    assert response.headers["location"] == "/static/index.html"
