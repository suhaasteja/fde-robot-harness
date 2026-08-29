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
   both connectors.

Or by API — see the git log for `807e6d6`, which has the exact `curl` calls. Note
`POST /api/v1/agents` takes `{name, manifest}`, and **updates are by `agent_id`,
not name**.

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
  That is the timeout, not a broken integration.
- **Editing anything in `tools/` needs an app restart.** Python caches imported
  modules, so a running app silently keeps using the old code — the edit looks
  like it did nothing.
- **The app's API prefix moved between releases** — v0.8.0 serves
  `/personalities` at the root, v0.10.0 used `/api/v1`. `bin/control-panel` probes
  for it.

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
