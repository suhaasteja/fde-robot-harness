"""check_codebase — ask the robot, out loud, whether our own code is vulnerable.

The scheduled pipeline (bin/cve-monitor) already does this on a timer, but it is
the only thing that does. This gives the conversation loop the same capability on
demand, so "is our code vulnerable right now?" is answerable in a sentence rather
than by waiting for the next scan.

It is deliberately read-only: it asks the physical-soc agent to assess, and never
patches, commits, or opens a PR. Remediation stays with cve-monitor, where the
approval gate lives.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict

import httpx

from reachy_mini_conversation_app.tools.core_tools import Tool, ToolDependencies

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
TRUEFORGE_URL = os.getenv("TRUEFORGE_BASE_URL", "http://localhost:8790").rstrip("/")
SOC_AGENT = os.getenv("TRUEFORGE_SOC_AGENT", "physical-soc")
TARGET = Path(os.getenv("CVE_TARGET_PATH", ROOT / "demo-fixture"))

# A spoken question cannot wait minutes. A full scan takes far longer than this,
# so the cap is deliberately short and the tool reports honestly when it expires.
TIMEOUT = float(os.getenv("CHECK_CODEBASE_TIMEOUT", "90"))
POLL = 2.0
SNAPSHOT_LIMIT = 40_000


def _snapshot(target: Path) -> str:
    """Bounded, secret-safe view of the codebase, same shape cve-monitor sends."""
    if not target.exists():
        return ""
    preferred = {
        "package.json", "requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml",
    }
    chunks: list[str] = []
    used = 0
    for path in sorted(target.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.name.startswith(".env"):
            continue
        if path.name not in preferred and path.suffix not in {".js", ".ts", ".py", ".go", ".rs"}:
            continue
        try:
            content = path.read_text(errors="replace")
        except OSError:
            continue
        block = f"\n--- {path.relative_to(target)} ---\n{content}\n"
        if used + len(block) > SNAPSHOT_LIMIT:
            break
        chunks.append(block)
        used += len(block)
    return "".join(chunks)


class CheckCodebase(Tool):
    """Assess our own repository for known vulnerabilities, on request."""

    name = "check_codebase"
    description = (
        "Check whether OUR OWN codebase is currently affected by any known public "
        "vulnerability. Use this when the user asks about our code, our repo, our "
        "service, or whether we are vulnerable or exposed — not for general security "
        "news, which ask_agent handles. Read-only: it assesses and reports, it never "
        "patches or opens a pull request. Takes up to a minute and a half, so say you "
        "are checking before calling. Summarize the result in two or three sentences."
    )
    needs_response = True
    parameters_schema = {
        "type": "object",
        "properties": {
            "focus": {
                "type": "string",
                "description": (
                    "Optional. A specific worry to concentrate on — a CVE id, a "
                    "dependency, or an area like authentication. Omit for a general check."
                ),
            }
        },
        "required": [],
    }

    async def __call__(self, deps: ToolDependencies, **kwargs: Any) -> Dict[str, Any]:
        """Ask the SOC agent to assess the configured codebase."""
        snapshot = _snapshot(TARGET)
        if not snapshot:
            return {
                "error": "no_codebase",
                "spoken": f"I couldn't read the codebase at {TARGET.name}.",
            }

        focus = kwargs.get("focus")
        focus_line = (
            f"\nConcentrate on: {focus.strip()}\n"
            if isinstance(focus, str) and focus.strip()
            else "\n"
        )
        message = (
            "Spoken context: someone is standing here asking, out loud, whether our own "
            "code is vulnerable right now. Answer conversationally.\n\n"
            "Task: assess the codebase below against known public vulnerabilities. Use "
            "Bright Data to confirm anything you suspect against an authoritative source; "
            "do not invent a match. This is a READ-ONLY assessment — do not patch, do not "
            "commit, do not open a pull request, and do not ask for approval.\n"
            "Reply in two or three sentences: whether anything applies, the CVE id and "
            "severity if so, and the one-line reason. If nothing applies, say so plainly."
            f"{focus_line}\nCODEBASE:\n{snapshot}"
        )

        headers = {"Content-Type": "application/json"}
        token = os.getenv("TRUEFORGE_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{TRUEFORGE_URL}/api/v1/sessions",
                    headers=headers,
                    json={"agent": {"name": SOC_AGENT}},
                )
                if r.status_code == 404:
                    return {
                        "error": "agent_not_found",
                        "spoken": f"There's no TrueForge agent called {SOC_AGENT}.",
                    }
                r.raise_for_status()
                session_id = r.json()["data"]["id"]

                r = await client.post(
                    f"{TRUEFORGE_URL}/api/v1/sessions/{session_id}/turns",
                    headers=headers,
                    json={
                        "input": [{"type": "user.message", "content": message}],
                        "stream": False,
                    },
                )
                r.raise_for_status()
                turn_id = r.json()["data"]["id"]

                waited = 0.0
                while waited < TIMEOUT:
                    await asyncio.sleep(POLL)
                    waited += POLL
                    t = await client.get(
                        f"{TRUEFORGE_URL}/api/v1/sessions/{session_id}/turns/{turn_id}",
                        headers=headers,
                    )
                    t.raise_for_status()
                    state = t.json()["data"]["state"]
                    status = state.get("status")

                    if status == "done":
                        answer = (state.get("output") or {}).get("content") or ""
                        if not answer:
                            # A turn paused at a checkpoint has no final output; its
                            # text lives in the messages. Should not happen here since
                            # we forbid asking for approval, but degrade gracefully.
                            ev = await client.get(
                                f"{TRUEFORGE_URL}/api/v1/sessions/{session_id}/events",
                                headers=headers,
                            )
                            rows = ev.json().get("data", []) if ev.status_code == 200 else []
                            answer = "\n".join(
                                row["event"]["content"]
                                for row in rows
                                if (row.get("event") or {}).get("type") == "model.message"
                                and isinstance((row.get("event") or {}).get("content"), str)
                            )
                        return {
                            "status": "done",
                            "codebase": TARGET.name,
                            "answer": answer or "The assessment returned nothing.",
                            "session": f"{TRUEFORGE_URL}/sessions/{session_id}",
                        }

                    if status in ("failed", "cancelled"):
                        return {"status": status, "spoken": f"The assessment {status}."}

                return {
                    "status": "still_running",
                    "spoken": (
                        "Still checking the codebase — that one is taking a while. "
                        "The full result will be in TrueForge."
                    ),
                    "session": f"{TRUEFORGE_URL}/sessions/{session_id}",
                }

        except httpx.ConnectError:
            return {
                "error": "trueforge_unreachable",
                "spoken": "I can't reach TrueForge right now.",
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("check_codebase failed")
            return {
                "error": type(e).__name__,
                "spoken": "Something went wrong checking the codebase.",
                "detail": str(e)[:300],
            }
