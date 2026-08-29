"""Voice approval bridge for the existing Reachy conversation loop.

The conversation app already owns listening and transcription. This tool gives
that loop one tightly-scoped way to pass an exact spoken approval to the
existing TrueForge/Qodo gate; it never merges code itself.
"""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict

from reachy_mini_conversation_app.tools.core_tools import Tool, ToolDependencies


ROOT = Path(__file__).resolve().parent.parent
MONITOR_STATE = ROOT / ".run" / "cve-monitor.json"
VOICE_DECISION = ROOT / ".run" / "reachy-approval.json"


def _active_incident() -> dict:
    try:
        state = json.loads(MONITOR_STATE.read_text())
    except (OSError, ValueError):
        return {}
    incidents = state.get("incidents") or {}
    ready = [row for row in incidents.values() if row.get("status") == "approval_ready"]
    return max(ready, key=lambda row: row.get("checked_at", ""), default={})


def _write_decision(value: dict) -> None:
    VOICE_DECISION.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="reachy-approval-", suffix=".json", dir=VOICE_DECISION.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle)
            handle.write("\n")
        os.replace(name, VOICE_DECISION)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


class ApproveCommit(Tool):
    """Record an exact, spoken approval for the currently waiting incident."""

    name = "approve_commit"
    description = (
        "Use only when the user explicitly says 'I approve commit' followed by a commit "
        "SHA. Pass their complete words verbatim. This records the voice decision for the "
        "currently waiting TrueForge security incident. Never infer approval from yes, go "
        "ahead, sounds good, or an SHA without the exact approval words."
    )
    needs_response = True
    parameters_schema = {
        "type": "object",
        "properties": {
            "words": {
                "type": "string",
                "description": "The user's complete approval sentence, verbatim.",
            }
        },
        "required": ["words"],
    }

    async def __call__(self, deps: ToolDependencies, **kwargs: Any) -> Dict[str, Any]:
        words = str(kwargs.get("words") or "").strip()
        incident = _active_incident()
        if not incident:
            return {"status": "locked", "spoken": "There is no verified commit awaiting approval."}
        sha = str(incident.get("sha") or "")
        short = sha[:7]
        normalized = " ".join(words.lower().split())
        exact = re.search(
            rf"\bi approve commit\s+{re.escape(short.lower())}(?![0-9a-f])", normalized
        )
        if not exact:
            return {
                "status": "ambiguous",
                "spoken": f"Approval was not recorded. Please say: I approve commit {short}.",
            }
        _write_decision({
            "decision": "approved", "words": words, "sha": sha,
            "cve": incident.get("cve"), "pr_url": incident.get("pr_url"),
        })
        return {
            "status": "recorded",
            "spoken": f"Approval recorded for commit {short}. TrueForge is completing the merge gate.",
        }
