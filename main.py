import os
import uuid
import shutil
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from converter import pdf_to_docx, docx_to_pdf
from docx_editor import extract_paragraphs, apply_rewrites
from rewriter import rewrite_resume

app = FastAPI(title="Resume Tailor")
app.mount("/static", StaticFiles(directory="static"), name="static")

TMP_BASE = "/tmp/resume-tailor"


def cleanup_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tailor")
async def tailor(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_description: str = Form(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if len(job_description.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Job description must be at least 50 characters.",
        )

    request_id = str(uuid.uuid4())
    work_dir = os.path.join(TMP_BASE, request_id)
    os.makedirs(work_dir, exist_ok=True)

    try:
        pdf_path = os.path.join(work_dir, "input.pdf")
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)

        docx_path = pdf_to_docx(pdf_path, work_dir)

        paragraphs = extract_paragraphs(docx_path)

        result = rewrite_resume(paragraphs, job_description.strip())

        output_docx = os.path.join(work_dir, "tailored.docx")
        apply_rewrites(docx_path, result.rewrites, output_docx)

        try:
            output_pdf = docx_to_pdf(output_docx, work_dir)
        except Exception:
            output_pdf = output_docx

        background_tasks.add_task(cleanup_dir, work_dir)

        return FileResponse(
            path=output_pdf,
            media_type="application/pdf" if output_pdf.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="tailored_resume.pdf" if output_pdf.endswith(".pdf") else "tailored_resume.docx",
            headers={
                "X-Match-Score": str(result.match_score),
                "X-Keywords-Added": ", ".join(result.keywords_added),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        cleanup_dir(work_dir)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
