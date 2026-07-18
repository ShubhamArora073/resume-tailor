import os
import tempfile
from pdf_generator import generate_pdf


def test_generate_pdf_creates_file():
    data = {
        "name": "Test User",
        "title": "Engineer",
        "contact": {"email": "t@t.com", "phone": "123", "location": "NY"},
        "summary": "A summary.",
        "experience": [{
            "company": "Acme",
            "title": "Dev",
            "location": "NYC",
            "start_date": "01/2020",
            "end_date": "Present",
            "description": "",
            "bullets": ["Did stuff", "More stuff"],
        }],
        "skills": ["Python", "Docker"],
        "education": [{"institution": "MIT", "degree": "BS CS", "location": "Boston", "end_date": "2020"}],
        "certifications": ["AWS"],
        "achievements": [{"title": "Award", "description": "Got it"}],
    }

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.pdf")
        result = generate_pdf(data, out)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0
