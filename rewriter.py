import json
import os
from dataclasses import dataclass

import anthropic


@dataclass
class RewriteResult:
    rewrites: list[dict]
    keywords_added: list[str]
    match_score: int


SYSTEM_PROMPT = """You are an expert resume writer and ATS optimization specialist.
Your job is to rewrite resume content to align with a given job description.

Rules:
- Only reword and re-emphasize existing experience. NEVER fabricate skills, roles, or achievements.
- Naturally incorporate keywords from the job description into bullet points.
- Use standard ATS-parseable section headings (Summary, Experience, Skills, Education, Certifications).
- Mirror exact keyword phrases from the JD (e.g., "CI/CD pipelines" not "continuous integration").
- Spell out acronyms at least once if the JD does.
- Maintain professional tone consistent with the original resume's voice.
- Include measurable achievements where they already exist (numbers, percentages, scale).
- Keep content concise — aim for 1-2 pages maximum.

Return ONLY valid JSON in the exact format specified. No markdown, no explanation."""


def build_prompt(paragraphs: list[dict], job_description: str) -> str:
    resume_text = "\n".join(
        f"[{p['index']}] {p['text']}" for p in paragraphs
    )

    return f"""## Job Description

{job_description}

## Current Resume Content (indexed by paragraph)

{resume_text}

## Instructions

Rewrite the resume paragraphs to better align with the job description above.
Return JSON in this exact format:

{{
  "sections": [
    {{
      "heading": "Section Name",
      "paragraphs": [
        {{"index": <paragraph_index>, "original": "<original text>", "rewritten": "<rewritten text>"}}
      ]
    }}
  ],
  "keywords_added": ["keyword1", "keyword2"],
  "match_score": <1-100 estimated ATS match percentage>
}}

Include ALL paragraphs in the output, even if unchanged (set rewritten = original in that case).
Only modify paragraphs where changes improve JD alignment."""


def parse_response(raw_text: str) -> RewriteResult:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Claude response as JSON: {e}")

    rewrites = []
    for section in data.get("sections", []):
        for para in section.get("paragraphs", []):
            rewrites.append({
                "index": para["index"],
                "rewritten": para["rewritten"],
            })

    return RewriteResult(
        rewrites=rewrites,
        keywords_added=data.get("keywords_added", []),
        match_score=data.get("match_score", 0),
    )


def rewrite_resume(paragraphs: list[dict], job_description: str) -> RewriteResult:
    client = anthropic.Anthropic()

    prompt = build_prompt(paragraphs, job_description)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    return parse_response(raw_text)
