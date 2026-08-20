# Ava — AI Resume Parser & Job Application Chatbot

Conversational hiring assistant built for **Conversive.ai Assignment 101**. Ava greets a candidate, presents open roles, accepts a PDF or text resume, extracts a structured profile with an LLM, scores the match with a published formula, and records contact consent.

---

## Overview

Ava is a full-stack application: a React chat UI and an Openings catalogue talk to a FastAPI backend. Chat is orchestrated with tool calling (list roles, fetch a job description, request a resume, store contact preference). Resume text is extracted with pdfplumber (or UTF-8 for `.txt`), then parsed to JSON by the language model. Qualification is **not** decided by the model; it is computed in `job_roles.py` so the result is deterministic and testable.

**Roles (seeded):** Developer · Tester · Data Analyst

---

## Features

- Natural-language chat (apply, browse, ask about a JD, small talk, off-topic refusal)
- Openings tab: view full job descriptions and apply into the same chat session
- Resume upload: PDF and `.txt`
- LLM extraction: name, email, phone, skills, education, years of experience
- Confidence scoring with a skill-floor so extra years cannot hide missing skills
- Alternate-role suggestions only when those roles actually qualify
- Contact confirmation when the candidate qualifies
- Claude via OpenRouter, with Gemini (multi-key) fallback
- MySQL persistence for roles and candidate records
- pytest coverage for scoring, parser helpers, and REST endpoints

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | Python 3.12+, FastAPI, Uvicorn |
| LLM (primary) | Claude via OpenRouter (Messages API, tool calling) |
| LLM (fallback) | Google Gemini (`google-generativeai`), rotating API keys |
| Database | MySQL, SQLAlchemy, PyMySQL |
| PDF | pdfplumber |
| Tests | pytest, FastAPI TestClient (LLM mocked) |

---

## Architecture

```
React (chat + openings + upload)
        │  REST
        ▼
FastAPI  ── chatbot.py     conversation + tools
         ── resume_parser.py   PDF/TXT → text → LLM JSON
         ── job_roles.py   match score + MySQL
         ── llm.py         OpenRouter → Gemini key chain
```

Separation of concerns matches the assignment: parsing, dialogue, and matching are separate modules. FastAPI only wires them. File upload is a dedicated endpoint; files are not sent through chat tool calls.

System-design diagrams (architecture, user flow, NLP pipeline) belong in the presentation. A written summary is in `docs/Write-up.pdf`.

---

## Qualification logic

After extraction, the candidate is scored against the role they applied for.

| Term | Definition |
| --- | --- |
| Skill overlap | Required skills found on the resume ÷ number of required skills (aliases such as `JS` → JavaScript). Extra skills do not raise the ratio above 1.0. |
| Experience score | `min(candidate years / role minimum, 1.0)` |
| Confidence | `0.6 × skill overlap + 0.4 × experience score` |

**Qualifies** only if **both** are true:

- `confidence ≥ 0.5`
- `skill overlap ≥ 0.5`

If the chosen role fails, Ava offers only other openings that pass the same rule. If none pass, the candidate is told they were not selected. If they pass, extracted contact details are shown and consent to contact is requested.

---

## Repository structure

```
├── backend/
│   ├── main.py              HTTP routes
│   ├── chatbot.py           Dialogue + tool calling
│   ├── resume_parser.py     Text extract + LLM parse
│   ├── job_roles.py         Matching and candidate persistence
│   ├── llm.py               OpenRouter / Gemini client
│   ├── models.py            SQLAlchemy models
│   ├── database.py
│   ├── seed.py              Three job roles
│   ├── migrate.py           Database + schema
│   ├── config.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── pytest.ini
│   └── tests/
├── frontend/
│   ├── src/                 React UI
│   ├── package.json
│   └── .env.example
├── docs/
│   └── Write-up.pdf         Assignment write-up
└── README.md
```

---

## Prerequisites

- Python 3.9 or later
- Node.js 18 or later
- MySQL 8 (local instance)
- An OpenRouter API key (Claude) and/or one or more Gemini API keys

---

## Configuration

### Backend — `backend/.env`

Copy `backend/.env.example` and set real keys. Do not commit `.env`.

| Variable | Purpose |
| --- | --- |
| `OPENROUTER_API_KEY` | Primary LLM (Claude) |
| `CLAUDE_MODEL` | OpenRouter model id (default `anthropic/claude-sonnet-4`) |
| `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3` | Fallback chain |
| `GEMINI_MODEL` | Default `gemini-2.0-flash` |
| `DATABASE_URL` | SQLAlchemy URL, e.g. `mysql+pymysql://user:password@localhost:3306/job_application_chatbot` |
| `APP_URL` / `APP_TITLE` | OpenRouter referer headers |

### Frontend — `frontend/.env`

```
VITE_API_BASE_URL=http://localhost:8000
```

---

## Setup

### 1. Database

Create a MySQL user/database that matches `DATABASE_URL`, then:

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # macOS / Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # macOS / Linux: cp .env.example .env
python migrate.py              # database, tables, seed roles
```

### 2. API

```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Health check: [http://localhost:8000/health](http://localhost:8000/health)

### 3. UI

```bash
cd frontend
npm install
copy .env.example .env         # optional; default is already localhost:8000
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness |
| `POST` | `/session` | New chat session |
| `GET` | `/roles` | Seeded openings |
| `POST` | `/chat` | Body: `{ "session_id", "message" }` |
| `POST` | `/upload-resume` | Query: `session_id`; multipart file (`.pdf` / `.txt`) |
| `POST` | `/reuse-resume` | Score the resume already on the session |
| `POST` | `/quick-apply` | Start apply for a role (from Openings) |
| `POST` | `/role-preview` | Full job description in chat |

Interactive docs while the API is running: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Tests

Tests use SQLite and mock the LLM. MySQL and live keys are not required.

```bash
cd backend
venv\Scripts\activate
pytest -q
```

Covered: confidence formula (including the skill floor), skill aliases, `.txt` extract, JSON normalisation, `/health`, `/session`, `/roles`, upload validation, quick-apply, role preview, and qualify-without-LLM.

---

## Typical user flow

1. Candidate opens Ava and states intent to apply (any phrasing).
2. They browse **Openings**, view a job description, or apply from chat.
3. They upload a PDF or `.txt` resume (or reuse one already on the session).
4. The system extracts the profile and scores the chosen role.
5. Qualified: confirm contact details and consent. Not qualified: matching alternatives only, or a clear not-selected outcome.

---

## Assignment mapping

| Requirement | Implementation |
| --- | --- |
| Conversational apply flow, ≥3 roles | Chat + seeded Developer / Tester / Data Analyst |
| Flexible NLP | LLM + tool calling (not a keyword state machine) |
| PDF or text resume | pdfplumber + UTF-8 `.txt` |
| Extract name, email, phone, skills, education, experience | LLM JSON parse |
| Qualify against role attributes | Formula in `job_roles.py` |
| Confirm contact if qualified | Chat consent + `candidates.agreed_to_contact` |
| Modular code + APIs | Separate modules + FastAPI |
| Bonus: confidence scoring | Weighted skill + experience score |
| Bonus: LLM parse | Claude / Gemini instead of spaCy NER |