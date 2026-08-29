# Integrating the robot into an existing TrueForge setup

For someone who already runs TrueForge with their own connectors (Qodo, GitHub, a
codebase) and wants the Reachy Mini available to those agents.

**You do not need any code from this repo.** The robot is an MCP connector. You
register a URL and attach it to agents you already have.

Assumes TrueForge is local (`npx`, port `8790`) on the **same machine as the
robot** — `bin/robot-mcp` binds to loopback. If TrueForge ever moves, start it
with `--host 0.0.0.0` and use the host's real address.

---

## 1. Bring the robot up

```bash
git clone https://github.com/suhaasteja/fde-robot-harness
cd fde-robot-harness
bin/setup                      # venv + pinned versions + /say patch + .env
# put your OPENAI_API_KEY in .env
```

Three processes, three terminals:

```bash
~/reachy-conv/bin/reachy-mini-daemon                    # :8000  hardware
~/reachy-conv/bin/reachy-mini-conversation-app --ui     # :7860  voice  (from repo root)
~/reachy-conv/bin/python bin/robot-mcp                  # :7880  MCP server
```

The app **must** run from the repo root or it will not find `.env` and will
silently fall back to the free Hugging Face backend. Confirm on startup:

```
Configured backend provider: openai (OpenAI Realtime), model: gpt-realtime-mini
```

Sanity check before touching TrueForge:

```bash
curl -s localhost:8000/api/volume/current      # daemon alive
curl -s localhost:7860/openapi.json | grep -o '"/say"'   # patch applied
```

If `/say` is missing, run `bin/patch-app` and restart the app.

---

## 2. Register the robot as a connector

```bash
curl -X POST http://localhost:8790/api/v1/settings/mcp-servers \
  -H 'Content-Type: application/json' \
  -d '{"manifest":{
        "name":"reachy-mini",
        "type":"remote",
        "url":"http://127.0.0.1:7880/mcp",
        "description":"Control a Reachy Mini desk robot: motion, recorded emotions, speech, face tracking."}}'
```

Expect `201` and `"auth_status":{"status":"not_required"}`.

---

## 3. Attach it to your agent

```json
"mcp_servers": [
  {"name": "reachy-mini", "preload": true, "preload_tools": ["say", "robot_status"]},
  {"name": "qodo"},
  {"name": "github"}
]
```

Update with `PUT /api/v1/agents/{agent_id}` — **by id, not name**. Get the id from
`GET /api/v1/agents`. (`POST /api/v1/agents` takes `{name, manifest}`.)

---

## The three things that will silently not work

None of these produce a useful error. Each cost us a debugging round.

### 1. Preload `say`, or the agent will never speak

TrueForge uses deferred tool loading: an agent sees only tool **names** and must
call `get_tool_info` before it can use one. A tool the model never expands is
effectively invisible — and **instructing it to "call say" does not fix this.** We
put the rule in the system prompt, confirmed it was stored, and the agent still
never called it.

`"preload": true, "preload_tools": ["say", "robot_status"]` is the fix.

Leave your other connectors deferred — preloading a large server's whole tool list
bloats every prompt, which is what deferred loading is for. Preload the few tools
you want reached reflexively.

### 2. Use a capable model

`gpt-5-4-mini` could not hold the narration rules. It skipped announcements
entirely on multi-step tasks, and when it did speak it parroted the literal
example phrasing out of the instructions while actually doing something else.
`gpt-5-5` follows them reliably.

### 3. Keep spoken lines short

A 90-word announcement is 40+ seconds of speech. It gets interrupted, and when it
is, it is lost. There is a hard 45-word cap in our instructions and an explicit
rule never to read a list aloud — pick the most notable item and offer to go
deeper. Both are load-bearing, not style.

---

## Instructions to copy

`trueforge/robot-operator.agent.json` is a working spec. Copy its "Speaking out
loud" block. The shape that works:

- **Before slow work** — one line under fifteen words, naming the actual source.
- **On spawning a subagent** — one line. These are the long silences worth covering.
- **On failure** — say so rather than going quiet.
- **With the answer** — under 45 words, self-contained: answer first, then the
  source in plain words (never tool names like `call_tool` or `scrape_as_markdown`).

Trigger them off a marker in the task text. Ours is a `Spoken context:` prefix,
added by `tools/ask_agent.py` on every delegation, which tells the agent a person
is physically waiting.

---

## The tools

| Tool | Signature |
|---|---|
| `robot_status` | — |
| `say` | `text, verbatim?` |
| `wake_up` / `go_to_sleep` | — |
| `look` | `yaw_degrees?, pitch_degrees?, roll_degrees?, body_yaw_degrees?, duration_seconds?` |
| `set_antennas` | `left_degrees?, right_degrees?, duration_seconds?` |
| `stop_moving` | — |
| `list_moves` | `dataset?` — `"emotions"` (85) or `"dances"` |
| `play_move` | `move_name, dataset?` |
| `list_sounds` / `play_sound` | `filename` |
| `set_volume` | `level` 0–100 |
| `face_tracking` | `enabled` |
| `detected_face` | — |

Notes that matter at the boundary:

- **Angles are degrees.** The daemon wants radians; `robot-mcp` converts. Sensible
  ranges: yaw ±60, pitch ±30, roll ±25, antennas ±90.
- **`say` returns `ok:true` for _queued_, not spoken.** It is not proof of audio.
- **`play_sound` plays files only** — there is no TTS in the daemon. Use `say`.
- **`list_moves` before `play_move`.** Don't guess names.
- **`set_volume` reads back ±1** — macOS quantises to 16 steps. Not a bug.
- **Movement is real.** Agents default to
  `require_approval_for_tools: ["@write","@destructive"]`, so movement pauses for
  approval in the chat UI. That default is deliberate.

---

## Optional: let the robot call *your* agents

The reverse direction. `tools/ask_agent.py` is loaded by the conversation app and
delegates to a named TrueForge agent, so anything that agent reaches — Qodo,
GitHub, your codebase, subagents — becomes reachable by voice.

```bash
TRUEFORGE_BASE_URL=http://localhost:8790
TRUEFORGE_DEFAULT_AGENT=<your-agent-name>
```

Behaviour worth knowing:

- All delegations share **one TrueForge session**, so the UI shows a single
  readable thread with every tool call. It rotates after 12h or 40 turns.
- It gives up waiting after 45s and tells the user "still working" — **but the
  answer still arrives by voice later**, because `say` does not depend on that
  round trip. One broad question ran 41 tool calls and several minutes.
- The robot loops the `waiting` emotion while a delegation runs, so a slow turn
  does not look like a crash. `REACHY_BUSY_MOTION=0` disables it.

---

## When something is silent

| Symptom | Cause |
|---|---|
| `say` returns `say_not_available` | `/say` patch missing. Run `bin/patch-app`, restart the app. |
| Agent never calls `say` | Not preloaded (see above), or the model is too small. |
| `ok:true` but no audio | The line was too long, or a barge-in flushed it. Shorten it. |
| Robot silent, everything "healthy" | Realtime socket can go stale while reporting connected. Restart the app. |
| Tools work, robot does not move | Approval gate — check the TrueForge chat for a pending prompt. |
| App on the wrong backend | Started outside the repo root, so `.env` was not found. |

After **any** reinstall or upgrade of the conversation app, re-run `bin/setup` —
installing overwrites `console.py` and removes the `/say` route with no other
symptom.
