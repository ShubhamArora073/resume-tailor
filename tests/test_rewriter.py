import json
import pytest
from unittest.mock import patch, MagicMock

from rewriter import rewrite_resume, build_prompt, parse_response, RewriteResult


def test_build_prompt_includes_jd_and_resume():
    paragraphs = [
        {"index": 0, "text": "Software Engineer with 5 years experience", "heading_level": None},
        {"index": 1, "text": "Built CI/CD pipelines", "heading_level": None},
    ]
    jd = "Looking for a DevOps engineer with Kubernetes experience"

    prompt = build_prompt(paragraphs, jd)

    assert "Software Engineer with 5 years experience" in prompt
    assert "Looking for a DevOps engineer" in prompt
    assert "Kubernetes" in prompt


def test_parse_response_valid_json():
    raw = json.dumps({
        "sections": [
            {
                "heading": "Experience",
                "paragraphs": [
                    {"index": 0, "original": "old", "rewritten": "new"},
                    {"index": 1, "original": "old2", "rewritten": "new2"},
                ]
            }
        ],
        "keywords_added": ["Kubernetes", "Docker"],
        "match_score": 82
    })

    result = parse_response(raw)

    assert isinstance(result, RewriteResult)
    assert len(result.rewrites) == 2
    assert result.rewrites[0] == {"index": 0, "rewritten": "new"}
    assert result.keywords_added == ["Kubernetes", "Docker"]
    assert result.match_score == 82


def test_parse_response_invalid_json_raises():
    with pytest.raises(ValueError, match="Failed to parse"):
        parse_response("not json at all")


@patch("rewriter.anthropic")
def test_rewrite_resume_calls_claude_and_returns_result(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps({
        "sections": [
            {
                "heading": "Summary",
                "paragraphs": [
                    {"index": 0, "original": "old", "rewritten": "Tailored summary"}
                ]
            }
        ],
        "keywords_added": ["Python"],
        "match_score": 90
    })
    mock_client.messages.create.return_value = mock_response

    paragraphs = [{"index": 0, "text": "Original summary", "heading_level": None}]
    jd = "Python developer needed"

    result = rewrite_resume(paragraphs, jd)

    assert result.rewrites[0]["rewritten"] == "Tailored summary"
    assert result.match_score == 90
    mock_client.messages.create.assert_called_once()
