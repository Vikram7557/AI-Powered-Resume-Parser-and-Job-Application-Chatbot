from pathlib import Path

import pytest

from resume_parser import (
    _extract_json,
    _normalize_profile,
    extract_resume_text,
)


def test_extract_txt_resume(tmp_path: Path):
    path = tmp_path / "resume.txt"
    path.write_text("Jane Doe\nPython, SQL\n", encoding="utf-8")
    assert "Jane Doe" in extract_resume_text(str(path))


def test_rejects_unsupported_suffix(tmp_path: Path):
    path = tmp_path / "resume.docx"
    path.write_text("not used", encoding="utf-8")
    with pytest.raises(ValueError, match="PDF or .txt"):
        extract_resume_text(str(path))


def test_normalize_profile_from_messy_llm_json():
    profile = _normalize_profile(
        {
            "name": " John Doe ",
            "email": "john@example.com",
            "phone": "9876543210",
            "skills": "Python, React; SQL",
            "education": "B.Tech",
            "experience_years": "2",
        }
    )
    assert profile["name"] == "John Doe"
    assert profile["skills"] == ["Python", "React", "SQL"]
    assert profile["experience_years"] == 2.0


def test_extract_json_strips_markdown_fences():
    data = _extract_json('```json\n{"name": "Ava", "skills": []}\n```')
    assert data["name"] == "Ava"
