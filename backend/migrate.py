"""
Create the database, tables, and seed job roles.

Run once after setting DATABASE_URL:

    cd backend
    python migrate.py

If an old SQLite file (app.db) exists, candidate rows are copied into MySQL.
"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, SessionLocal, engine, ensure_database
from models import CandidateORM, JobRoleORM
from seed import seed_job_roles


def copy_sqlite_candidates(sqlite_path: Path) -> int:
    sqlite_engine = create_engine(
        f"sqlite:///{sqlite_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SqliteSession = sessionmaker(bind=sqlite_engine)
    src = SqliteSession()
    dest = SessionLocal()
    copied = 0
    try:
        rows = src.query(CandidateORM).all()
        if not rows:
            return 0
        existing_emails = {
            email for (email,) in dest.query(CandidateORM.email).all() if email
        }
        for row in rows:
            if row.email and row.email in existing_emails:
                continue
            dest.add(
                CandidateORM(
                    name=row.name,
                    email=row.email,
                    phone=row.phone,
                    skills_json=row.skills_json,
                    education=row.education,
                    experience_years=row.experience_years,
                    matched_role=row.matched_role,
                    confidence=row.confidence,
                    qualifies=row.qualifies,
                    agreed_to_contact=row.agreed_to_contact,
                    created_at=row.created_at,
                )
            )
            copied += 1
        dest.commit()
        return copied
    finally:
        src.close()
        dest.close()
        sqlite_engine.dispose()


def migrate() -> None:
    ensure_database()
    Base.metadata.create_all(bind=engine)
    print("Tables created: job_roles, candidates")
    seed_job_roles()

    sqlite_path = Path(__file__).resolve().parent / "app.db"
    if sqlite_path.exists():
        copied = copy_sqlite_candidates(sqlite_path)
        print(f"Copied {copied} candidate(s) from SQLite app.db")
    else:
        print("No SQLite app.db found - skipped candidate copy")

    db = SessionLocal()
    try:
        roles = db.query(JobRoleORM).count()
        candidates = db.query(CandidateORM).count()
        print(f"MySQL now has {roles} job role(s) and {candidates} candidate(s)")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
