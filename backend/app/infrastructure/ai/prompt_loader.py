"""Load and render prompt templates from the prompts/ directory."""

from __future__ import annotations

from pathlib import Path
from string import Template

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_SYSTEM_SEP = "---SYSTEM---"
_USER_SEP = "---USER---"


def _load_raw(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def _split(raw: str) -> tuple[str, str]:
    """Return (system_text, user_template) from a prompt file."""
    if _SYSTEM_SEP not in raw or _USER_SEP not in raw:
        raise ValueError("Prompt file must contain ---SYSTEM--- and ---USER--- sections")
    after_system = raw.split(_SYSTEM_SEP, 1)[1]
    system_part, user_part = after_system.split(_USER_SEP, 1)
    return system_part.strip(), user_part.strip()


def render(name: str, **variables: object) -> tuple[str, str]:
    """Return (system_instruction, user_message) with variables substituted."""
    raw = _load_raw(name)
    system, user_template = _split(raw)
    user_message = Template(user_template).safe_substitute(variables)
    return system, user_message
