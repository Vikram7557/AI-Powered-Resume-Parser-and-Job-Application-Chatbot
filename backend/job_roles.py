"""
Job role queries + candidate-to-role matching + candidate persistence.
Separation of concerns: this file knows nothing about chat state or PDF parsing.
Roles come from the DB (seeded by seed.py); this module owns the matching math.
"""
import json
import re

from database import SessionLocal
from models import CandidateORM, JobRoleORM

_SKILL_ALIASES = {
    "js": "javascript",
    "react.js": "react",
    "reactjs": "react",
    "node.js": "nodejs",
    "node": "nodejs",
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    "test case design": "test cases",
    "test case": "test cases",
    "manual testing": "manual testing",
    "agile methodology": "agile",
    "powerbi": "power bi",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "mysql": "sql",
    "postgresql": "sql",
    "postgres": "sql",
    "sqlite": "sql",
}


def format_job_description(role: dict) -> str:
    """Render a full JD for chat (View) using seeded role data only."""
    exp = role.get("min_experience_years") or 0
    exp_label = "6+ months" if exp == 0.5 else f"{int(exp) if exp == int(exp) else exp}+ years"
    skills = ", ".join(role.get("required_skills") or [])
    nice = ", ".join(role.get("nice_to_have") or [])
    bullets = "\n".join(f"• {item}" for item in (role.get("responsibilities") or []))
    parts = [
        f"**{role.get('title')} — Job description**",
        "",
        "**About the role**",
        (role.get("description") or "").strip(),
        "",
        "**What you'll do**",
        bullets,
        "",
        f"**Required skills:** {skills}",
    ]
    if nice:
        parts.append(f"**Nice to have:** {nice}")
    parts.extend(
        [
            f"**Qualifications:** {role.get('qualifications') or '—'}",
            f"**Experience:** {exp_label}",
        ]
    )
    return "\n".join(parts)


def list_roles() -> list[dict]:
    db = SessionLocal()
    try:
        return [r.to_dict() for r in db.query(JobRoleORM).all()]
    finally:
        db.close()


def get_role(title: str) -> dict | None:
    needle = (title or "").strip()
    if not needle:
        return None
    db = SessionLocal()
    try:
        role = db.query(JobRoleORM).filter(JobRoleORM.title.ilike(needle)).first()
        if role:
            return role.to_dict()
        lowered = needle.lower()
        for row in db.query(JobRoleORM).all():
            t = row.title.lower()
            if t in lowered or lowered in t:
                return row.to_dict()
        return None
    finally:
        db.close()


def _normalize_skill(skill: str) -> str:
    cleaned = re.sub(r"[^a-z0-9+#.\s]", " ", (skill or "").lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return _SKILL_ALIASES.get(cleaned, cleaned)


def _skill_matches(candidate_skills: list[str], required: str) -> bool:
    required_norm = _normalize_skill(required)
    if not required_norm:
        return False
    for skill in candidate_skills:
        cand = _normalize_skill(skill)
        if cand == required_norm:
            return True
        if len(required_norm) >= 4 and (required_norm in cand or cand in required_norm):
            return True
    return False


def _skill_overlap_ratio(candidate_skills: list[str], required_skills: list[str]) -> float:
    if not required_skills:
        return 0.0
    hits = sum(1 for req in required_skills if _skill_matches(candidate_skills, req))
    return hits / len(required_skills)


def match_candidate_to_role(
    candidate_skills: list[str], candidate_experience_years: float, role: dict
) -> dict:
    """
    Confidence score (bonus requirement):
    confidence = 0.6 * skill_overlap_ratio + 0.4 * experience_score
    """
    required = role["required_skills"]
    skill_ratio = _skill_overlap_ratio(candidate_skills, required)
    exp_score = min(
        candidate_experience_years / max(role["min_experience_years"], 0.1), 1.0
    )
    confidence = round(0.6 * skill_ratio + 0.4 * exp_score, 2)
    matched = [s for s in required if _skill_matches(candidate_skills, s)]
    missing = [s for s in required if not _skill_matches(candidate_skills, s)]
    return {
        "role": role["title"],
        "confidence": confidence,
        "qualifies": confidence >= 0.5 and skill_ratio >= 0.5,
        "matched_skills": matched,
        "missing_skills": missing,
    }


def score_all_roles(candidate_skills: list[str], candidate_experience_years: float) -> list[dict]:
    results = [
        match_candidate_to_role(candidate_skills, candidate_experience_years, role)
        for role in list_roles()
    ]
    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results


def best_match(candidate_skills: list[str], candidate_experience_years: float) -> dict:
    results = score_all_roles(candidate_skills, candidate_experience_years)
    return results[0] if results else {}


def save_candidate(profile: dict, match: dict) -> int:
    """Persists a parsed candidate + match result. Returns the new row id."""
    db = SessionLocal()
    try:
        row = CandidateORM(
            name=profile.get("name"),
            email=profile.get("email"),
            phone=profile.get("phone"),
            skills_json=json.dumps(profile.get("skills", [])),
            education=profile.get("education"),
            experience_years=profile.get("experience_years"),
            matched_role=match.get("role"),
            confidence=match.get("confidence"),
            qualifies=match.get("qualifies"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def update_candidate_match(candidate_id: int, match: dict) -> None:
    db = SessionLocal()
    try:
        row = db.query(CandidateORM).filter(CandidateORM.id == candidate_id).first()
        if row:
            row.matched_role = match.get("role")
            row.confidence = match.get("confidence")
            row.qualifies = match.get("qualifies")
            db.commit()
    finally:
        db.close()


def update_candidate_contact_preference(candidate_id: int, agrees: bool) -> None:
    db = SessionLocal()
    try:
        row = db.query(CandidateORM).filter(CandidateORM.id == candidate_id).first()
        if row:
            row.agreed_to_contact = agrees
            db.commit()
    finally:
        db.close()
