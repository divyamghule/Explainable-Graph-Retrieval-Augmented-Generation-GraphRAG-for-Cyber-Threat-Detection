# NovaTech Solutions

## Full-Stack Company Website with Explainable GraphRAG Cyber-Threat Detection

NovaTech Solutions is an educational full-stack IT company website combined
with an explainable cybersecurity monitoring module. The website provides
company content, contact collection, careers and internship applications. The
security module converts structured web activity logs into a Neo4j knowledge
graph and uses Gemini to generate evidence-based analyst explanations.

## What This Project Includes

### Company website

- Responsive NovaTech Solutions landing page
- Services, projects and team sections
- Contact inquiry form stored in SQLite
- Careers, jobs and internships pages
- Three internship roles:
  - Web Development - Mumbai
  - Data Science - Mumbai
  - Artificial Intelligence - Mumbai
- Login-protected internship application flow
- PDF-only resume upload validation
- SQLite storage for internship applications
- JSON APIs for services, team and projects

### Explainable GraphRAG threat detection

- Structured request and security-event logging
- Detection indicators for:
  - SQL injection attempts
  - Brute-force login activity
  - Suspicious file uploads
  - Reconnaissance of sensitive paths
  - Suspicious HTTP status activity
- Neo4j graph relationships between source IPs, endpoints and security events
- Threat scoring based on attempted events
- Recent-event and top-source queries for the dashboard
- Gemini explanations grounded in the events retrieved from Neo4j
- India Standard Time (IST) timestamps using `Asia/Kolkata` / UTC+05:30
- Graceful Neo4j outage handling with connection timeout and retry backoff

## Architecture

```text
Browser
   |
   v
FastAPI website (port 8001)
   |-- HTML templates, CSS and JavaScript
   |-- SQLite: contacts and internship applications
   |-- log.log / server_access.log
   v
detector.py
   |-- reads structured activity logs
   |-- writes graph data to Neo4j (Bolt 7687)
   |-- retrieves evidence and requests Gemini explanation
   v
Security dashboard
```

## Technology Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Frontend:** Jinja2 templates, HTML, CSS and JavaScript
- **Application database:** SQLite
- **Knowledge graph:** Neo4j
- **LLM explanations:** Google Gemini API
- **Timezone:** `Asia/Kolkata` (IST)

## Project Structure

```text
.
├── backend/
│   ├── main.py                    # FastAPI routes and security logging
│   ├── data.py                    # Services, team and project content
│   ├── db.py                      # SQLite schema and persistence
│   ├── templates/                 # Website and security dashboard pages
│   └── static/                    # CSS and browser JavaScript
├── detector.py                    # Neo4j ingestion and Gemini explanations
├── run.py                         # Uvicorn application runner
├── run.bat                        # Windows setup and startup script
├── requirements.txt               # Python dependencies
├── .env.example                   # Configuration template
├── log.log                        # Structured activity log
├── server_access.log              # Access log
└── backend/company.db             # SQLite database created by the app
```

## Requirements

- Windows, macOS or Linux
- Python 3.10+
- A Neo4j server for security dashboard features
- A Google Gemini API key for analyst explanations

The website itself can run with SQLite without Neo4j. Only the detector,
security metrics, event list and Gemini explanation features require Neo4j.

## Setup

### Windows

From the project directory:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set your own Neo4j password and Gemini API key. Never commit
`.env` or real API keys.

### Other platforms

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

## Configuration

```env
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DATABASE=neo4j
NEO4J_CONNECTION_TIMEOUT_SECONDS=5
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash
LOG_FILE_PATH=log.log
THREAT_THRESHOLD=0.75
NEO4J_RETRY_SECONDS=15
```

`GEMINI_MODEL` must name a model enabled for the configured API key and
supporting content generation. If Google changes model availability, replace
it with another generation-capable model.

## Run the Application

### Windows launcher

```bat
run.bat
```

The launcher starts the detector and website in separate terminals and opens
the website and security dashboard in the browser. If `.env` is missing, it
creates the file from `.env.example` and continues starting the website.

### Manual startup

Start the website:

```bash
python run.py
```

Start the detector in another terminal:

```bash
python detector.py
```

To process existing log entries once:

```bash
python detector.py --once --from-start
```

Open the website at [http://127.0.0.1:8001](http://127.0.0.1:8001) and the
security dashboard at
[http://127.0.0.1:8001/security-dashboard](http://127.0.0.1:8001/security-dashboard).

## Demo Login

- **URL:** `/login`
- **Email:** `admin@novatech.com`
- **Password:** `Admin@123`

This is demonstration-only authentication and must not be used in production.

## Routes and APIs

## output image 
<img width="1023" height="210" alt="image" src="https://github.com/user-attachments/assets/5873feb7-08ef-41e5-b6c8-5a2adfd1c014" />
<img width="1342" height="643" alt="image" src="https://github.com/user-attachments/assets/a740dc30-9f7b-4732-82b7-2b5fa75aa915" />
<img width="874" height="496" alt="image" src="https://github.com/user-attachments/assets/00a70d0e-87a6-4536-8889-d80b74a21b8f" />
<img width="1365" height="627" alt="image" src="https://github.com/user-attachments/assets/cb3adbf3-68db-40dd-98f9-196e9007f222" />
<img width="1259" height="551" alt="image" src="https://github.com/user-attachments/assets/332483fa-0dfd-446e-aee5-ca32e4b7cb6c" />
<img width="1332" height="331" alt="image" src="https://github.com/user-attachments/assets/112d9db5-2896-4a58-b15f-74c3e385d0e0" />
<img width="614" height="629" alt="Screenshot 2026-10-24 125049" src="https://github.com/user-attachments/assets/6270f971-06cd-40cc-8f12-729f85f2de06" />








### Website routes

- `GET /`
- `GET /careers`
- `GET /careers/jobs`
- `GET /careers/internships`
- `GET /careers/internships/{internship_slug}/apply`
- `POST /careers/internships/{internship_slug}/apply`
- `GET /login`
- `POST /login`
- `POST /contact`
- `GET /health`

### Public data APIs

- `GET /api/services`
- `GET /api/team`
- `GET /api/projects`

### Security APIs

- `GET /api/security/summary`
- `GET /api/security/events`
- `GET /api/security/explain/{source_ip}`

## How Explainable GraphRAG Works

1. FastAPI records each request as structured JSON in `log.log` and
   `server_access.log`.
2. `detector.py` reads each event and classifies its threat type.
3. Neo4j stores `IPAddress`, `Endpoint` and `SecurityEvent` nodes.
4. Relationships such as `GENERATED`, `TARGETED`, `ATTEMPTED` and `ACCESSED`
   preserve the event context.
5. The dashboard retrieves recent events and the most active threat sources.
6. When an IP is explained, the detector retrieves up to 50 related events,
   calculates a threat score and sends only that evidence to Gemini.
7. Gemini returns a defensive explanation containing the attack type, timeline,
   confidence and practical containment steps.

## Security and Privacy Notes

- Do not commit `.env`, passwords, API keys or uploaded resumes.
- The included login credentials are for local demonstration only.
- Resume uploads are accepted only when the filename, MIME type and PDF
  signature are valid.
- Security logs record request metadata and detection indicators, not form
  secrets or passwords.
- Neo4j is optional for the main website but required for threat intelligence
  views.
- This project is an educational demonstration, not a production security
  monitoring system.

## Troubleshooting

### Neo4j connection refused

Start Neo4j and confirm that it is listening on `127.0.0.1:7687`. Verify
`NEO4J_PASSWORD` and `NEO4J_DATABASE` in `.env`. The detector uses a bounded
connection timeout and retries after `NEO4J_RETRY_SECONDS`.

### Gemini model not found

Check `GEMINI_API_KEY` and set `GEMINI_MODEL` to a generation-capable model
available to that key. The API key must be active and have access to the
Generative Language API.

### Website does not open

Check that port `8001` is available and run:

```bash
python run.py
```

Then open `http://127.0.0.1:8001`.

## License and Purpose

This project is intended for college, portfolio and educational
demonstration purposes.
