import json
import os
import pytest
from unittest.mock import patch, MagicMock

from rewriter import rewrite_resume, build_prompt, parse_response, RewriteResult


def test_build_prompt_includes_jd_and_resume():
    resume_text = "Software Engineer with 5 years experience\nBuilt CI/CD pipelines"
    jd = "Looking for a DevOps engineer with Kubernetes experience"

    prompt = build_prompt(resume_text, jd)

    assert "Software Engineer with 5 years experience" in prompt
    assert "Looking for a DevOps engineer" in prompt
    assert "Kubernetes" in prompt


def test_parse_response_valid_json():
    raw = json.dumps({
        "name": "John Doe",
        "title": "DevOps Engineer",
        "contact": {"email": "j@d.com", "phone": "123", "location": "NY"},
        "summary": "Experienced engineer.",
        "experience": [],
        "skills": ["Python"],
        "education": [],
        "certifications": [],
        "achievements": [],
        "keywords_added": ["Kubernetes", "Docker"],
        "match_score": 82,
    })

    result = parse_response(raw)

    assert isinstance(result, RewriteResult)
    assert result.resume_data["name"] == "John Doe"
    assert result.keywords_added == ["Kubernetes", "Docker"]
    assert result.match_score == 82
    assert "keywords_added" not in result.resume_data
    assert "match_score" not in result.resume_data


def test_parse_response_invalid_json_raises():
    with pytest.raises(ValueError, match="Failed to parse"):
        parse_response("not json at all")


def test_model_and_timeout_defaults():
    from rewriter import MODEL, TIMEOUT
    assert MODEL == os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    assert isinstance(TIMEOUT, int)
    assert TIMEOUT > 0


@patch.dict(os.environ, {"AI_GATEWAY_KEY": "fake-key", "AI_GATEWAY_USER": "test@test.com"})
@patch("rewriter.anthropic")
def test_rewrite_resume_calls_claude_and_returns_result(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps({
        "name": "John Doe",
        "title": "DevOps Engineer",
        "contact": {"email": "j@d.com", "phone": "123", "location": "NY"},
        "summary": "Tailored summary.",
        "experience": [],
        "skills": ["Python"],
        "education": [],
        "certifications": [],
        "achievements": [],
        "keywords_added": ["Python"],
        "match_score": 90,
    })
    mock_client.messages.create.return_value = mock_response

    result = rewrite_resume("Original resume text", "Python developer needed")

    assert result.resume_data["summary"] == "Tailored summary."
    assert result.match_score == 90
    mock_client.messages.create.assert_called_once()
