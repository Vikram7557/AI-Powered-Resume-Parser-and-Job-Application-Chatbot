"""
LLM-orchestrated chatbot using Claude tool-calling.

Why this design over a rule-based state machine:
- Handles small talk ("how are you"), off-topic refusal (weather etc.), and
  arbitrary phrasing naturally, while still reliably triggering the right
  backend actions (list roles, request resume upload, record contact consent)
  via tool calls instead of brittle keyword matching.
- Matches the JD's explicit ask: "integrate and orchestrate LLMs into
  conversational flows... tool-calling / function-calling pipelines."

Separation of concerns is preserved: this file only owns conversation
orchestration. It calls into job_roles.py for role data; resume parsing/
matching still lives in resume_parser.py / job_roles.py and is triggered
from main.py's /upload-resume endpoint (file upload can't happen through a
text tool call, so that part stays a dedicated REST endpoint).
"""
import json
from enum import Enum

from config import MODEL_NAME
from job_roles import (
    format_job_description,
    get_role,
    list_roles,
    save_candidate,
    score_all_roles,
    update_candidate_contact_preference,
    update_candidate_match,
)
from llm import client, last_llm_info


class Stage(str, Enum):
    CHATTING = "CHATTING"
    AWAIT_RESUME = "AWAIT_RESUME"
    AWAIT_RESUME_CHOICE = "AWAIT_RESUME_CHOICE"
    AWAIT_CONTACT_CONFIRM = "AWAIT_CONTACT_CONFIRM"
    DONE = "DONE"


SYSTEM_PROMPT = """You are Ava, a friendly job application assistant for Conversive.ai.

Your job:
- Have a natural, warm conversation. If the user makes small talk (e.g. "how are you"),
  respond briefly and naturally, then gently steer back toward applying or exploring roles.
- If they decline applying, be gracious and wait — don't keep pushing. If they later ask
  about roles, help them.
- If the user wants to browse all openings, do NOT list every role in chat. Tell them
  they can open the Openings tab to view and apply. You may call list_job_roles only to
  answer a specific question (e.g. "any testing jobs?") and mention matching titles briefly.
- If they ask for a job description, details, or "what does this role involve", call
  get_role_details and present a real JD: about the role, responsibilities, required
  skills, nice-to-have skills, qualifications, and minimum experience. Do not invent them.
- Uncertain phrasing like "maybe developer" still means they want that role's details.
- If the user confirms they want to apply, call request_resume_upload with the role_title
  they chose (if known).
  - If no resume is on file yet, ask them to upload a PDF or .txt file. Do NOT mention UI internals.
  - If a resume is already on file, the tool result will say so. Ask whether they want to
    continue with the uploaded resume or upload a different one. Do NOT re-score until they
    choose. If they want to keep the same resume, call reuse_uploaded_resume with the role.
- After a screening result: be honest. Cite matched_skills and missing_skills from the
  tool/system payload only. Never invent contact info, years, degrees, or extra openings.
- If they did not qualify for the role they applied to, ONLY mention roles in
  alternative_matches (true matches). Never list unmatched open roles. Ask if they want to
  apply to those matching opening(s). If alternative_matches is empty, say they were not
  selected for this role or other current openings — do not promise a recruiter callback.
- If they qualify (original role or a matching alternative they chose), then ask whether
  Conversive.ai may contact them. When they answer, call record_contact_preference.
- After contact preference is recorded, you may still answer hiring questions.
- STRICT SCOPE: only job applications, open roles, and hiring at Conversive.ai. Off-topic
  (weather, news, trivia, cooking, coding help): politely refuse and redirect. Do not answer it.
- Keep most replies concise (2-4 sentences). Job descriptions may use short bullet lists.
"""

TOOLS = [
    {
        "name": "list_job_roles",
        "description": "Get all currently open job roles with required skills, qualifications, and minimum experience.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_role_details",
        "description": "Get the full job description (summary, responsibilities, skills, qualifications, min experience) for one role by title.",
        "input_schema": {
            "type": "object",
            "properties": {"role_title": {"type": "string", "description": "e.g. 'Developer', 'Tester', 'Data Analyst'"}},
            "required": ["role_title"],
        },
    },
    {
        "name": "request_resume_upload",
        "description": "Call when the user wants to apply. Pass the role they chose. If a resume is already on file, this asks them to reuse or replace it instead of scoring immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role_title": {
                    "type": "string",
                    "description": "Role they are applying for, e.g. 'Developer'",
                }
            },
        },
    },
    {
        "name": "reuse_uploaded_resume",
        "description": "Score the already-uploaded resume against a role. Call this when the user confirms they want to keep the same resume for a new or same role.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role_title": {
                    "type": "string",
                    "description": "Role to score against, e.g. 'Developer'",
                }
            },
            "required": ["role_title"],
        },
    },
    {
        "name": "record_contact_preference",
        "description": "Call this after the user answers whether Conversive.ai can contact them, and only if they qualified for at least one role they applied to.",
        "input_schema": {
            "type": "object",
            "properties": {"agrees_to_contact": {"type": "boolean"}},
            "required": ["agrees_to_contact"],
        },
    },
]


class Session:
    def __init__(self):
        self.history: list[dict] = []
        self.stage: Stage = Stage.CHATTING
        self.candidate_profile: dict | None = None
        self.match_result: dict | None = None
        self.all_matches: list[dict] = []
        self.candidate_id: int | None = None
        self.intended_role: str | None = None
        self.applied_roles: list[str] = []
        self.rejected_roles: list[str] = []
        self.resume_filename: str | None = None
        self.pending_reply: str | None = None
        self.last_evaluation: dict | None = None
        self.ui_role_cards: list[dict] = []
        self.ui_suggestions: list[str] = []
        self._listed_roles: bool = False
        self._detail_role: str | None = None


def session_snapshot(session: Session) -> dict:
    return {
        "stage": session.stage.value,
        "profile": session.candidate_profile,
        "matches": session.all_matches,
        "intended_role": session.intended_role,
        "applied_roles": session.applied_roles,
        "rejected_roles": session.rejected_roles,
        "resume_filename": session.resume_filename,
        "role_cards": session.ui_role_cards,
        "suggestions": session.ui_suggestions,
        **last_llm_info(),
    }


def _reset_turn_ui(session: Session) -> None:
    session.ui_role_cards = []
    session.ui_suggestions = []
    session._listed_roles = False
    session._detail_role = None
    session.last_evaluation = None


def build_ui_hints(session: Session) -> None:
    """Attach clickable role cards and suggested replies for the frontend."""
    suggestions: list[str] = []
    evaluation = session.last_evaluation

    if evaluation:
        primary = evaluation.get("primary") or {}
        alts = evaluation.get("alternative_matches") or []
        if primary.get("qualifies"):
            suggestions = ["Yes, you may contact me", "No, please don't contact me"]
        elif alts:
            suggestions = [f"Apply for {m['role']}" for m in alts] + ["See other roles"]
        else:
            suggestions = ["See other roles", "That's all, thanks"]
    elif session.stage == Stage.AWAIT_CONTACT_CONFIRM:
        suggestions = ["Yes, you may contact me", "No, please don't contact me"]
    elif session.stage == Stage.AWAIT_RESUME_CHOICE:
        suggestions = ["Continue with the uploaded resume", "I'll upload a different resume"]
    elif session.stage == Stage.DONE:
        suggestions = ["What are the next steps?", "Tell me about the hiring process"]
    elif session.stage == Stage.AWAIT_RESUME:
        suggestions = []
    elif session._detail_role:
        suggestions = [f"Apply for {session._detail_role}", "See other roles"]
    elif session._listed_roles:
        suggestions = ["See other roles", "I'd like to apply"]
    elif session.stage == Stage.CHATTING:
        suggestions = ["Show open roles", "I'd like to apply"]

    session.ui_role_cards = []
    session.ui_suggestions = suggestions


def start_application(session: Session, role_title: str) -> str:
    """Apply / View-Apply shortcut: upload if needed, otherwise screen the stored resume."""
    _reset_turn_ui(session)
    _set_intended_role(session, role_title)
    title = session.intended_role or role_title
    session.history.append({"role": "user", "content": f"I'd like to apply for the {title} role."})

    if session.candidate_profile:
        evaluation = evaluate_profile(session, title)
        session.last_evaluation = evaluation
        reply = narrate_match(session, evaluation)
        build_ui_hints(session)
        return reply

    session.stage = Stage.AWAIT_RESUME
    reply = (
        f"Great — let's get your application started for **{title}**. "
        "Please upload your resume as a PDF or .txt file and I'll screen it against this role."
    )
    session.history.append({"role": "assistant", "content": reply})
    build_ui_hints(session)
    return reply


def preview_role(session: Session, role_title: str) -> str:
    """Show the seeded full JD without waiting on a tool-calling loop."""
    _reset_turn_ui(session)
    role = get_role(role_title)
    if not role:
        reply = f"I couldn't find a role matching '{role_title}'. Would you like to see our open positions?"
        session.history.append({"role": "user", "content": f"Show the job description for {role_title}"})
        session.history.append({"role": "assistant", "content": reply})
        session._listed_roles = True
        build_ui_hints(session)
        return reply

    session._detail_role = role["title"]
    reply = format_job_description(role) + "\n\nWould you like to apply for this role?"
    session.history.append({"role": "user", "content": f"Show the full job description for {role['title']}"})
    session.history.append({"role": "assistant", "content": reply})
    build_ui_hints(session)
    return reply


def _set_intended_role(session: Session, title: str | None) -> str | None:
    title = (title or "").strip()
    if not title:
        return session.intended_role
    role = get_role(title)
    session.intended_role = role["title"] if role else title
    return session.intended_role


def evaluate_profile(session: Session, role_title: str | None = None) -> dict:
    """Score the stored resume against all roles; update session + DB."""
    _set_intended_role(session, role_title)
    profile = session.candidate_profile or {}
    all_matches = score_all_roles(profile.get("skills", []), profile.get("experience_years") or 0)
    session.all_matches = all_matches

    intended = session.intended_role
    primary = next((m for m in all_matches if m["role"] == intended), None)
    if primary is None:
        primary = all_matches[0] if all_matches else {}
    session.match_result = primary

    alternatives = [
        m for m in all_matches
        if m.get("qualifies") and m.get("role") != primary.get("role")
    ]

    if intended:
        if primary.get("qualifies"):
            if intended not in session.applied_roles:
                session.applied_roles.append(intended)
            if intended in session.rejected_roles:
                session.rejected_roles.remove(intended)
            session.stage = Stage.AWAIT_CONTACT_CONFIRM
        else:
            if intended not in session.rejected_roles:
                session.rejected_roles.append(intended)
            session.stage = Stage.CHATTING

    if session.candidate_id is not None:
        update_candidate_match(session.candidate_id, primary)
    else:
        session.candidate_id = save_candidate(profile, primary)

    return {
        "applied_role": intended,
        "primary": primary,
        "alternative_matches": alternatives,
        "all_matches": all_matches,
        "profile": profile,
    }


def narrate_match(session: Session, evaluation: dict) -> str:
    primary = evaluation.get("primary") or {}
    alternatives = evaluation.get("alternative_matches") or []
    applied = evaluation.get("applied_role")
    qualifies = bool(primary.get("qualifies"))

    if qualifies:
        instructions = (
            f"They applied for {applied} and QUALIFY. Summarize name/email/phone/experience/"
            f"education from the profile only. Cite matched_skills. Then ask if Conversive.ai may "
            f"contact them. Do not list other openings unless they ask."
        )
    elif alternatives:
        titles = ", ".join(m["role"] for m in alternatives)
        instructions = (
            f"They applied for {applied} and do NOT qualify. Cite missing_skills for that role. "
            f"Then say this resume is a better fit for: {titles}. Show ONLY those matching "
            f"opening(s) from alternative_matches (title + why they match). Ask if they want to "
            f"apply for that role / those roles. Do NOT list unmatched openings. Do NOT ask "
            f"contact permission yet."
        )
    else:
        instructions = (
            f"They applied for {applied} and do NOT qualify for it or any other current opening. "
            f"Say they were not selected this time. Do not promise recruiter contact. "
            f"Do not list open roles. Offer to answer questions about the hiring process."
        )

    summary = (
        f"[SYSTEM: Resume screening complete. Profile: {json.dumps(evaluation.get('profile'))}. "
        f"Primary match: {json.dumps(primary)}. "
        f"alternative_matches (TRUE matches only): {json.dumps(alternatives)}. "
        f"{instructions}]"
    )
    session.history.append({"role": "user", "content": summary})

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=900,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=session.history,
    )
    session.history.append({"role": "assistant", "content": response.content})
    text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    return "\n".join(text_blocks).strip() or "I've reviewed your resume against that role."


def inject_resume_result(session: Session, profile: dict, filename: str | None = None) -> str:
    _reset_turn_ui(session)
    session.candidate_profile = profile
    if filename:
        session.resume_filename = filename
    evaluation = evaluate_profile(session)
    session.last_evaluation = evaluation
    reply = narrate_match(session, evaluation)
    build_ui_hints(session)
    return reply


def _execute_tool(name: str, tool_input: dict, session: Session) -> dict:
    if name == "list_job_roles":
        session._listed_roles = True
        return {"roles": list_roles()}

    if name == "get_role_details":
        title = tool_input.get("role_title", "")
        role = get_role(title)
        if role:
            session._detail_role = role["title"]
        return {"role": role} if role else {"error": f"No role found matching '{title}'"}

    if name == "request_resume_upload":
        _set_intended_role(session, tool_input.get("role_title"))
        if session.candidate_profile:
            session.stage = Stage.AWAIT_RESUME_CHOICE
            return {
                "status": "choose_resume",
                "role": session.intended_role,
                "resume_filename": session.resume_filename,
                "instruction": (
                    "A resume is already on file. Ask the user whether to continue with it "
                    "or upload a different PDF or .txt file. If they continue, call reuse_uploaded_resume."
                ),
            }
        session.stage = Stage.AWAIT_RESUME
        return {"status": "upload_requested", "role": session.intended_role}

    if name == "reuse_uploaded_resume":
        if not session.candidate_profile:
            return {"error": "No resume is on file yet. Ask them to upload a PDF or .txt file."}
        evaluation = evaluate_profile(session, tool_input.get("role_title"))
        session.last_evaluation = evaluation
        session.pending_reply = narrate_match(session, evaluation)
        return {
            "status": "evaluated",
            "applied_role": evaluation["applied_role"],
            "primary": evaluation["primary"],
            "alternative_matches": evaluation["alternative_matches"],
        }

    if name == "record_contact_preference":
        agrees = tool_input.get("agrees_to_contact", False)
        session.stage = Stage.DONE
        if session.candidate_id is not None:
            update_candidate_contact_preference(session.candidate_id, agrees)
        return {"status": "recorded", "agrees_to_contact": agrees}

    return {"error": f"Unknown tool {name}"}


def handle_message(session: Session, user_text: str) -> str:
    _reset_turn_ui(session)
    session.history.append({"role": "user", "content": user_text})

    for _ in range(6):
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=session.history,
        )
        session.history.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            build_ui_hints(session)
            return "\n".join(text_blocks).strip()

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool(block.name, block.input, session)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )
                if session.pending_reply:
                    session.history.append({"role": "user", "content": tool_results})
                    reply = session.pending_reply
                    session.pending_reply = None
                    build_ui_hints(session)
                    return reply
        session.history.append({"role": "user", "content": tool_results})

    build_ui_hints(session)
    return "Sorry — I hit a snag processing that. Could you try again?"
