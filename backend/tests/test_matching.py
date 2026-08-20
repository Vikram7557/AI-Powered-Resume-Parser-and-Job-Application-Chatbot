"""Qualification math: confidence = 0.6 * skills + 0.4 * experience."""
from job_roles import match_candidate_to_role

DEVELOPER = {
    "title": "Developer",
    "required_skills": ["Python", "JavaScript", "React", "REST APIs", "SQL"],
    "min_experience_years": 1.0,
}


def test_qualifies_when_most_skills_and_enough_experience():
    result = match_candidate_to_role(
        ["Python", "JavaScript", "React", "REST APIs"],
        2.0,
        DEVELOPER,
    )
    # 4/5 skills = 0.8; exp capped at 1.0 → 0.6*0.8 + 0.4*1 = 0.88
    assert result["confidence"] == 0.88
    assert result["qualifies"] is True
    assert "SQL" in result["missing_skills"]


def test_experience_is_capped_at_one():
    junior = match_candidate_to_role(
        ["Python", "JavaScript", "React", "REST APIs", "SQL"],
        1.0,
        DEVELOPER,
    )
    senior = match_candidate_to_role(
        ["Python", "JavaScript", "React", "REST APIs", "SQL"],
        10.0,
        DEVELOPER,
    )
    assert junior["confidence"] == senior["confidence"] == 1.0
    assert junior["qualifies"] is True


def test_skill_ratio_cannot_exceed_one():
    result = match_candidate_to_role(
        ["Python", "JavaScript", "React", "REST APIs", "SQL", "Docker", "AWS"],
        1.0,
        DEVELOPER,
    )
    assert result["confidence"] == 1.0
    assert result["qualifies"] is True


def test_rejects_when_skills_below_half_even_if_confidence_looks_ok():
    result = match_candidate_to_role(
        ["Python", "JavaScript"],
        5.0,
        DEVELOPER,
    )
    # 2/5 = 0.4; exp = 1.0 → 0.64, but skill_ratio < 0.5
    assert result["confidence"] == 0.64
    assert result["qualifies"] is False


def test_aliases_count_as_required_skills():
    result = match_candidate_to_role(
        ["Python", "JS", "React.js", "REST APIs", "MySQL"],
        1.0,
        DEVELOPER,
    )
    assert result["qualifies"] is True
    assert result["confidence"] == 1.0
    assert result["missing_skills"] == []


def test_tester_junior_can_qualify_at_six_months():
    tester = {
        "title": "Tester",
        "required_skills": [
            "Manual Testing",
            "Selenium",
            "Test Case Design",
            "SQL",
            "Agile",
        ],
        "min_experience_years": 0.5,
    }
    result = match_candidate_to_role(
        ["Manual Testing", "Selenium", "Test Cases", "SQL"],
        0.5,
        tester,
    )
    assert result["confidence"] == 0.88
    assert result["qualifies"] is True
