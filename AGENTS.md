# fde-robot-harness

Runs a **Reachy Mini** desk robot with an OpenAI Realtime voice loop, and wires it
into **TrueForge** in both directions.

This file is for whoever (human or agent) picks the repo up next. Read the
[Rules](#rules-read-before-changing-anything) before changing versions or config —
several settings here look wrong and are deliberate.

## What this is

| Piece | Where | Purpose |
|---|---|---|
| `reachy-mini-daemon` | venv, port `8000` | Talks to the robot hardware. Everything else is a client of it. |
| `reachy-mini-conversation-app` | venv, port `7860` | The voice loop. Pinned to **v0.8.0**. |
| `bin/robot-mcp` | port `7880` | Exposes the robot as an MCP server → TrueForge agents can move it. |
| `bin/control-panel` | port `7870` | Local UI: system prompt, transcript, volume, saved memory. |
| `tools/ask_agent.py` | loaded by the app | Lets the robot delegate to a TrueForge agent → reaches its connectors. |
| TrueForge | port `8790` | Agent harness (`npx @truefoundry/trueforge@latest`). |

Two directions, both working:

```
TrueForge agent ──MCP :7880──> robot        (agents move the robot)
robot ──ask_agent──> TrueForge :8790        (voice reaches Bright Data, Qodo, ...)
```

## Setup

**Prerequisites:** macOS, Homebrew Python 3.12, Node ≥ 22.14, and a venv at
`~/reachy-conv`. The robot itself is **optional** — see [Without a robot](#without-a-robot).

If `~/reachy-conv` does not exist:

```bash
/opt/homebrew/bin/python3.12 -m venv ~/reachy-conv
uv pip install --python ~/reachy-conv/bin/python \
  "reachy-mini<1.10" \
  "reachy_mini_conversation_app @ git+https://github.com/pollen-robotics/reachy_mini_conversation_app.git@v0.8.0"
```

Expect `reachy-mini 1.9.0` and `reachy-mini-conversation-app 0.8.0`. Anything else
means the pin drifted — see the Rules.

**`.env` is not committed** (it holds an API key). Create it in the repo root:

```bash
BACKEND_PROVIDER=openai
MODEL_NAME=gpt-realtime-mini
OPENAI_API_KEY=sk-...

# Stops a forgotten session billing all night. Upstream default is 1440 (24h).
REACHY_MINI_APP_TIMEOUT_MINUTES=15

# Robot -> TrueForge
REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY=/absolute/path/to/fde-robot-harness/tools
AUTOLOAD_EXTERNAL_TOOLS=true
TRUEFORGE_BASE_URL=http://localhost:8790
TRUEFORGE_DEFAULT_AGENT=robot-operator
```

## Running it

Use the plain upstream commands. `make` targets exist but the maintainer prefers
these — do not phrase instructions in terms of the wrappers.

```bash
# 1. daemon (own terminal). No flags: defaults wake the robot up.
~/reachy-conv/bin/reachy-mini-daemon

# 2. voice app — MUST be run from the repo root so .env is found
cd /path/to/fde-robot-harness
~/reachy-conv/bin/reachy-mini-conversation-app --ui

# 3. optional
npx @truefoundry/trueforge@latest        # :8790
~/reachy-conv/bin/python bin/robot-mcp   # :7880
bin/control-panel --port 7870
```

Daemon **first** — the app checks for it once at startup and won't notice one
appearing later. Stop with `Ctrl-C`, or `kill -TERM <pid>` from another shell.

Confirm the backend on startup:

```
Configured backend provider: openai (OpenAI Realtime), model: gpt-realtime-mini
✓ Loaded external tool: ask_agent
```

If the first line is missing you are in the wrong directory and silently on the
free Hugging Face backend.

## Without a robot

Most of the stack works unplugged, which is enough to develop everything except
actual motion:

```bash
~/reachy-conv/bin/reachy-mini-daemon --mockup-sim --headless
```

| Works | Does not |
|---|---|
| TrueForge, agents, connectors | Physical movement |
| `bin/robot-mcp` + all 13 tools (return simulated/None state) | Audio in/out (`No Reachy Mini Audio USB device found` — expected) |
| Control panel: transcript, saved memory | Volume (needs the robot's audio device) |
| `tools/ask_agent.py` end to end | The voice loop as an actual conversation |

The voice app will start and connect to OpenAI without a robot, but with no mic
or speaker it is not useful — develop against TrueForge and the MCP server instead.

## TrueForge setup

Nothing here is committed (it lives in TrueForge's own SQLite DB), so a fresh
instance needs:

1. **Model provider** — Settings → Models → OpenAI, paste the key.
2. **Connectors** — Settings → Connectors. Add the robot as a custom MCP server at
   `http://127.0.0.1:7880/mcp` (no auth). Add Bright Data / Qodo via the UI, since
   OAuth needs the browser flow.
3. **Agent** — name it `robot-operator` (matches `TRUEFORGE_DEFAULT_AGENT`), attach
   both connectors, and **preload the `say` tool** (see below).

### Preload `say`, or the robot stays silent

TrueForge uses [deferred tool loading](https://trueforge.dev/key-features/deferred-tool-loading):
an agent sees only tool *names* and must call `get_tool_info` then `call_tool` to
use one. A tool the model never bothers to expand is effectively invisible —
instructing it to "call say" is not enough on its own, which cost a debugging
round to discover.

Preload it explicitly:

```json
"mcp_servers": [
  {"name": "reachy-mini", "preload": true, "preload_tools": ["say", "robot_status"]},
  {"name": "bright-data"}
]
```

Leave `bright-data` deferred — it has many tools and preloading them all would
bloat every prompt. That is the tradeoff deferred loading exists for: preload the
few tools you want reached reflexively, defer the long tail.

The instructions then tell it *when* to speak: before slow work, when it spawns a
subagent, when the answer lands, and if something fails — never per tool call, which
is unbearable to listen to.

**Use `gpt-5-5`, not `gpt-5-4-mini`, for this agent.** The mini model could not hold
the narration rules: it skipped announcements, and when it did speak it parroted the
literal example phrasing from the instructions ("Checking the robot now.") while
actually searching the web. `gpt-5-5` follows them reliably and writes fresh lines.
That is a real cost difference per turn — but narration is the whole point of the
robot knowing what it is doing, and the mini model cannot deliver it.

Verified on a two-subagent task: 13 tool calls produced exactly 3 spoken lines —
"I'll check Hacker News and Lobste.rs now.", "I'm sending two researchers to check
both sites in parallel.", "Hacker News has the more technical top story today."

Or by API — see the git log for `807e6d6`, which has the exact `curl` calls. Note
`POST /api/v1/agents` takes `{name, manifest}`, and **updates are by `agent_id`,
not name**.

## Integrating with another TrueForge setup

If you already run TrueForge with your own connectors (Qodo, a codebase, subagents),
**you do not need any of this repo's code**. The robot is just another MCP
connector. Point your TrueForge at it and attach it to any agent you already have.

### What this repo exposes

| Surface | Where | Needs |
|---|---|---|
| Robot as an MCP server — 14 tools | `http://127.0.0.1:7880/mcp` | `bin/robot-mcp` + daemon |
| `POST /say` — make the robot speak | `http://127.0.0.1:7860/say` | `bin/patch-app` + the app running `--ui` |

Tools: `robot_status`, `wake_up`, `go_to_sleep`, `look`, `set_antennas`,
`stop_moving`, `list_moves`, `play_move`, `list_sounds`, `play_sound`,
`set_volume`, `say`, `face_tracking`, `detected_face`.

### Adding the robot to your agents

```bash
curl -X POST http://<your-trueforge>/api/v1/settings/mcp-servers \
  -H 'Content-Type: application/json' -d '{"manifest":{
    "name":"reachy-mini","type":"remote",
    "url":"http://127.0.0.1:7880/mcp",
    "description":"Control a Reachy Mini desk robot: motion, emotions, speech."}}'
```

Then on any agent — including one that already has Qodo and your codebase:

```json
"mcp_servers": [
  {"name": "reachy-mini", "preload": true, "preload_tools": ["say", "robot_status"]},
  {"name": "qodo"},
  {"name": "your-codebase"}
]
```

**Preload `say` or your agent will never speak.** TrueForge defers tool loading:
agents see only tool *names* and must call `get_tool_info` first. A tool the model
never expands is invisible, and no amount of instruction fixes it. This cost us a
debugging round — see [Preload `say`](#preload-say-or-the-robot-stays-silent).

Then tell the agent *when* to speak. The working rules are in
`trueforge/robot-operator.agent.json` — copy the "Speaking out loud" block. The
parts that matter: a hard 45-word cap per spoken line, never read a list aloud,
and announce at start / on subagent spawn / on failure / with the result.

**Use a capable model.** `gpt-5-4-mini` could not hold these rules — it skipped
announcements and parroted example phrasing from the prompt while doing something
else. `gpt-5-5` is reliable.

### Calling your agents from the robot

The reverse direction is `tools/ask_agent.py`. Point it at your agent:

```bash
TRUEFORGE_BASE_URL=http://<your-trueforge>
TRUEFORGE_DEFAULT_AGENT=<your-agent-name>
```

Anything that agent can reach — Qodo, your codebase, your subagents — is then
reachable by voice, with no change to this repo.

### What actually needs the robot

Only motion, audio and volume. Your agents, connectors, `ask_agent`, and the whole
MCP surface work against `--mockup-sim` with no hardware — see
[Without a robot](#without-a-robot). Someone can integrate and test the entire
software path before the robot is ever plugged in.

### Contract notes

- Angles are **degrees** at the MCP boundary; the daemon wants radians and
  `robot-mcp` converts. Do not send radians.
- `say` returns `ok:true` for **queued**, not spoken. It is not proof of audio.
- Long spoken lines get lost. Keep them short; the 45-word cap is not cosmetic.
- Movement is real. The default `require_approval_for_tools: ["@write","@destructive"]`
  gate is deliberate — an agent that moves hardware unattended is a bad default.

## Rules (read before changing anything)

1. **Do not upgrade the conversation app.** v0.8.0 is the last release with
   multi-backend support. v0.9.0 (`5b8d974`, "consolidate around the default
   backend") removed it, and v0.9.0+ *ignore* `BACKEND_PROVIDER`/`MODEL_NAME` with
   a warning — you would silently lose OpenAI Realtime and land back on Hugging
   Face. There is an upstream regression test keeping it removed. **The app reads
   no YAML; there is no config file that restores it.**
2. **Do not upgrade the SDK past 1.9.x.** Conversation app v1.x needs
   `reachy_mini.io.jsonrpc` (SDK ≥ 1.10), and the Reachy Mini Control app still
   bundles 1.9.0 for the daemon. Check the real gate with:
   `"$HOME/Library/Application Support/com.pollen-robotics.reachy-mini/.venv/bin/python3" -c "import importlib.metadata as m; print(m.version('reachy-mini'))"`
3. **Never `pip install` without a venv active.** The default shell sits in conda
   `base` and installs silently overwrite conda-managed packages. Always pass
   `--python ~/reachy-conv/bin/python`.
4. **Launch by absolute path.** Conda's glib predates 2.80 and shadows GStreamer's,
   giving `Symbol not found: _g_once_init_enter_pointer`.
5. **Never run two daemons.** They fight over `:8000` and the serial port.
6. **Keep the approval gate.** Agents default to
   `require_approval_for_tools: ["@write","@destructive"]`, so robot movement asks
   first. Loosening it lets an agent move real hardware unattended.

## Gotchas

- **SIGINT does nothing to a backgrounded app** — no controlling terminal. Verified:
  alive after 60s, nothing logged. Use `SIGTERM` (exits in ~1s). `Ctrl-C` only
  works in the foreground.
- **`pkill -f reachy-mini-conversation-app` also matches the shell wrapper**, so it
  can look like it worked while the real process lives on. Target the Python pid.
- **If `:7860` is taken, `--ui` starts anyway and silently serves no UI.** The bind
  error is buried in the log and reads as a broken control panel.
- **Volume reads back off by one** — macOS quantises to 16 steps. Not a bug.
- **The robot remembers things about you** across restarts, in
  `~/.local/share/reachy_mini_conversation_app/memory.v1.json`. It is injected into
  every session, so a stale nickname outlives restarts and personality changes.
  Clear it in the control panel.
- **`ask_agent` caps at 45s.** A deep crawl returns "still working", not an answer.
  That is the timeout, not a broken integration — and the spoken answer still
  arrives later, because `say` does not depend on the `ask_agent` round trip.
- **The robot plays the `waiting` emotion on a loop while a delegation runs**, so a
  slow turn does not look like a crash. Disable with `REACHY_BUSY_MOTION=0`, or
  swap the gesture with `REACHY_BUSY_MOVE=<emotion>` (`list_moves` for the 85
  available).
- **Editing anything in `tools/` needs an app restart.** Python caches imported
  modules, so a running app silently keeps using the old code — the edit looks
  like it did nothing.
- **The app's API prefix moved between releases** — v0.8.0 serves
  `/personalities` at the root, v0.10.0 used `/api/v1`. `bin/control-panel` probes
  for it.

## The /say patch

`bin/robot-mcp`'s `say` tool needs a `POST /say` route that upstream does not
ship. The app can already inject speech — that is how the startup greeting works
(`conversation.item.create` + `response.create`) — it just exposes no HTTP door.
`bin/patch-app` adds one:

```bash
bin/patch-app          # apply (idempotent)
bin/patch-app --check  # patched / unpatched
bin/patch-app --revert # restore the .orig backup
```

**Re-run it after any reinstall or version switch** — it edits the installed
package, so a reinstall silently reverts it and `say` starts returning
`say_not_available`. The script refuses to write anything that would not compile,
and keeps `console.py.orig` beside the file it edits.

Restart the app afterwards; Python caches imported modules.

```bash
curl -X POST http://127.0.0.1:7860/say -H 'Content-Type: application/json' \
  -d '{"text":"Search finished."}'                     # says it word for word
  -d '{"text":"Tell them it is done.","verbatim":false}' # phrases it itself
```

This matters beyond convenience: if a voice turn is interrupted, the app drops
the tool result (`_wait_for_response_done_before_tool_result` times out after 30s
and logs "Dropping realtime model result"), so the robot never speaks the answer
and you have to ask again. Pushing speech through `/say` sidesteps that entirely,
because it does not depend on the realtime response lifecycle.

## TrueForge sessions

Every `ask_agent` delegation lands in **one shared session**, so the UI shows a
single readable thread with each tool call, its arguments and its result — rather
than a new sidebar row per question. Turns chain, so the agent remembers earlier
delegations. The id lives in `.run/trueforge_session` (gitignored); delete it to
start a fresh thread.

That thread is rotated rather than grown forever, since chained turns make context
(and cost) creep up, and TrueForge's compaction would eventually spend a model call
summarizing it:

| Variable | Default | Trigger |
|---|---|---|
| `TRUEFORGE_SESSION_TTL_HOURS` | `12` | Session older than this |
| `TRUEFORGE_SESSION_MAX_TURNS` | `40` | Backstop for a very busy day |

Rotation is checked before each delegation, and a session that no longer exists
server-side (TrueForge restarted, thread deleted) transparently opens a new one.

## Costs

`gpt-realtime-mini` bills roughly **$0.006/min** listening and **$0.024/min**
speaking, and **an open session bills for the mic even in silence** (~$0.36/hr).
Stop the app when you are not using it; that is what the 15-minute timeout is for.
TrueForge agent turns bill separately on the same key.

## Recreating the agent

`trueforge/robot-operator.agent.json` is the exported spec — instructions,
connectors, preloads. TrueForge stores agents in its own database, so this file is
the only version-controlled copy. Restore it with:

```bash
curl -X POST http://localhost:8790/api/v1/agents \
  -H 'Content-Type: application/json' \
  -d @trueforge/robot-operator.agent.json
```

Updates go to `PUT /api/v1/agents/{agent_id}` — **by id, not name**. Get the id
from `GET /api/v1/agents`.
