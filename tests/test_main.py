import os
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from dataclasses import dataclass

from main import app, extract_jd_keywords, compute_match_score


@dataclass
class MockRewriteResult:
    resume_data: dict
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
@patch("main.generate_pdf")
@patch("main.rewrite_resume")
@patch("main.extract_text_from_pdf")
async def test_tailor_endpoint_success(mock_extract, mock_rewrite, mock_genpdf):
    mock_extract.return_value = "John Doe\nSoftware Engineer with AWS and Kubernetes"
    mock_rewrite.return_value = MockRewriteResult(
        resume_data={
            "name": "John Doe",
            "title": "DevOps Engineer",
            "contact": {"email": "j@d.com", "phone": "123", "location": "NY"},
            "summary": "Experienced DevOps engineer.",
            "experience": [],
            "skills": ["AWS", "Kubernetes"],
            "education": [],
            "certifications": [],
            "achievements": [],
        },
        keywords_added=["Kubernetes"],
        match_score=85,
    )

    def fake_gen(data, output_path, photo_path=None):
        with open(output_path, "wb") as f:
            f.write(b"%PDF-1.4 fake pdf content here")
        return output_path

    mock_genpdf.side_effect = fake_gen

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tailor",
            files={"file": ("resume.pdf", b"%PDF-fake", "application/pdf")},
            data={"job_description": "Looking for DevOps engineer with AWS and Kubernetes experience " * 3},
        )

    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert "match_score" in data
    assert "keywords_found" in data
    assert "keywords_missing" in data
    assert "resume_data" in data
    assert data["claude_score"] == 85


@pytest.mark.asyncio
async def test_root_redirects():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        response = await client.get("/")
    assert response.status_code == 307


def test_extract_jd_keywords():
    jd = "We need someone with AWS, Kubernetes, Docker, and CI/CD experience. Site reliability engineering is key."
    keywords = extract_jd_keywords(jd)
    kw_lower = [k.lower() for k in keywords]
    assert "aws" in kw_lower
    assert "kubernetes" in kw_lower
    assert "docker" in kw_lower


def test_compute_match_score():
    resume = "Experienced in AWS and Kubernetes. Built CI/CD pipelines using Docker."
    keywords = ["AWS", "Kubernetes", "Docker", "Terraform", "Ansible"]
    result = compute_match_score(resume, keywords)
    assert result["score"] == 60
    assert len(result["found"]) == 3
    assert len(result["missing"]) == 2


@pytest.mark.asyncio
async def test_download_returns_pdf():
    request_id = "12345678-1234-1234-1234-123456789abc"
    work_dir = os.path.join("/tmp/resume-tailor", request_id)
    os.makedirs(work_dir, exist_ok=True)
    pdf_path = os.path.join(work_dir, "tailored_resume.pdf")

    try:
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 test content")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/download/{request_id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert b"%PDF-1.4" in response.content
    finally:
        if os.path.exists(work_dir):
            import shutil
            shutil.rmtree(work_dir)


@pytest.mark.asyncio
async def test_download_not_found():
    request_id = "87654321-4321-4321-4321-cba987654321"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/download/{request_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
@patch("main.generate_pdf")
async def test_regenerate_creates_pdf(mock_genpdf):
    request_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    work_dir = os.path.join("/tmp/resume-tailor", request_id)
    os.makedirs(work_dir, exist_ok=True)

    try:
        def fake_gen(data, output_path, photo_path=None):
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.4 regenerated")
            return output_path

        mock_genpdf.side_effect = fake_gen

        resume_data = {
            "name": "Jane Doe",
            "title": "Engineer",
            "contact": {"email": "jane@example.com", "phone": "555", "location": "SF"},
            "summary": "Experienced engineer.",
            "experience": [],
            "skills": ["Python"],
            "education": [],
            "certifications": [],
            "achievements": [],
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/regenerate/{request_id}", json=resume_data)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_genpdf.assert_called_once()
    finally:
        if os.path.exists(work_dir):
            import shutil
            shutil.rmtree(work_dir)


@pytest.mark.asyncio
async def test_regenerate_session_expired():
    request_id = "11111111-2222-3333-4444-555555555555"

    resume_data = {
        "name": "Test User",
        "title": "Developer",
        "contact": {"email": "test@example.com", "phone": "000", "location": "NYC"},
        "summary": "Test summary.",
        "experience": [],
        "skills": [],
        "education": [],
        "certifications": [],
        "achievements": [],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/regenerate/{request_id}", json=resume_data)

    assert response.status_code == 404
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
