import uuid
import json
import logging
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .data import PROJECTS, SERVICES, TEAM
from .db import init_db, save_contact, save_internship_application

BASE_DIR = Path(__file__).resolve().parent
ACCESS_LOG_PATH = BASE_DIR.parent / "server_access.log"
ACTIVITY_LOG_PATH = BASE_DIR.parent / "log.log"
access_logger = logging.getLogger("novatech.access")
if not access_logger.handlers:
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    formatter = logging.Formatter("%(message)s")
    for log_path in (ACCESS_LOG_PATH, ACTIVITY_LOG_PATH):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(formatter)
        access_logger.addHandler(handler)

PROJECT_NAME = "Explainable GraphRAG-Based Cyber Threat Detection using Knowledge Graph & Large Language Model"
SQLI_PATTERNS = (
    re.compile(r"(?:'|%27)\s*(?:or|and)\s*['\d]", re.IGNORECASE),
    re.compile(r"(?:union\s+select|select\s+.+\s+from|drop\s+table|--|/\*)", re.IGNORECASE),
)
RECON_PATHS = re.compile(r"(?:^|/)(?:\.env|\.git|wp-admin|wp-login\.php|phpmyadmin|server-status)(?:/|$)", re.IGNORECASE)
login_failures = defaultdict(deque)
security_store = None


def log_event(event_type: str, request: Request, **details: object) -> None:
    """Write structured, privacy-conscious events for security analysis."""
    client_ip = request.client.host if request.client else "unknown"
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": PROJECT_NAME,
        "event_type": event_type,
        "source_ip": client_ip,
        "method": request.method,
        "path": request.url.path,
        **details,
    }
    access_logger.info(json.dumps(event, ensure_ascii=True, sort_keys=True))


def detect_sqli(value: str) -> list[str]:
    indicators = []
    for pattern in SQLI_PATTERNS:
        if pattern.search(value):
            indicators.append(pattern.pattern)
    return indicators


def inspect_input(request: Request, field_values: dict[str, str]) -> None:
    for field_name, value in field_values.items():
        indicators = detect_sqli(value)
        if indicators:
            log_event(
                "sql_injection_indicator",
                request,
                field=field_name,
                indicators=indicators,
                value_length=len(value),
            )


def get_security_store():
    global security_store
    if security_store is None:
        from detector import SecurityStore

        security_store = SecurityStore()
    return security_store

UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="NovaTech Solutions")
app.add_middleware(SessionMiddleware, secret_key="novatech-session-secret")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = None
    if RECON_PATHS.search(request.url.path):
        log_event("reconnaissance_scan", request, indicator="sensitive_or_hidden_path")
    query_indicators = detect_sqli(request.url.query)
    if query_indicators:
        log_event(
            "sql_injection_indicator",
            request,
            field="query_string",
            indicators=query_indicators,
            value_length=len(request.url.query),
        )
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        client_host = request.client.host if request.client else "unknown"
        status_code = response.status_code if response else 500
        user_agent = request.headers.get("user-agent", "-")
        log_event(
            "http_request",
            request,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            user_agent=user_agent,
        )

INTERNSHIPS = {
    "web-development": {"name": "Web Development", "location": "Mumbai"},
    "data-science": {"name": "Data Science", "location": "Mumbai"},
    "artificial-intelligence": {"name": "Artificial Intelligence", "location": "Mumbai"},
}


@app.on_event("startup")
def startup_event() -> None:
    UPLOADS_DIR.mkdir(exist_ok=True)
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "services": SERVICES,
            "team": TEAM,
            "projects": PROJECTS,
            "message": "",
            "status": "",
        },
    )


@app.post("/contact", response_class=HTMLResponse)
def contact_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    company: str = Form(""),
    service_interest: str = Form(""),
    message: str = Form(...),
):
    inspect_input(
        request,
        {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "company": company,
            "service_interest": service_interest,
            "message": message,
        },
    )
    save_contact(full_name, email, phone, company, service_interest, message)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "services": SERVICES,
            "team": TEAM,
            "projects": PROJECTS,
            "message": "Thanks! Your inquiry has been submitted successfully.",
            "status": "ok",
        },
    )


@app.get("/api/services")
def api_services():
    return JSONResponse({"services": SERVICES})


@app.get("/api/team")
def api_team():
    return JSONResponse({"team": TEAM})


@app.get("/api/projects")
def api_projects():
    return JSONResponse({"projects": PROJECTS})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/security-dashboard", response_class=HTMLResponse)
def security_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="security_dashboard.html",
        context={"request": request},
    )


@app.get("/api/security/summary")
def security_summary():
    try:
        return get_security_store().summary()
    except Exception as error:
        return JSONResponse({"error": str(error)}, status_code=503)


@app.get("/api/security/events")
def security_events():
    try:
        return {"events": get_security_store().recent_events()}
    except Exception as error:
        return JSONResponse({"error": str(error)}, status_code=503)


@app.get("/api/security/explain/{source_ip}")
def security_explanation(source_ip: str):
    try:
        return {"source_ip": source_ip, "explanation": get_security_store().explain_ip(source_ip)}
    except Exception as error:
        return JSONResponse({"error": str(error)}, status_code=503)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "message": "",
            "status": "",
        },
    )


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    inspect_input(request, {"email": email})
    if email.strip().lower() == "admin@novatech.com" and password == "Admin@123":
        request.session["is_logged_in"] = True
        request.session["user_email"] = email.strip().lower()
        login_failures.pop(request.client.host if request.client else "unknown", None)
        return RedirectResponse(url=f"/careers/internships", status_code=303)

    client_ip = request.client.host if request.client else "unknown"
    failures = login_failures[client_ip]
    now = time.monotonic()
    failures.append(now)
    while failures and now - failures[0] > 60:
        failures.popleft()
    log_event("failed_login", request, attempt_count_last_60_seconds=len(failures))
    if len(failures) >= 5:
        log_event(
            "brute_force_login",
            request,
            attempt_count_last_60_seconds=len(failures),
            threshold=5,
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "message": "Invalid email or password.",
            "status": "error",
        },
        status_code=401,
    )


@app.get("/careers", response_class=HTMLResponse)
def careers(request: Request):
    return templates.TemplateResponse(request=request, name="careers.html", context={"request": request})


@app.get("/careers/jobs", response_class=HTMLResponse)
def jobs_page(request: Request):
    return templates.TemplateResponse(request=request, name="jobs.html", context={"request": request})


@app.get("/careers/internships", response_class=HTMLResponse)
def internships_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="internships.html",
        context={
            "request": request,
            "internships": INTERNSHIPS,
        },
    )


@app.get("/careers/internships/{internship_slug}/apply", response_class=HTMLResponse)
def internship_apply_page(request: Request, internship_slug: str):
    if not request.session.get("is_logged_in"):
        return RedirectResponse(url="/login", status_code=303)

    internship_info = INTERNSHIPS.get(internship_slug)
    if not internship_info:
        return templates.TemplateResponse(
            request=request,
            name="internships.html",
            context={
                "request": request,
                "internships": INTERNSHIPS,
                "message": "Internship not found.",
                "status": "error",
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="internship_apply.html",
        context={
            "request": request,
            "internship_slug": internship_slug,
            "internship_name": internship_info["name"],
            "internship_location": internship_info["location"],
            "message": "",
            "status": "",
        },
    )


@app.post("/careers/internships/{internship_slug}/apply", response_class=HTMLResponse)
def submit_internship_application(
    request: Request,
    internship_slug: str,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    college_name: str = Form(...),
    graduation_year: str = Form(...),
    skills: str = Form(...),
    resume_file: UploadFile = File(...),
    cover_letter: str = Form(...),
):
    if not request.session.get("is_logged_in"):
        return RedirectResponse(url="/login", status_code=303)

    internship_info = INTERNSHIPS.get(internship_slug)
    if not internship_info:
        return templates.TemplateResponse(
            request=request,
            name="internships.html",
            context={
                "request": request,
                "internships": INTERNSHIPS,
                "message": "Internship not found.",
                "status": "error",
            },
            status_code=404,
        )

    filename = resume_file.filename or ""
    is_pdf_content = (resume_file.content_type or "").lower() == "application/pdf"
    is_pdf_name = filename.lower().endswith(".pdf")
    file_bytes = resume_file.file.read()
    is_pdf_signature = file_bytes.startswith(b"%PDF-")
    if not (is_pdf_content and is_pdf_name and is_pdf_signature):
        log_event(
            "malicious_file_upload",
            request,
            filename_extension=Path(filename).suffix.lower() or "<none>",
            content_type=resume_file.content_type or "unknown",
            size_bytes=len(file_bytes),
            reason="resume must be a genuine PDF file",
        )
        return templates.TemplateResponse(
            request=request,
            name="internship_apply.html",
            context={
                "request": request,
                "internship_slug": internship_slug,
                "internship_name": internship_info["name"],
                "internship_location": internship_info["location"],
                "message": "Only PDF resume is allowed.",
                "status": "error",
            },
            status_code=400,
        )

    unique_resume_name = f"{uuid.uuid4().hex}.pdf"
    resume_path = UPLOADS_DIR / unique_resume_name
    with resume_path.open("wb") as file_out:
        file_out.write(file_bytes)

    save_internship_application(
        internship_name=internship_info["name"],
        full_name=full_name,
        email=email,
        phone=phone,
        college_name=college_name,
        graduation_year=graduation_year,
        skills=skills,
        resume_link=f"/uploads/{unique_resume_name}",
        cover_letter=cover_letter,
    )

    return templates.TemplateResponse(
        request=request,
        name="internship_apply.html",
        context={
            "request": request,
            "internship_slug": internship_slug,
            "internship_name": internship_info["name"],
            "internship_location": internship_info["location"],
            "message": "Application submitted successfully. Our HR team will contact you soon.",
            "status": "ok",
        },
    )
