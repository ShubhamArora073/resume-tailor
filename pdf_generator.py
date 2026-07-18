import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

TARGET_PAGES = 2
FONT_MIN = 8.5
FONT_MAX = 10.5
FONT_STEP = 0.25

DEFAULTS = {
    "font_size": 9.5,
    "line_height": 1.4,
    "section_margin": 12,
    "job_margin": 10,
    "bullet_margin": 3,
    "page_padding": 20,
}

CAPS = {
    "line_height": 1.5,
    "section_margin": 14,
    "job_margin": 12,
    "bullet_margin": 4,
    "page_padding": 22,
}

STEPS = {
    "line_height": 0.02,
    "section_margin": 0.5,
    "job_margin": 0.5,
    "bullet_margin": 0.25,
    "page_padding": 0.5,
}


def _render(env, resume_data, photo_path, params):
    template = env.get_template("resume.html")
    html_content = template.render(
        data=resume_data,
        photo_path=photo_path,
        **params,
    )
    return HTML(string=html_content, base_url=TEMPLATES_DIR).render()


def generate_pdf(resume_data: dict, output_path: str, photo_path: str = None) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(default=True, default_for_string=True),
    )

    params = dict(DEFAULTS)

    doc = _render(env, resume_data, photo_path, params)

    # Phase 1: shrink font if content overflows target pages
    if len(doc.pages) > TARGET_PAGES:
        low = FONT_MIN
        high = params["font_size"]
        best_font = FONT_MIN

        while low <= high:
            mid = round((low + high) / 2 / FONT_STEP) * FONT_STEP
            mid = round(mid, 2)
            test = {**params, "font_size": mid}
            test_doc = _render(env, resume_data, photo_path, test)
            if len(test_doc.pages) <= TARGET_PAGES:
                best_font = mid
                doc = test_doc
                low = round(mid + FONT_STEP, 2)
            else:
                high = round(mid - FONT_STEP, 2)

        params["font_size"] = best_font
        doc = _render(env, resume_data, photo_path, params)

    # Phase 2: if exactly at target pages, mildly expand spacing to reduce trailing whitespace
    if len(doc.pages) == TARGET_PAGES:
        keys = list(CAPS.keys())
        changed = True
        while changed:
            changed = False
            for key in keys:
                if params[key] >= CAPS[key]:
                    continue
                trial = dict(params)
                trial[key] = round(params[key] + STEPS[key], 2)
                trial_doc = _render(env, resume_data, photo_path, trial)
                if len(trial_doc.pages) <= TARGET_PAGES:
                    params[key] = trial[key]
                    doc = trial_doc
                    changed = True
                    break

    doc.write_pdf(output_path)
    return output_path
