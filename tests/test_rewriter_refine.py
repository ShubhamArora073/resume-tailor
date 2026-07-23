import json
import os
import pytest
from unittest.mock import patch, MagicMock

from rewriter import refine_resume, parse_response, RewriteResult


@patch.dict(os.environ, {"AI_GATEWAY_KEY": "fake-key", "AI_GATEWAY_USER": "test@test.com"})
@patch("rewriter.anthropic")
def test_refine_resume_happy_path(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    refined_data = {
        "name": "John Doe",
        "title": "Senior DevOps Engineer",
        "contact": {"email": "j@d.com", "phone": "123", "location": "NY"},
        "summary": "Experienced engineer with Kubernetes and Terraform expertise.",
        "experience": [],
        "skills": ["Python", "Kubernetes", "Terraform"],
        "education": [],
        "certifications": [],
        "achievements": [],
    }

    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps(refined_data)
    mock_client.messages.create.return_value = mock_response

    current_data = {
        "name": "John Doe",
        "title": "DevOps Engineer",
        "contact": {"email": "j@d.com", "phone": "123", "location": "NY"},
        "summary": "Experienced engineer.",
        "experience": [],
        "skills": ["Python"],
        "education": [],
        "certifications": [],
        "achievements": [],
    }

    result = refine_resume(current_data, ["Kubernetes", "Terraform"])

    assert result["name"] == "John Doe"
    assert "Kubernetes" in result["skills"]
    assert "Terraform" in result["skills"]
    mock_client.messages.create.assert_called_once()


@patch.dict(os.environ, {"AI_GATEWAY_KEY": "fake-key", "AI_GATEWAY_USER": "test@test.com"})
@patch("rewriter.anthropic")
def test_refine_resume_strips_markdown_code_fences(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    refined_data = {
        "name": "Jane Smith",
        "title": "Platform Engineer",
        "contact": {"email": "jane@x.com", "phone": "456", "location": "SF"},
        "summary": "Platform engineer with CI/CD expertise.",
        "experience": [],
        "skills": ["Docker", "CI/CD"],
        "education": [],
        "certifications": [],
        "achievements": [],
    }

    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "```json\n" + json.dumps(refined_data) + "\n```"
    mock_client.messages.create.return_value = mock_response

    current_data = {
        "name": "Jane Smith",
        "title": "Platform Engineer",
        "contact": {"email": "jane@x.com", "phone": "456", "location": "SF"},
        "summary": "Platform engineer.",
        "experience": [],
        "skills": ["Docker"],
        "education": [],
        "certifications": [],
        "achievements": [],
    }

    result = refine_resume(current_data, ["CI/CD"])

    assert result["name"] == "Jane Smith"
    assert "CI/CD" in result["skills"]


@patch.dict(os.environ, {"AI_GATEWAY_KEY": "fake-key", "AI_GATEWAY_USER": "test@test.com"})
@patch("rewriter.anthropic")
def test_refine_resume_invalid_json_raises(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "This is not valid JSON at all"
    mock_client.messages.create.return_value = mock_response

    current_data = {"name": "Test", "skills": ["Go"]}

    with pytest.raises(json.JSONDecodeError):
        refine_resume(current_data, ["Kubernetes"])


def test_parse_response_handles_json_code_fence():
    data = {
        "name": "Alex Dev",
        "title": "SRE",
        "contact": {"email": "a@b.com", "phone": "789", "location": "London"},
        "summary": "Site reliability engineer.",
        "experience": [],
        "skills": ["Prometheus", "Grafana"],
        "education": [],
        "certifications": [],
        "achievements": [],
        "keywords_added": ["Prometheus", "Grafana"],
        "match_score": 78,
    }

    raw = "```json\n" + json.dumps(data) + "\n```"

    result = parse_response(raw)

    assert isinstance(result, RewriteResult)
    assert result.resume_data["name"] == "Alex Dev"
    assert result.keywords_added == ["Prometheus", "Grafana"]
    assert result.match_score == 78
    assert "keywords_added" not in result.resume_data
    assert "match_score" not in result.resume_data
