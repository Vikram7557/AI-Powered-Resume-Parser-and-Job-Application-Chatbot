"""
Resume parsing module: PDF -> raw text -> structured candidate profile via LLM.
"""
import json
import re
from pathlib import Path
from typing import TypedDict

import pdfplumber

from config import MODEL_NAME
from llm import client


class CandidateProfile(TypedDict):
    name: str
    email: str
    phone: str
    skills: list[str]
    education: str
    experience_years: float


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from an uploaded resume PDF."""
    text_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)
    return "\n".join(text_chunks).strip()


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read().strip()


def extract_resume_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".txt":
        return extract_text_from_txt(file_path)
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    raise ValueError("Please upload a PDF or .txt resume.")


PARSE_PROMPT = """You are a resume parser. Extract these fields from the resume text.
Return ONLY a JSON object with this exact shape:

{
  "name": "string",
  "email": "string",
  "phone": "string",
  "skills": ["skill1", "skill2"],
  "education": "highest degree + institution, one line",
  "experience_years": 0
}

Use 0 for experience_years if unknown. Use empty strings/arrays if a field is missing.

Resume text:
---
RESUME_TEXT_HERE
---
"""


def _response_text(response) -> str:
    parts = []
    for block in getattr(response, "content", []) or []:
        text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
        if text:
            parts.append(text)
    if parts:
        return "\n".join(parts).strip()
    return (getattr(response, "text", None) or "").strip()


def _extract_json(raw: str) -> dict:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("Parser did not return a JSON object")
    return data


def _normalize_profile(data: dict) -> CandidateProfile:
    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in re.split(r"[,;/]", skills) if s.strip()]
    try:
        years = float(data.get("experience_years") or 0)
    except (TypeError, ValueError):
        years = 0.0
    return {
        "name": str(data.get("name") or "").strip(),
        "email": str(data.get("email") or "").strip(),
        "phone": str(data.get("phone") or "").strip(),
        "skills": [str(s).strip() for s in skills if str(s).strip()],
        "education": str(data.get("education") or "").strip(),
        "experience_years": years,
    }


def parse_resume_with_llm(resume_text: str) -> CandidateProfile:
    prompt = PARSE_PROMPT.replace("RESUME_TEXT_HERE", resume_text[:18000])

    def _call(json_mode: bool):
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1200,
            json_mode=json_mode,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = _response_text(response)
        if not raw:
            raise ValueError("LLM returned an empty parse result")
        return _normalize_profile(_extract_json(raw))

    try:
        return _call(True)
    except Exception as first:
        print(f"JSON-mode parse failed ({first!r}); retrying without JSON mode.")
        return _call(False)


def parse_resume(file_path: str) -> CandidateProfile:
    """PDF or .txt path -> structured candidate profile."""
    text = extract_resume_text(file_path)
    if not text:
        raise ValueError(
            "No readable text in that file. Use a .txt resume or a text-based PDF (not a scanned image)."
        )
    return parse_resume_with_llm(text)
