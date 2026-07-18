import json
import os
import ssl
from dataclasses import dataclass

import anthropic
import httpx


@dataclass
class RewriteResult:
    resume_data: dict
    keywords_added: list[str]
    match_score: int


SYSTEM_PROMPT = """You are an expert resume writer who creates polished, ATS-optimized 2-page resumes.

Your approach:
- You write like a professional resume writer, not a robot. Strong action verbs, quantified impact.
- Only reword and re-emphasize existing experience. NEVER fabricate skills, roles, or achievements.
- Mirror exact keyword phrases from the JD naturally within bullet points.
- Each bullet starts with a strong action verb and includes measurable impact where data exists.
- You ensure the content fills EXACTLY 2 full pages — not 1.5, not 2.5.

Content guidelines for a 2-page resume:
- Summary: 3-4 lines, compelling narrative connecting experience to the target role
- Most recent role (5+ years): 8-10 strong bullets
- Second role (3-4 years): 6-7 bullets
- Third role (1-2 years): 4-5 bullets
- Fourth/older roles (1-2 years): 3-4 bullets
- Skills: 20-25 keywords grouped logically
- Education: Only college/university degrees
- Certifications: All relevant certs listed
- Achievements: 2-3 notable awards or recognitions

Writing rules:
- Every bullet must demonstrate IMPACT (what changed because of your work)
- Use metrics: percentages, counts, time saved, team sizes, scale of systems
- Start bullets with: Led, Architected, Implemented, Automated, Reduced, Improved, Designed, Drove, Spearheaded, Delivered, Orchestrated, Established
- NO weak bullets like "Worked on X" or "Responsible for Y" — rewrite them with impact
- Order bullets by relevance to the JD (most relevant first within each role)
- Remove duplicates — if two bullets say similar things, merge into one stronger bullet

Return ONLY valid JSON in the exact format specified. No markdown, no explanation, no code fences."""


def build_prompt(resume_text: str, job_description: str) -> str:
    return f"""## Job Description

{job_description}

## Current Resume Content (raw text extracted from PDF)

{resume_text}

## Instructions

Rewrite this resume to be ATS-optimized for the above JD. Produce content for a European-style 2-page CV.

The output renders into a two-column template: left sidebar has photo, contact, skills, languages, certifications.
The main right area has summary, experience, education, achievements.
Target content that fills exactly 2 A4 pages with this layout.

Rules:
- Ignore garbled text, emoji artifacts, or broken formatting from PDF extraction
- Education: ONLY university/college degrees (skip high school, intermediate, boards)
- Clean up any location formatting issues
- Include languages section (infer from resume context — if Indian, include English and Hindi)
- Skills: list as individual items, max 15, ordered by JD relevance

Content targets for 2-page European CV:
- Most recent role: 6-8 bullets
- Second role: 5-6 bullets
- Third role: 3-4 bullets
- Older roles: 2-3 bullets each
- Summary: 3-4 sentences (50-70 words)

Return this exact JSON structure:

{{
  "name": "Full Name",
  "title": "Professional Title (tailored to match JD's target role)",
  "contact": {{
    "email": "email@example.com",
    "phone": "phone number",
    "location": "City, Country",
    "linkedin": "linkedin.com/in/username (if available)"
  }},
  "summary": "3-4 sentence professional summary (50-70 words) positioning the candidate for this role.",
  "experience": [
    {{
      "company": "Company Name",
      "title": "Job Title",
      "location": "City, Country",
      "start_date": "MM/YYYY",
      "end_date": "MM/YYYY or Present",
      "bullets": ["Impact-driven bullet with metrics and action verb"]
    }}
  ],
  "skills": ["Skill1", "Skill2"],
  "languages": [
    {{"name": "English", "level": "Native/Fluent"}},
    {{"name": "Hindi", "level": "Native"}}
  ],
  "education": [
    {{
      "institution": "University Name",
      "degree": "Degree Name",
      "location": "City, Country",
      "end_date": "YYYY"
    }}
  ],
  "certifications": ["Cert Name 1", "Cert Name 2"],
  "achievements": [
    {{
      "title": "Award/Recognition Title",
      "description": "One sentence explaining the achievement"
    }}
  ],
  "keywords_added": ["keyword1", "keyword2"],
  "match_score": 85
}}

IMPORTANT:
- Ensure enough bullet points to fill 2 pages (typically 22-28 bullets total — sidebar takes space)
- Skills should be JD-relevant first, then supporting skills
- Every bullet must pass the "so what?" test — it must show impact, not just activity
- Include ALL relevant certifications — they go in the sidebar"""


def parse_response(raw_text: str) -> RewriteResult:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Claude response as JSON: {e}")

    keywords = data.pop("keywords_added", [])
    match_score = data.pop("match_score", 0)

    return RewriteResult(
        resume_data=data,
        keywords_added=keywords,
        match_score=match_score,
    )


REFINE_PROMPT = """You previously generated a tailored resume, but the following keywords from the JD are MISSING from the output.
Your job: incorporate these missing keywords naturally into the resume content WITHOUT fabricating new experience.

Strategies:
- Add missing keywords into existing bullet points where they naturally fit
- Add the skill to the skills section if the candidate plausibly has it (based on their background)
- Rephrase bullets to use the exact keyword phrasing
- Add a keyword into the summary if it's a core theme

Do NOT force keywords that don't fit the candidate's real experience. It's better to miss a keyword than to lie.

MISSING KEYWORDS: {missing_keywords}

Here is the current resume JSON that needs refinement:

{current_json}

Return the COMPLETE updated resume JSON in the exact same format. Every field must be present.
Only modify content to incorporate missing keywords — do not remove existing content or change the structure.
Return ONLY valid JSON, no markdown, no explanation."""


def _make_client() -> anthropic.Anthropic:
    ssl_context = ssl.create_default_context()
    http_client = httpx.Client(verify=ssl_context, timeout=120.0)

    if os.environ.get("AI_GATEWAY_URL"):
        return anthropic.Anthropic(
            base_url=os.environ["AI_GATEWAY_URL"],
            api_key=os.environ["AI_GATEWAY_KEY"],
            default_headers={"x-sfdc-user-id": os.environ.get("AI_GATEWAY_USER", "")},
            http_client=http_client,
        )

    return anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        http_client=http_client,
    )


def refine_resume(current_data: dict, missing_keywords: list[str]) -> dict:
    """Second pass: incorporate missing keywords into existing resume."""
    client = _make_client()

    prompt = REFINE_PROMPT.format(
        missing_keywords=", ".join(missing_keywords),
        current_json=json.dumps(current_data, indent=2),
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=16384,
        system="You refine resumes to improve ATS keyword coverage. Only incorporate keywords that fit naturally. Never fabricate experience. Return valid JSON only.",
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]

    return json.loads(cleaned)


def rewrite_resume(resume_text: str, job_description: str) -> RewriteResult:
    client = _make_client()

    prompt = build_prompt(resume_text, job_description)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=16384,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    return parse_response(raw_text)
