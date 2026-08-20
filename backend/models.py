"""
SQLAlchemy ORM models: JobRoleORM (seeded reference data) and CandidateORM
(every parsed application, for the "DB" part of the assignment).
"""
import json
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from database import Base


class JobRoleORM(Base):
    __tablename__ = "job_roles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), unique=True, nullable=False)
    required_skills_json = Column(Text, nullable=False)  # JSON-encoded list[str]
    qualifications = Column(String(255), nullable=False)
    min_experience_years = Column(Float, nullable=False)
    description = Column(Text, default="")
    responsibilities_json = Column(Text, default="[]")
    nice_to_have_json = Column(Text, default="[]")

    @property
    def required_skills(self) -> list[str]:
        return json.loads(self.required_skills_json)

    @property
    def responsibilities(self) -> list[str]:
        return json.loads(self.responsibilities_json or "[]")

    @property
    def nice_to_have(self) -> list[str]:
        return json.loads(self.nice_to_have_json or "[]")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description or "",
            "responsibilities": self.responsibilities,
            "required_skills": self.required_skills,
            "nice_to_have": self.nice_to_have,
            "qualifications": self.qualifications,
            "min_experience_years": self.min_experience_years,
        }


class CandidateORM(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150))
    email = Column(String(150))
    phone = Column(String(50))
    skills_json = Column(Text)  # JSON-encoded list[str]
    education = Column(String(255))
    experience_years = Column(Float)
    matched_role = Column(String(100))
    confidence = Column(Float)
    qualifies = Column(Boolean)
    agreed_to_contact = Column(Boolean, nullable=True)  # null until answered
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "skills": json.loads(self.skills_json or "[]"),
            "education": self.education,
            "experience_years": self.experience_years,
            "matched_role": self.matched_role,
            "confidence": self.confidence,
            "qualifies": self.qualifies,
            "agreed_to_contact": self.agreed_to_contact,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
