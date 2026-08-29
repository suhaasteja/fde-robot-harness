"""ask_agent — let the robot delegate work to a TrueForge agent.

This is the robot -> TrueForge direction. The robot keeps the voice loop; a
TrueForge agent does the heavy work using whatever connectors it has attached
(Qodo AI for code review, Bright Data for scraping, and so on), and the robot
speaks the answer back.

The other direction lives in `bin/robot-mcp`, which exposes the robot itself as
an MCP server so TrueForge agents can move it. Both can be active at once.

Loaded via the app's external-tools mechanism:

    REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY=/Users/mac/Desktop/fde-robot-harness/tools
    AUTOLOAD_EXTERNAL_TOOLS=true
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import httpx

from reachy_mini_conversation_app.tools.core_tools import Tool, ToolDependencies

logger = logging.getLogger(__name__)

TRUEFORGE_URL = os.getenv("TRUEFORGE_BASE_URL", "http://localhost:8790").rstrip("/")
DEFAULT_AGENT = os.getenv("TRUEFORGE_DEFAULT_AGENT", "")

# Every delegation lands in ONE TrueForge session, so the UI shows a single
# continuous thread of what the robot asked for — with each tool call, its
# arguments, and its result rendered by the agent-steps panel. A new session per
# call would scatter that across dozens of one-turn threads.
#
# Reusing the session also chains turns (previous_turn_id defaults to "auto"),
# so the agent remembers earlier delegations in the same conversation.
SESSION_FILE = Path(
    os.getenv(
        "TRUEFORGE_SESSION_FILE",
        Path(__file__).resolve().parent.parent / ".run" / "trueforge_session",
    )
)

# ...but not forever. Turns chain, so the thread's context grows with every
# delegation. Left unbounded it eventually trips TrueForge's compaction, which
# spends a model call to summarize and quietly loses detail, and the sidebar row
# becomes an unnavigable wall titled after whatever was asked first.
#
# Rotating keeps each thread cheap to run and readable after the fact. Age is the
# primary trigger (a working session is a natural unit); the turn cap is a
# backstop for a very busy day.
SESSION_TTL_HOURS = float(os.getenv("TRUEFORGE_SESSION_TTL_HOURS", "12"))
SESSION_MAX_TURNS = int(os.getenv("TRUEFORGE_SESSION_MAX_TURNS", "40"))

# Spoken conversation cannot tolerate a long silence, so cap the wait and return
# a partial status rather than leaving the user staring at a mute robot.
TURN_TIMEOUT = float(os.getenv("TRUEFORGE_TURN_TIMEOUT", "45"))
POLL_INTERVAL = 1.5


def _token_headers() -> Dict[str, str]:
    """Bearer header only when the server has OIDC login on; local mode needs none."""
    token = os.getenv("TRUEFORGE_TOKEN", "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


async def _should_rotate(
    client: httpx.AsyncClient, headers: Dict[str, str], session: dict
) -> str:
    """Return a reason to rotate, or "" to keep using this session."""
    created = str(session.get("created_at", ""))
    if created:
        try:
            started = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - started).total_seconds() / 3600
            if age_h >= SESSION_TTL_HOURS:
                return f"age {age_h:.1f}h >= {SESSION_TTL_HOURS}h"
        except ValueError:
            pass  # unparseable timestamp is not a reason to throw the session away

    r = await client.get(
        f"{TRUEFORGE_URL}/api/v1/sessions/{session['id']}/turns", headers=headers
    )
    if r.status_code == 200:
        n = len(r.json().get("data", []))
        if n >= SESSION_MAX_TURNS:
            return f"{n} turns >= {SESSION_MAX_TURNS}"
    return ""


async def _resolve_session(
    client: httpx.AsyncClient, headers: Dict[str, str], agent_name: str
) -> str:
    """Return the shared session id, rotating it when it gets old or long.

    The server is the source of truth: a stored id is verified before reuse, so a
    restarted TrueForge (or a deleted session) transparently gets a fresh one
    instead of failing every delegation.
    """
    stored = ""
    try:
        stored = SESSION_FILE.read_text().strip()
    except OSError:
        pass

    if stored:
        r = await client.get(f"{TRUEFORGE_URL}/api/v1/sessions/{stored}", headers=headers)
        if r.status_code == 200:
            reason = await _should_rotate(client, headers, r.json()["data"])
            if not reason:
                return stored
            logger.info("Rotating TrueForge session %s (%s).", stored, reason)
        else:
            logger.info("Stored TrueForge session %s is gone; opening a new one.", stored)

    r = await client.post(
        f"{TRUEFORGE_URL}/api/v1/sessions",
        headers=headers,
        json={"agent": {"name": agent_name}},
    )
    r.raise_for_status()
    session_id = r.json()["data"]["id"]

    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(session_id)
    except OSError as e:
        logger.warning("Could not persist TrueForge session id: %s", e)

    logger.info("Opened TrueForge session %s — view it at %s", session_id, TRUEFORGE_URL)
    return session_id


class AskAgent(Tool):
    """Delegate a question or task to a TrueForge agent."""

    name = "ask_agent"
    description = (
        "Delegate a research, code-review, scraping, or analysis task to a TrueForge "
        "agent that has tools you do not. Use this whenever the user asks for something "
        "requiring the web, a codebase, or an external system — not for chit-chat or "
        "for moving your own body. Answers take several seconds, so say you are working "
        "on it before calling. Returns the agent's written answer for you to summarize "
        "aloud; keep the spoken version to a few sentences."
    )
    needs_response = True
    parameters_schema = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": (
                    "The full task for the agent, phrased as you would to a capable "
                    "colleague. Include any specifics the user gave — URLs, repo names, "
                    "constraints — since the agent cannot hear the conversation."
                ),
            },
            "context": {
                "type": "string",
                "description": (
                    "Optional. What the user said in their own words, plus any relevant "
                    "background from the conversation so far. The agent cannot hear the "
                    "conversation, so this is the only way it learns what led to the "
                    "request — and it is what shows up in the TrueForge UI, making the "
                    "delegation readable later. Two or three sentences is plenty."
                ),
            },
            "agent": {
                "type": "string",
                "description": (
                    "Optional named TrueForge agent to use. Omit to use the default. "
                    "Only pass a name the user explicitly asked for."
                ),
            },
        },
        "required": ["question"],
    }

    async def __call__(self, deps: ToolDependencies, **kwargs: Any) -> Dict[str, Any]:
        """Open a TrueForge session, run one turn, and return the agent's reply."""
        question = kwargs.get("question")
        if not isinstance(question, str) or not question.strip():
            return {"error": "question must be a non-empty string"}

        agent_name = (kwargs.get("agent") or DEFAULT_AGENT or "").strip()
        if not agent_name:
            return {
                "error": "no_agent_configured",
                "spoken": (
                    "I don't have a TrueForge agent configured yet, so I can't delegate that."
                ),
            }

        logger.info("Tool call: ask_agent agent=%r question=%r", agent_name, question[:120])
        headers = {"Content-Type": "application/json", **_token_headers()}

        # Spoken context first, so the TrueForge thread reads as a conversation
        # rather than a bare instruction with no provenance.
        context = kwargs.get("context")
        message = question
        if isinstance(context, str) and context.strip():
            message = f"Spoken context: {context.strip()}\n\nTask: {question}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    session_id = await _resolve_session(client, headers, agent_name)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        return {
                            "error": "agent_not_found",
                            "spoken": f"There's no TrueForge agent called {agent_name}.",
                        }
                    raise

                # stream=false: take the turn id now and poll. The SSE stream is
                # richer, but a voice turn only needs the final text, and polling
                # keeps this resilient to a dropped connection mid-answer.
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
                while waited < TURN_TIMEOUT:
                    await asyncio.sleep(POLL_INTERVAL)
                    waited += POLL_INTERVAL
                    t = await client.get(
                        f"{TRUEFORGE_URL}/api/v1/sessions/{session_id}/turns/{turn_id}",
                        headers=headers,
                    )
                    t.raise_for_status()
                    state = t.json()["data"]["state"]
                    status = state.get("status")

                    if status == "done":
                        # A "done" turn carrying requiredActions is paused, not
                        # finished -- it wants an approval or an MCP login that
                        # nobody can give it from a voice conversation.
                        if state.get("requiredActions") or state.get("required_actions"):
                            return {
                                "status": "needs_attention",
                                "spoken": (
                                    "The agent needs approval before it can continue. "
                                    "Check the TrueForge window."
                                ),
                            }
                        answer = (state.get("output") or {}).get("content") or ""
                        return {
                            "status": "done",
                            "answer": answer or "The agent finished but returned nothing.",
                        }

                    if status in ("failed", "cancelled"):
                        return {
                            "status": status,
                            "spoken": f"The agent {status}.",
                            "detail": str(state.get("error"))[:300],
                        }

                return {
                    "status": "still_running",
                    "session_id": session_id,
                    "spoken": (
                        "The agent is still working. I'll keep going and you can check "
                        "TrueForge for the full answer."
                    ),
                }

        except httpx.ConnectError:
            return {
                "error": "trueforge_unreachable",
                "spoken": "I can't reach TrueForge right now.",
                "detail": f"No server at {TRUEFORGE_URL}",
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("ask_agent failed")
            return {
                "error": type(e).__name__,
                "spoken": "Something went wrong asking the agent.",
                "detail": str(e)[:300],
            }
