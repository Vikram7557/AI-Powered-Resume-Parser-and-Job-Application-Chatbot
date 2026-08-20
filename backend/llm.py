"""
LLM client: OpenRouter (Claude) first, Google Gemini as fallback.

chatbot.py and resume_parser.py keep using client.messages.create(...) with
Anthropic-style tools/history. Gemini responses are adapted to the same shape.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

from anthropic import APIConnectionError, APIStatusError, Anthropic, RateLimitError

from config import (
    APP_TITLE,
    APP_URL,
    GEMINI_API_KEYS,
    GEMINI_MODEL,
    MODEL_NAME,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)

_openrouter = Anthropic(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    default_headers={
        "HTTP-Referer": APP_URL,
        "X-Title": APP_TITLE,
    },
)

def _get_gemini_model(api_key: str, system: str | None, tools: list | None):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    kwargs = {"model_name": GEMINI_MODEL}
    if system:
        kwargs["system_instruction"] = system
    gemini_tools = _anthropic_tools_to_gemini(tools or [])
    if gemini_tools:
        kwargs["tools"] = gemini_tools
    return genai.GenerativeModel(**kwargs)


def _gemini_should_rotate(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in (
            "resource_exhausted",
            "quota",
            "rate limit",
            "429",
            "403",
            "401",
            "permission_denied",
            "invalid api key",
            "api key not valid",
            "exceeded",
            "insufficient",
        )
    )


def _should_fallback(exc: BaseException) -> bool:
    if isinstance(exc, TypeError):
        return True
    if isinstance(exc, (APIConnectionError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        code = getattr(exc, "status_code", None)
        if code in {401, 402, 403, 429, 500, 502, 503, 529}:
            return True
        body = str(exc).lower()
        if any(token in body for token in ("billing", "credits", "payment_required", "afford")):
            return True
    text = str(exc).lower()
    return any(token in text for token in ("billing", "credits", "payment_required", "402"))


class AttrDict(dict):
    """JSON-serializable content block that still supports block.type / block.text."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _text_block(text: str):
    return AttrDict(type="text", text=text or "")


def _tool_block(name: str, tool_input: dict, tool_id: str | None = None):
    return AttrDict(
        type="tool_use",
        id=tool_id or f"call_{name}_{uuid.uuid4().hex[:8]}",
        name=name,
        input=tool_input or {},
    )


def _block_type(block) -> str | None:
    if isinstance(block, dict):
        return block.get("type")
    return getattr(block, "type", None)


def _block_attr(block, name, default=None):
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def _anthropic_tools_to_gemini(tools: list) -> list:
    if not tools:
        return []
    decls = []
    for tool in tools:
        schema = dict(tool.get("input_schema") or {"type": "object", "properties": {}})
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        decls.append(
            {
                "name": tool["name"],
                "description": tool.get("description") or "",
                "parameters": schema,
            }
        )
    return [{"function_declarations": decls}]


def _tool_name_index(messages: list[dict]) -> dict[str, str]:
    names = {}
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        blocks = content if isinstance(content, list) else [content]
        for block in blocks:
            if _block_type(block) == "tool_use":
                names[_block_attr(block, "id")] = _block_attr(block, "name")
    return names


def _parse_tool_payload(raw):
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {"result": raw}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"result": raw}
    return parsed if isinstance(parsed, dict) else {"result": parsed}


def _history_to_gemini(messages: list[dict]) -> list[dict]:
    tool_names = _tool_name_index(messages)
    contents = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            if isinstance(content, str):
                contents.append({"role": "user", "parts": [content]})
                continue
            parts = []
            for item in content or []:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    name = tool_names.get(item.get("tool_use_id"), "unknown")
                    payload = _parse_tool_payload(item.get("content"))
                    parts.append({"function_response": {"name": name, "response": payload}})
                elif isinstance(item, str):
                    parts.append(item)
                else:
                    parts.append(str(item))
            if parts:
                contents.append({"role": "user", "parts": parts})
        elif role == "assistant":
            parts = []
            blocks = content if isinstance(content, list) else [content]
            for block in blocks:
                btype = _block_type(block)
                if btype == "text":
                    text = _block_attr(block, "text") or ""
                    if text:
                        parts.append(text)
                elif btype == "tool_use":
                    parts.append(
                        {
                            "function_call": {
                                "name": _block_attr(block, "name"),
                                "args": dict(_block_attr(block, "input") or {}),
                            }
                        }
                    )
                elif isinstance(block, str) and block:
                    parts.append(block)
            if parts:
                contents.append({"role": "model", "parts": parts})
    return contents


def _function_call_args(fc) -> dict:
    args = getattr(fc, "args", None)
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    try:
        return {k: args[k] for k in args}
    except Exception:
        return dict(args)


def _gemini_to_anthropic(response) -> SimpleNamespace:
    content = []
    used_tool = False
    candidates = getattr(response, "candidates", None) or []
    parts = []
    if candidates:
        parts = getattr(getattr(candidates[0], "content", None), "parts", None) or []
    for part in parts:
        fc = getattr(part, "function_call", None)
        if fc and getattr(fc, "name", None):
            used_tool = True
            content.append(_tool_block(fc.name, _function_call_args(fc)))
            continue
        text = getattr(part, "text", None)
        if text:
            content.append(_text_block(text))
    if not content:
        text = getattr(response, "text", None) or ""
        content.append(_text_block(text))
    return SimpleNamespace(
        content=content,
        stop_reason="tool_use" if used_tool else "end_turn",
    )


def _content_block_to_dict(block) -> dict:
    if isinstance(block, dict):
        return dict(block)
    if hasattr(block, "model_dump"):
        data = block.model_dump()
        return data if isinstance(data, dict) else {"type": "text", "text": str(block)}
    btype = getattr(block, "type", None)
    if btype == "text":
        return {"type": "text", "text": getattr(block, "text", "") or ""}
    if btype == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", "") or "",
            "name": getattr(block, "name", "") or "",
            "input": getattr(block, "input", None) or {},
        }
    if btype == "tool_result":
        return {
            "type": "tool_result",
            "tool_use_id": getattr(block, "tool_use_id", "") or "",
            "content": getattr(block, "content", "") or "",
        }
    return {"type": "text", "text": str(block)}


def _messages_for_openrouter(messages: list | None) -> list[dict]:
    """Both Gemini AttrDict blocks and Anthropic SDK objects must be plain JSON."""
    out = []
    for msg in messages or []:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(content, str):
            out.append({"role": role, "content": content})
        elif isinstance(content, list):
            out.append({"role": role, "content": [_content_block_to_dict(b) for b in content]})
        else:
            out.append({"role": role, "content": _content_block_to_dict(content)})
    return out


def _create_gemini(*, max_tokens: int, system=None, tools=None, messages=None, json_mode: bool = False):
    if not GEMINI_API_KEYS:
        raise RuntimeError(
            "OpenRouter failed and no Gemini keys are set. "
            "Add GEMINI_API_KEY, GEMINI_API_KEY_2, ... in backend/.env."
        )

    import google.generativeai as genai

    contents = _history_to_gemini(messages or [])
    if not contents:
        contents = [{"role": "user", "parts": ["Hello"]}]

    last_error: Exception | None = None
    for index, api_key in enumerate(GEMINI_API_KEYS, start=1):
        try:
            model = _get_gemini_model(api_key, system, tools)
            gen_cfg = {"max_output_tokens": max_tokens}
            if json_mode:
                gen_cfg["response_mime_type"] = "application/json"
            response = model.generate_content(
                contents,
                generation_config=genai.GenerationConfig(**gen_cfg),
            )
            if index > 1:
                print(f"Gemini key {index} succeeded.")
            return _gemini_to_anthropic(response)
        except Exception as exc:
            last_error = exc
            if index < len(GEMINI_API_KEYS) and _gemini_should_rotate(exc):
                print(f"Gemini key {index} failed; trying key {index + 1}.")
                continue
            if index < len(GEMINI_API_KEYS):
                # Schema/request bugs won't be fixed by another key — still try next
                # only for quota-like errors; otherwise raise.
                raise
            break

    raise RuntimeError(
        f"All {len(GEMINI_API_KEYS)} Gemini key(s) failed. Add more keys or wait for quota reset."
    ) from last_error


class _Messages:
    def create(self, *, model=None, max_tokens=1000, system=None, tools=None, messages=None, json_mode=False):
        global _last_provider, _last_model_label
        try:
            kwargs = {
                "model": model or MODEL_NAME,
                "max_tokens": max_tokens,
                "messages": _messages_for_openrouter(messages or []),
            }
            if system is not None:
                kwargs["system"] = system
            if tools is not None:
                kwargs["tools"] = tools
            result = _openrouter.messages.create(**kwargs)
            _last_provider = "openrouter"
            _last_model_label = _pretty_claude_label(model or MODEL_NAME)
            return result
        except Exception as exc:
            if not _should_fallback(exc):
                raise
            print(f"OpenRouter failed ({exc.__class__.__name__}); falling back to Gemini.")
            try:
                result = _create_gemini(
                    max_tokens=max_tokens,
                    system=system,
                    tools=tools,
                    messages=messages,
                    json_mode=json_mode,
                )
                _last_provider = "gemini"
                _last_model_label = _pretty_gemini_label(GEMINI_MODEL)
                return result
            except Exception as gemini_exc:
                raise RuntimeError(
                    "OpenRouter failed and every Gemini fallback key failed. "
                    "Add GEMINI_API_KEY / GEMINI_API_KEY_2 in backend/.env."
                ) from gemini_exc


class _Client:
    messages = _Messages()


client = _Client()

_last_provider = "openrouter"
_last_model_label = "Claude"


def _pretty_claude_label(model_id: str) -> str:
    name = (model_id or "").split("/")[-1].replace("-", " ").strip()
    if "claude" in name.lower():
        return "Claude"
    return name.title() or "Claude"


def _pretty_gemini_label(model_id: str) -> str:
    name = (model_id or "").replace("-", " ").strip()
    if "gemini" in name.lower():
        return "Gemini"
    return name.title() or "Gemini"


def last_llm_info() -> dict:
    return {
        "provider": _last_provider,
        "model_label": _last_model_label,
    }
