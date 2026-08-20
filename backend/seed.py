"""
Seeds the job_roles table on startup (idempotent — upserts by title).
This is the "DB seeding" step: run automatically from main.py's startup event,
or manually via `python seed.py`.
"""
import json

from sqlalchemy import inspect, text

from database import Base, SessionLocal, engine, ensure_database
from models import CandidateORM, JobRoleORM  # noqa: F401  (register candidates table)

SEED_ROLES = [
    {
        "title": "Developer",
        "description": (
            "Conversive.ai is hiring a Developer to build the product behind Ava — our "
            "conversational hiring assistant. You will work across a Python API, a React "
            "frontend, and the data layer that stores candidates, roles, and applications.\n\n"
            "This is a hands-on full-stack role: you will ship features end-to-end, review "
            "code, and help keep the platform reliable as more candidates apply."
        ),
        "responsibilities": [
            "Design, build, and ship features across the Python backend and React frontend",
            "Create and consume REST APIs, including auth, file upload, and chat endpoints",
            "Model and query application data in SQL (MySQL or similar)",
            "Write clean, testable code and take part in code reviews",
            "Debug production issues, improve performance, and document what you ship",
            "Work with product and QA to turn hiring-flow requirements into working software",
        ],
        "required_skills": ["Python", "JavaScript", "React", "REST APIs", "SQL"],
        "nice_to_have": ["TypeScript", "Node.js", "FastAPI", "Git", "AWS", "CI/CD"],
        "qualifications": "Bachelor's in Computer Science, IT, or a related field",
        "min_experience_years": 1.0,
    },
    {
        "title": "Tester",
        "description": (
            "Conversive.ai is hiring a Tester to own quality for Ava and the hiring workflows "
            "candidates and recruiters use every day. You will design test cases, execute "
            "manual cycles, and grow automation so releases stay predictable.\n\n"
            "You will sit close to engineering: log clear bugs, retest fixes, and help the "
            "team catch issues before they reach applicants."
        ),
        "responsibilities": [
            "Write and execute test cases for web flows, chat, and REST APIs",
            "Perform thorough manual testing across browsers and key user journeys",
            "Build and maintain UI automation with Selenium (or a similar framework)",
            "Log reproducible bugs, track them through fix and retest, and sign off releases",
            "Validate data-heavy scenarios with SQL where results depend on stored records",
            "Work in an Agile cadence: stand-ups, sprint goals, and regression before release",
        ],
        "required_skills": ["Manual Testing", "Selenium", "Test Case Design", "SQL", "Agile"],
        "nice_to_have": ["ISTQB", "Postman", "API Testing", "JIRA", "Cypress"],
        "qualifications": "Bachelor's degree; ISTQB Foundation preferred",
        "min_experience_years": 0.5,
    },
    {
        "title": "Data Analyst",
        "description": (
            "Conversive.ai is hiring a Data Analyst to turn hiring and product data into "
            "decisions. You will work with application funnels, role-match outcomes, and "
            "usage metrics so recruiting and product teams know what to do next.\n\n"
            "You will own dashboards, ad-hoc analysis, and clear recommendations — not "
            "just charts, but what the numbers mean for Conversive.ai."
        ),
        "responsibilities": [
            "Analyze candidate, application, and match data using SQL and Python",
            "Build and maintain reports in Excel and Power BI for recruiting and product",
            "Apply descriptive statistics to spot funnel drop-offs, trends, and outliers",
            "Define simple metrics (apply rate, qualify rate, time-to-screen) and keep them trusted",
            "Present findings in plain language and recommend experiments or process changes",
            "Partner with engineering to improve data quality and reporting pipelines",
        ],
        "required_skills": ["Python", "SQL", "Excel", "Power BI", "Statistics"],
        "nice_to_have": ["pandas", "Tableau", "A/B Testing", "Data Visualization"],
        "qualifications": "Bachelor's in Statistics, Computer Science, Mathematics, or related field",
        "min_experience_years": 1.0,
    },
]


def _ensure_role_columns():
    """create_all does not add columns to existing tables — patch them here."""
    inspector = inspect(engine)
    if "job_roles" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("job_roles")}
    statements = []
    if "description" not in existing:
        statements.append("ALTER TABLE job_roles ADD COLUMN description TEXT")
    if "responsibilities_json" not in existing:
        statements.append("ALTER TABLE job_roles ADD COLUMN responsibilities_json TEXT")
    if "nice_to_have_json" not in existing:
        statements.append("ALTER TABLE job_roles ADD COLUMN nice_to_have_json TEXT")
    if not statements:
        return
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def seed_job_roles():
    ensure_database()
    Base.metadata.create_all(bind=engine)
    _ensure_role_columns()
    db = SessionLocal()
    try:
        for role in SEED_ROLES:
            row = db.query(JobRoleORM).filter(JobRoleORM.title == role["title"]).first()
            payload = {
                "required_skills_json": json.dumps(role["required_skills"]),
                "qualifications": role["qualifications"],
                "min_experience_years": role["min_experience_years"],
                "description": role["description"],
                "responsibilities_json": json.dumps(role["responsibilities"]),
                "nice_to_have_json": json.dumps(role["nice_to_have"]),
            }
            if row:
                for key, value in payload.items():
                    setattr(row, key, value)
            else:
                db.add(JobRoleORM(title=role["title"], **payload))
        db.commit()
        print(f"Job roles ready: {len(SEED_ROLES)}.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_job_roles()
