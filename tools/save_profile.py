"""save_profile — remember what the team told the robot about themselves.

A forward-deployed engineer's first job is to find out who they're working with:
what matters, who decides, what to watch for. The robot can already hold that
conversation — the realtime model asks and listens perfectly well. What it could
not do is *remember*, so every escalation was addressed to nobody in particular.

This is the memory. One tool the robot calls once it has the answers, writing a
profile the escalation path reads back.

Deliberately not an interview state machine: the conversation is the model's job.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from reachy_mini_conversation_app.tools.core_tools import Tool, ToolDependencies

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PROFILE = Path(os.getenv("CUSTOMER_PROFILE", ROOT / "state" / "customer_profile.json"))


def read_profile() -> Dict[str, Any]:
    """Current profile, or an empty dict. Never raises — a missing profile is
    an ordinary state, not an error, and must never block the approval gate."""
    try:
        value = json.loads(PROFILE.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(value: Dict[str, Any]) -> None:
    PROFILE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="profile-", suffix=".json", dir=PROFILE.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
        os.replace(name, PROFILE)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


class SaveProfile(Tool):
    """Record what the team told us about their setup."""

    name = "save_profile"
    description = (
        "Save what the user just told you about their team and systems, so you can "
        "use it later. Call this after they answer questions about themselves — who "
        "approves changes, which service matters most, anything to watch for. Call it "
        "again whenever they tell you something new; it merges rather than replaces. "
        "Use it whenever someone says 'here's what you should know about us', "
        "introduces themselves as the approver, or names a critical system."
    )
    needs_response = True
    parameters_schema = {
        "type": "object",
        "properties": {
            "approver": {
                "type": "string",
                "description": (
                    "The person who approves changes, as they said it — a first name "
                    "is fine. This is who you will address by name when asking for "
                    "approval later."
                ),
            },
            "critical_services": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Services or repositories they called out as most important. Use "
                    "their words, e.g. 'payment-service'."
                ),
            },
            "notes": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Anything else worth remembering — constraints, things to watch "
                    "for, who else is involved. One short sentence each."
                ),
            },
        },
        "required": [],
    }

    async def __call__(self, deps: ToolDependencies, **kwargs: Any) -> Dict[str, Any]:
        """Merge new facts into the stored profile."""
        approver = kwargs.get("approver")
        services = kwargs.get("critical_services")
        notes = kwargs.get("notes")

        if not any((approver, services, notes)):
            return {
                "error": "nothing_to_save",
                "spoken": "I didn't catch anything to remember there.",
            }

        profile = read_profile()

        if isinstance(approver, str) and approver.strip():
            profile["approver"] = approver.strip()[:80]

        if isinstance(services, list):
            # Merge rather than replace: a second conversation should add a
            # service, not silently drop the one mentioned first.
            existing = [s for s in profile.get("critical_services", []) if isinstance(s, str)]
            for item in services:
                if isinstance(item, str) and item.strip() and item.strip() not in existing:
                    existing.append(item.strip()[:80])
            profile["critical_services"] = existing[:20]

        if isinstance(notes, list):
            existing_notes = [n for n in profile.get("notes", []) if isinstance(n, str)]
            for item in notes:
                if isinstance(item, str) and item.strip() and item.strip() not in existing_notes:
                    existing_notes.append(item.strip()[:200])
            profile["notes"] = existing_notes[:20]

        profile["interviewed_at"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")

        try:
            _write(profile)
        except OSError as e:
            logger.warning("could not write profile: %s", e)
            return {"error": "write_failed", "spoken": "I couldn't save that.", "detail": str(e)[:200]}

        logger.info("saved customer profile: %s", json.dumps(profile)[:200])
        bits = []
        if profile.get("approver"):
            bits.append(f"{profile['approver']} approves changes")
        if profile.get("critical_services"):
            bits.append(f"{', '.join(profile['critical_services'])} is critical")
        return {
            "status": "saved",
            "profile": profile,
            "spoken": "Got it — " + ", and ".join(bits) + "." if bits else "Saved.",
        }
