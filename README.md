# NovaTech Solutions - Full Stack IT Company Website

A complete college-ready full-stack web development project.

## Features
- Modern responsive IT company landing page
- Services, projects, team sections (dynamic from backend data)
- Contact inquiry form
- SQLite database storage for inquiries
- JSON APIs for services/team/projects
- Careers flow: Job Apply page -> Jobs / Internships
- Jobs page with "No Job Available" state
- Internships page with 3 roles:
	- Web Development (Mumbai)
	- Data Science (Mumbai)
	- Artificial Intelligence (Mumbai)
- Internship application form with realistic fields
- PDF resume upload support (`.pdf` only)
- Login required before internship apply

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: HTML, CSS, JavaScript, Jinja2 templates
- Database: SQLite

## Project Structure
- `backend/main.py` - API routes and page rendering
- `backend/data.py` - company data content
- `backend/db.py` - SQLite setup and save logic
- `backend/templates/index.html` - full website page
- `backend/static/css/styles.css` - styles
- `backend/static/js/main.js` - frontend interactions
- `run.py` - app runner

## Run Locally
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open:
- http://127.0.0.1:8001

## Login (Demo)
- URL: `/login`
- Email: `admin@novatech.com`
- Password: `Admin@123`

Internship apply page requires login.

## Careers Routes
- `GET /careers`
- `GET /careers/jobs`
- `GET /careers/internships`
- `GET /careers/internships/{internship_slug}/apply`
- `POST /careers/internships/{internship_slug}/apply`

## API Endpoints
- `GET /api/services`
- `GET /api/team`
- `GET /api/projects`
- `POST /contact`
- `GET /health`

## Notes
- Contact form submissions are stored in `backend/company.db`.
- Internship applications are stored in `backend/company.db` (table: `internship_applications`).
- Uploaded resume PDFs are stored in `backend/uploads/`.
- This project is built for educational/portfolio demonstration.
