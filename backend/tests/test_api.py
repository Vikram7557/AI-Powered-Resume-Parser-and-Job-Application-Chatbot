from chatbot import Session, evaluate_profile


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_session(client):
    response = client.post("/session")
    assert response.status_code == 200
    assert "session_id" in response.json()


def test_roles_lists_three_openings(client):
    titles = {row["title"] for row in client.get("/roles").json()}
    assert titles == {"Developer", "Tester", "Data Analyst"}


def test_quick_apply_asks_for_resume_when_none_on_file(client):
    session_id = client.post("/session").json()["session_id"]
    response = client.post(
        "/quick-apply",
        json={"session_id": session_id, "role_title": "Developer"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "upload" in body["reply"].lower()
    assert body["intended_role"] == "Developer"
    assert body["stage"] == "AWAIT_RESUME"


def test_role_preview_returns_seeded_jd(client):
    session_id = client.post("/session").json()["session_id"]
    response = client.post(
        "/role-preview",
        json={"session_id": session_id, "role_title": "Tester"},
    )
    assert response.status_code == 200
    reply = response.json()["reply"]
    assert "Tester" in reply
    assert "Selenium" in reply


def test_upload_rejects_non_resume_file(client):
    session_id = client.post("/session").json()["session_id"]
    response = client.post(
        "/upload-resume",
        params={"session_id": session_id},
        files={"file": ("photo.png", b"not a resume", "image/png")},
    )
    assert response.status_code == 422


def test_upload_txt_uses_parser_then_chat_payload(client, monkeypatch):
    monkeypatch.setattr(
        "main.parse_resume",
        lambda _path: {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "9876543210",
            "skills": ["Python", "JavaScript", "React", "REST APIs", "SQL"],
            "education": "B.Tech",
            "experience_years": 2.0,
        },
    )
    monkeypatch.setattr(
        "main.inject_resume_result",
        lambda session, profile, filename=None: "We found your name is John Doe.",
    )
    session_id = client.post("/session").json()["session_id"]
    response = client.post(
        "/upload-resume",
        params={"session_id": session_id},
        files={"file": ("resume.txt", b"John Doe\nPython", "text/plain")},
    )
    assert response.status_code == 200
    assert "John Doe" in response.json()["reply"]


def test_evaluate_profile_qualifies_developer_without_llm():
    session = Session()
    session.candidate_profile = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "9876543210",
        "skills": ["Python", "JavaScript", "React", "REST APIs", "SQL"],
        "education": "B.Tech",
        "experience_years": 2.0,
    }
    evaluation = evaluate_profile(session, "Developer")
    assert evaluation["primary"]["role"] == "Developer"
    assert evaluation["primary"]["qualifies"] is True
    assert session.stage.value == "AWAIT_CONTACT_CONFIRM"
    assert "Developer" in session.applied_roles
