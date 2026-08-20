"""
FastAPI entrypoint. Wires chatbot.py (LLM orchestration) + resume_parser.py +
job_roles.py (DB-backed) together.

Run: uvicorn main:app --reload --port 8000
(job_roles table is auto-seeded on startup — see seed.py)
"""
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chatbot import (
    Session,
    evaluate_profile,
    handle_message,
    inject_resume_result,
    narrate_match,
    preview_role,
    build_ui_hints,
    session_snapshot,
    start_application,
)
from job_roles import list_roles
from resume_parser import parse_resume
from seed import seed_job_roles

app = FastAPI(title="Resume Parser & Job Application Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: lock down for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory chat session store (separate from persisted DB records).
# TODO: swap for Redis/DB-backed sessions for multi-instance deployments.
SESSIONS: dict[str, Session] = {}


@app.on_event("startup")
def on_startup():
    seed_job_roles()


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ReuseResumeRequest(BaseModel):
    session_id: str
    role_title: str | None = None


class RoleActionRequest(BaseModel):
    session_id: str
    role_title: str


class ChatResponse(BaseModel):
    reply: str
    stage: str
    profile: dict | None = None
    matches: list[dict] = []
    intended_role: str | None = None
    applied_roles: list[str] = []
    rejected_roles: list[str] = []
    resume_filename: str | None = None
    role_cards: list[dict] = []
    suggestions: list[str] = []
    provider: str = "openrouter"
    model_label: str = "Claude"


def get_session(session_id: str) -> Session:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = Session()
    return SESSIONS[session_id]


def chat_payload(session: Session, reply: str) -> dict:
    return {"reply": reply, **session_snapshot(session)}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/session")
def new_session():
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = Session()
    return {"session_id": session_id}


@app.get("/roles")
def get_roles():
    return list_roles()


def _llm_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session = get_session(req.session_id)
    reply = _llm_call(handle_message, session, req.message)
    return chat_payload(session, reply)


@app.post("/upload-resume", response_model=ChatResponse)
def upload_resume(session_id: str, file: UploadFile = File(...)):
    session = get_session(session_id)
    suffix = Path(file.filename or "resume.pdf").suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=422,
            detail="Please upload a PDF or .txt resume.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        profile = parse_resume(tmp_path)
    except Exception as exc:
        print(f"Resume parse failed: {exc!r}")
        raise HTTPException(
            status_code=422,
            detail=str(exc) if str(exc) else "Could not parse that resume. Please upload a PDF or .txt file.",
        ) from exc

    reply = _llm_call(inject_resume_result, session, profile, filename=file.filename)
    return chat_payload(session, reply)


@app.post("/reuse-resume", response_model=ChatResponse)
def reuse_resume(req: ReuseResumeRequest):
    session = get_session(req.session_id)
    if not session.candidate_profile:
        raise HTTPException(status_code=400, detail="No resume is on file for this session.")
    evaluation = evaluate_profile(session, req.role_title)
    session.last_evaluation = evaluation
    reply = _llm_call(narrate_match, session, evaluation)
    build_ui_hints(session)
    return chat_payload(session, reply)


@app.post("/quick-apply", response_model=ChatResponse)
def quick_apply(req: RoleActionRequest):
    session = get_session(req.session_id)
    reply = _llm_call(start_application, session, req.role_title)
    return chat_payload(session, reply)


@app.post("/role-preview", response_model=ChatResponse)
def role_preview(req: RoleActionRequest):
    session = get_session(req.session_id)
    reply = preview_role(session, req.role_title)
    return chat_payload(session, reply)
