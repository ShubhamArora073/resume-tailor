import asyncio
import os
import re
import uuid
import shutil
import time
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Path
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from converter import extract_text_from_pdf
from rewriter import rewrite_resume, refine_resume
from pdf_generator import generate_pdf

load_dotenv()

TMP_BASE = "/tmp/resume-tailor"
MAX_PDF_SIZE = 10 * 1024 * 1024
MAX_PHOTO_SIZE = 5 * 1024 * 1024
CLEANUP_INTERVAL = 600
SESSION_MAX_AGE = 3600


async def cleanup_old_sessions():
    while True:
        try:
            if os.path.exists(TMP_BASE):
                now = time.time()
                for entry in os.listdir(TMP_BASE):
                    session_dir = os.path.join(TMP_BASE, entry)
                    if os.path.isdir(session_dir):
                        dir_age = now - os.path.getmtime(session_dir)
                        if dir_age > SESSION_MAX_AGE:
                            shutil.rmtree(session_dir, ignore_errors=True)
        except Exception:
            pass
        await asyncio.sleep(CLEANUP_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(cleanup_old_sessions())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Resume Tailor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


def cleanup_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)


def extract_jd_keywords(job_description: str) -> list[str]:
    """Extract meaningful keywords/phrases from a job description."""
    skill_patterns = [
        r'\b(?:AWS|GCP|Azure|Kubernetes|Docker|Terraform|Jenkins|Ansible|'
        r'Python|Go|Java|Linux|CI/CD|GitOps|Prometheus|Grafana|CloudWatch|'
        r'ELK|Elasticsearch|Datadog|Splunk|Kafka|Redis|PostgreSQL|MySQL|'
        r'MongoDB|Helm|ArgoCD|Argo Rollouts|Spinnaker|Chef|Puppet|Salt|'
        r'SonarQube|Maven|Gradle|Git|GitHub Actions|CircleCI|TravisCI|'
        r'CloudFormation|CDK|Pulumi|Vault|Consul|Istio|Envoy|Nginx|'
        r'HAProxy|RabbitMQ|SQS|SNS|Lambda|ECS|EKS|Fargate|EC2|S3|RDS|'
        r'DynamoDB|IAM|VPC|Route53|ALB|NLB|WAF|Shield|GuardDuty|'
        r'KMS|Secrets Manager|Parameter Store|CodePipeline|CodeBuild|'
        r'CodeDeploy|Bamboo|TeamCity|Nexus|Artifactory|JFrog|Packer|'
        r'Vagrant|VMware|vSphere|OpenStack|Ceph|GlusterFS|NFS|'
        r'Shell|Bash|PowerShell|Ruby|Perl|Node\.js|TypeScript|React|'
        r'Vue|Angular|REST|GraphQL|gRPC|HTTP|TCP|UDP|DNS|TLS|SSL|mTLS|'
        r'OAuth|SAML|OIDC|LDAP|Active Directory|SSO|MFA|'
        r'Jira|Confluence|ServiceNow|PagerDuty|OpsGenie|Slack|'
        r'Agile|Scrum|Kanban|DevOps|SRE|Platform Engineering|'
        r'ITIL|ITSM|Change Management|Incident Management)\b',
    ]

    phrase_patterns = [
        r'(?:site reliability engineering|infrastructure.as.code|'
        r'continuous integration|continuous delivery|continuous deployment|'
        r'blue.green deploy|canary deploy|rolling deploy|'
        r'incident response|root cause analysis|post.?mortem|'
        r'disaster recovery|business continuity|high availability|'
        r'load balancing|auto.?scaling|capacity planning|'
        r'configuration management|secrets management|'
        r'container orchestration|microservices|service mesh|'
        r'observability|monitoring|alerting|logging|tracing|'
        r'SLOs?|SLIs?|SLAs?|error budgets?|'
        r'MTTR|MTTD|MTTF|MTBF|'
        r'toil reduction|automation|self.?healing|'
        r'security hardening|vulnerability management|'
        r'compliance|SOC.?2|ISO.?27001|PCI.?DSS|HIPAA|FedRAMP|'
        r'cost optimization|FinOps|'
        r'cross.?functional|technical leadership|mentoring)',
    ]

    keywords = set()
    text_lower = job_description.lower()

    for pattern in skill_patterns:
        matches = re.findall(pattern, job_description, re.IGNORECASE)
        keywords.update(m.strip() for m in matches)

    for pattern in phrase_patterns:
        matches = re.findall(pattern, text_lower)
        keywords.update(m.strip() for m in matches)

    return sorted(keywords, key=str.lower)


def normalize_for_matching(text: str) -> str:
    """Normalize text for keyword matching: lowercase, treat hyphens/spaces as interchangeable."""
    return re.sub(r'[-_/]', ' ', text.lower()).strip()


def keyword_in_text(keyword: str, text_normalized: str) -> bool:
    """Check if a keyword appears in text, handling variants."""
    kw_norm = normalize_for_matching(keyword)
    if kw_norm in text_normalized:
        return True
    kw_nospace = kw_norm.replace(' ', '')
    if kw_nospace in text_normalized.replace(' ', ''):
        return True
    return False


def dedupe_keywords(keywords: list[str]) -> list[str]:
    """Remove keyword variants that are essentially the same."""
    seen_normalized = {}
    result = []
    for kw in keywords:
        norm = normalize_for_matching(kw)
        if norm not in seen_normalized:
            seen_normalized[norm] = kw
            result.append(kw)
    return result


def compute_match_score(resume_text: str, jd_keywords: list[str]) -> dict:
    """Compute real match score by checking which JD keywords appear in resume."""
    resume_normalized = normalize_for_matching(resume_text)
    deduped = dedupe_keywords(jd_keywords)
    found = []
    missing = []

    for kw in deduped:
        if keyword_in_text(kw, resume_normalized):
            found.append(kw)
        else:
            missing.append(kw)

    total = len(deduped)
    score = round((len(found) / total) * 100) if total > 0 else 0
    return {"score": score, "found": found, "missing": missing, "total": total}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tailor")
async def tailor(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    photo: UploadFile = File(None),
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
        pdf_content = await file.read()
        if len(pdf_content) > MAX_PDF_SIZE:
            raise HTTPException(status_code=413, detail="PDF file exceeds 10MB limit.")
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)

        photo_path = None
        if photo and photo.filename:
            photo_content = await photo.read()
            if len(photo_content) > MAX_PHOTO_SIZE:
                raise HTTPException(status_code=413, detail="Photo file exceeds 5MB limit.")
            photo_ext = os.path.splitext(photo.filename)[1] or ".jpg"
            photo_path = os.path.join(work_dir, f"photo{photo_ext}")
            with open(photo_path, "wb") as f:
                f.write(photo_content)

        resume_text = extract_text_from_pdf(pdf_path)

        result = await asyncio.to_thread(rewrite_resume, resume_text, job_description.strip())

        jd_keywords = extract_jd_keywords(job_description.strip())
        resume_data = result.resume_data

        output_pdf = os.path.join(work_dir, "tailored_resume.pdf")
        await asyncio.to_thread(generate_pdf, resume_data, output_pdf, photo_path)
        final_resume_text = extract_text_from_pdf(output_pdf)
        match_data = compute_match_score(final_resume_text, jd_keywords)

        if match_data["score"] < 85 and match_data["missing"]:
            refined_data = await asyncio.to_thread(
                refine_resume, resume_data, match_data["missing"]
            )
            resume_data = refined_data
            await asyncio.to_thread(generate_pdf, resume_data, output_pdf, photo_path)
            final_resume_text = extract_text_from_pdf(output_pdf)
            match_data = compute_match_score(final_resume_text, jd_keywords)

        return JSONResponse({
            "request_id": request_id,
            "match_score": match_data["score"],
            "keywords_found": match_data["found"],
            "keywords_missing": match_data["missing"],
            "keywords_total": match_data["total"],
            "claude_score": result.match_score,
            "claude_keywords_added": result.keywords_added,
            "resume_data": resume_data,
            "original_text_preview": resume_text[:2000],
        })

    except HTTPException:
        raise
    except Exception as e:
        cleanup_dir(work_dir)
        raise HTTPException(status_code=500, detail=str(e))


UUID_PATTERN = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'


@app.post("/regenerate/{request_id}")
async def regenerate(
    request: Request,
    request_id: str = Path(..., pattern=UUID_PATTERN),
):
    resume_data = await request.json()
    work_dir = os.path.join(TMP_BASE, request_id)
    if not os.path.exists(work_dir):
        raise HTTPException(status_code=404, detail="Session expired.")

    output_pdf = os.path.join(work_dir, "tailored_resume.pdf")

    photo_path = None
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = os.path.join(work_dir, f"photo{ext}")
        if os.path.exists(candidate):
            photo_path = candidate
            break

    await asyncio.to_thread(generate_pdf, resume_data, output_pdf, photo_path)

    return {"status": "ok"}


@app.get("/download/{request_id}")
def download(request_id: str = Path(..., pattern=UUID_PATTERN)):
    work_dir = os.path.join(TMP_BASE, request_id)
    output_pdf = os.path.join(work_dir, "tailored_resume.pdf")

    if not os.path.exists(output_pdf):
        raise HTTPException(status_code=404, detail="PDF not found. It may have expired.")

    return FileResponse(
        path=output_pdf,
        media_type="application/pdf",
        filename="tailored_resume.pdf",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
