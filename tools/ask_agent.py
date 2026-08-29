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
from typing import Any, Dict

import httpx

from reachy_mini_conversation_app.tools.core_tools import Tool, ToolDependencies

logger = logging.getLogger(__name__)

TRUEFORGE_URL = os.getenv("TRUEFORGE_BASE_URL", "http://localhost:8790").rstrip("/")
DEFAULT_AGENT = os.getenv("TRUEFORGE_DEFAULT_AGENT", "")

# Spoken conversation cannot tolerate a long silence, so cap the wait and return
# a partial status rather than leaving the user staring at a mute robot.
TURN_TIMEOUT = float(os.getenv("TRUEFORGE_TURN_TIMEOUT", "45"))
POLL_INTERVAL = 1.5


def _token_headers() -> Dict[str, str]:
    """Bearer header only when the server has OIDC login on; local mode needs none."""
    token = os.getenv("TRUEFORGE_TOKEN", "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


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

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{TRUEFORGE_URL}/api/v1/sessions",
                    headers=headers,
                    json={"agent": {"name": agent_name}},
                )
                if r.status_code == 404:
                    return {
                        "error": "agent_not_found",
                        "spoken": f"There's no TrueForge agent called {agent_name}.",
                    }
                r.raise_for_status()
                session_id = r.json()["data"]["id"]

                # stream=false: take the turn id now and poll. The SSE stream is
                # richer, but a voice turn only needs the final text, and polling
                # keeps this resilient to a dropped connection mid-answer.
                r = await client.post(
                    f"{TRUEFORGE_URL}/api/v1/sessions/{session_id}/turns",
                    headers=headers,
                    json={
                        "input": [{"type": "user.message", "content": question}],
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
