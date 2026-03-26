import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "company.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                company TEXT,
                service_interest TEXT,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS internship_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internship_name TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                college_name TEXT NOT NULL,
                graduation_year TEXT NOT NULL,
                skills TEXT NOT NULL,
                resume_link TEXT,
                cover_letter TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def save_contact(
    full_name: str,
    email: str,
    phone: str,
    company: str,
    service_interest: str,
    message: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO contacts(full_name, email, phone, company, service_interest, message)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (full_name, email, phone, company, service_interest, message),
        )
        connection.commit()


def save_internship_application(
    internship_name: str,
    full_name: str,
    email: str,
    phone: str,
    college_name: str,
    graduation_year: str,
    skills: str,
    resume_link: str,
    cover_letter: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO internship_applications(
                internship_name,
                full_name,
                email,
                phone,
                college_name,
                graduation_year,
                skills,
                resume_link,
                cover_letter
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                internship_name,
                full_name,
                email,
                phone,
                college_name,
                graduation_year,
                skills,
                resume_link,
                cover_letter,
            ),
        )
        connection.commit()
