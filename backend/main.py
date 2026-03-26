import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .data import PROJECTS, SERVICES, TEAM
from .db import init_db, save_contact, save_internship_application

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="NovaTech Solutions")
app.add_middleware(SessionMiddleware, secret_key="novatech-session-secret")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
        "index.html",
        {
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
    save_contact(full_name, email, phone, company, service_interest, message)
    return templates.TemplateResponse(
        "index.html",
        {
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


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "message": "",
            "status": "",
        },
    )


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    if email.strip().lower() == "admin@novatech.com" and password == "Admin@123":
        request.session["is_logged_in"] = True
        request.session["user_email"] = email.strip().lower()
        return RedirectResponse(url=f"/careers/internships", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "message": "Invalid email or password.",
            "status": "error",
        },
        status_code=401,
    )


@app.get("/careers", response_class=HTMLResponse)
def careers(request: Request):
    return templates.TemplateResponse("careers.html", {"request": request})


@app.get("/careers/jobs", response_class=HTMLResponse)
def jobs_page(request: Request):
    return templates.TemplateResponse("jobs.html", {"request": request})


@app.get("/careers/internships", response_class=HTMLResponse)
def internships_page(request: Request):
    return templates.TemplateResponse(
        "internships.html",
        {
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
            "internships.html",
            {
                "request": request,
                "internships": INTERNSHIPS,
                "message": "Internship not found.",
                "status": "error",
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        "internship_apply.html",
        {
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
            "internships.html",
            {
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
    if not (is_pdf_content or is_pdf_name):
        return templates.TemplateResponse(
            "internship_apply.html",
            {
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
    file_bytes = resume_file.file.read()
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
        "internship_apply.html",
        {
            "request": request,
            "internship_slug": internship_slug,
            "internship_name": internship_info["name"],
            "internship_location": internship_info["location"],
            "message": "Application submitted successfully. Our HR team will contact you soon.",
            "status": "ok",
        },
    )
