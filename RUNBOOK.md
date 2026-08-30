# Physical SOC — demo runbook

Everything runs on one machine, from the repo root. If something is closed by
mistake, jump to [Restarting a service](#restarting-a-service).

```bash
cd ~/Desktop/fde-robot-harness
```

---

## The services

| # | Service | Port | Command | Needed for |
|---|---|---|---|---|
| 1 | daemon | 8000 | `~/reachy-conv/bin/reachy-mini-daemon` | motion, audio device |
| 2 | conversation app | 7860 | `~/reachy-conv/bin/reachy-mini-conversation-app --ui` | the robot's voice and ears |
| 3 | robot-mcp | 7880 | `~/reachy-conv/bin/python bin/robot-mcp` | agents controlling the robot |
| 4 | TrueForge | 8790 | `npx @truefoundry/trueforge@latest` | the agents |
| 5 | codebase-mcp | 7881 | `~/reachy-conv/bin/python bin/codebase-mcp` | agents searching our code |
| 6 | control panel | 7870 | `bin/control-panel` | optional — transcript, volume |

Order matters for 1 and 2: the app checks for the daemon once at startup and will
not notice one appearing later. **Always start the app from the repo root**, or it
will not find `.env` and will silently use the free Hugging Face backend.

Check everything at once:

```bash
bin/demo check
```

---

## Demo A — conversational (30 seconds, no pipeline)

The lightweight opener. Nothing to reset, nothing to wait for.

**Say:** *"Is our code vulnerable right now?"*

The robot narrates that it is checking, then answers with the CVE, severity, and
a one-line reason. Read-only — it assesses, it never patches.

**Say:** *"What are the latest critical CVEs this week?"*

Live web via Bright Data, through the `robot-operator` agent.

---

## Demo B — the full incident (about 8 minutes)

### 1. Reset — always, before every rehearsal

```bash
bin/demo reset
```

The fixture is one-shot. Once the pipeline patches it there is nothing left to
find, and the next scan correctly returns `VERDICT: NONE`. Reset restores the
vulnerable file and clears run state. Expect `# pass 1 / # fail 1` — the failing
security test *is* the vulnerability.

### 2. Preflight

```bash
bin/demo check
```

All lines green. The two that matter most:

- **robot serial device present** — if this warns, the daemon is in `--mockup-sim`
  and the robot will speak but never move.
- **/say route present** — if this fails, every announcement comes from the
  laptop's speakers while still reporting success.

### 3. Scan — the robot works out loud (~4 min)

```bash
bin/demo scan
```

Expect roughly, in its own voice:

> *"I'll check public disclosures and the fixture before deciding applicability."*
> *"I'm asking a second analyst to review exposure and regression coverage."*
> *"Approval checkpoint reached for CVE-2025-29927, patch identifier `<sha>`."*

Behind that: Bright Data finds the advisory, the agent patches in TrueForge's
sandbox, tests go from 1/2 to 2/2, two subagents report, a branch is pushed and a
PR opened, and Qodo is asked to review. The agent then **stops** at a native
approval checkpoint rather than declaring itself done.

### 4. Gate — wait for Qodo, then speak

```bash
bin/demo gate
```

Four prerequisites. `qodo_followup` is the slow one — Qodo takes a few minutes and
must review the **exact head SHA**; a stale review on an older commit will not do.

When approval turns `waiting`, say out loud:

> **"I approve commit `<sha>`"**

Use the exact seven-character SHA from the robot's announcement.

### 5. Show that it holds

Worth demonstrating, because it is the whole point:

| Say | Result |
|---|---|
| "yes go ahead" | ambiguous → **stays locked** |
| "sounds good, ship it" | ambiguous → **stays locked** |
| "I approve commit deadbee" | wrong SHA → **stays locked** |
| "no, hold the merge" | **denied** |
| "I approve commit `<sha>`" | **approved** |

Only an explicit verb plus the exact SHA opens it. Silence holds.

### 6. Merge — only when you mean it

`bin/demo gate` never merges. To close the loop for real:

```bash
bin/soc-watch --session "$(python3 -c "import json;print(json.load(open('.run/cve-monitor.json'))['session_id'])")" \
              --pr <N> --merge
```

`--merge` is a real `gh pr merge --match-head-commit`. It can only merge the exact
approved and Qodo-reviewed commit.

---

## Restarting a service

Closed a terminal? Each is independent — restart just the one.

```bash
cd ~/Desktop/fde-robot-harness

# 1. daemon (add --mockup-sim --headless if the robot is unplugged)
~/reachy-conv/bin/reachy-mini-daemon

# 2. conversation app — MUST be from the repo root
~/reachy-conv/bin/reachy-mini-conversation-app --ui

# 3. robot-mcp
~/reachy-conv/bin/python bin/robot-mcp

# 3b. codebase-mcp (searchable view of demo-fixture)
~/reachy-conv/bin/python bin/codebase-mcp

# 4. TrueForge
npx @truefoundry/trueforge@latest

# 5. control panel (optional)
bin/control-panel
```

Then `bin/demo check`.

**If you restart the daemon, restart the app too** — it binds to the daemon at
startup and will not reconnect on its own.

**Restart the app after editing anything in `tools/`.** Python caches imported
modules, so the edit is silently ignored by a running app.

---

## When something is wrong

| Symptom | Cause | Fix |
|---|---|---|
| Voice comes from the Mac, not the robot | `/say` route missing | `bin/patch-app`, restart the app |
| Robot speaks but never moves | daemon in `--mockup-sim` | restart the daemon without that flag |
| Robot does not respond to you | mic muted, or app not running | `bin/demo check` |
| Scan says `VERDICT: NONE` | fixture already patched | `bin/demo reset` |
| Approval stuck at `locked` | Qodo has not reviewed the head SHA | wait; check the PR |
| App on the wrong backend | started outside the repo root | restart from repo root |
| A service looks down but works | it may bind IPv6-only | probe `localhost`, not `127.0.0.1` |

After **any** reinstall of the conversation app, re-run `bin/setup` — installing
overwrites `console.py` and removes `/say` with no other symptom.

---

## Watching it happen

- **TrueForge** — `http://localhost:8790`, or the exact thread from `bin/demo status`.
  Expand *Agent steps* for each tool call, its arguments, and its result.
- **Control panel** — `http://127.0.0.1:7870`. The **Agent** tab follows the live
  thread automatically, so you never hunt for the new session.
- **Transcript in the panel** needs the app piped:
  `~/reachy-conv/bin/reachy-mini-conversation-app --ui 2>&1 | tee -a logs/app.log`
