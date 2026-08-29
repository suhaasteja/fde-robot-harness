# Physical SOC — Demo Runbook

**Reachy Mini as the human-in-the-loop for automated CVE remediation.**

A vulnerability lands. TrueForge writes and sandbox-tests the patch. Reachy physically
stops the room and demands a human's approval out loud before anything merges.

---

## The problem we're demoing against

Scanners find CVEs. Bots open patch PRs. Both of those are solved.

What isn't solved: the patch sits in a PR, the notification lands in a Slack channel with
40 other notifications, and the CRITICAL fix ships four days later — or worse, gets
rubber-stamped by someone who never read the diff.

Approval has no *weight*. We give it weight by making it physical.

---

## Architecture

```
  Bright Data                TrueForge (:8790)              Reachy Mini
  ───────────                ─────────────────              ───────────
  CVE feeds        ──┐                                   ┌─ speaks the alert
  vendor advisories  ├──►  agent session                 │  (antennae + head turn)
  breach forums      │     ├─ scan dependencies          │
  release notes    ──┘     ├─ write patch  ┐             │
                           ├─ run tests    ├─ sandbox    │
                           └─ subagent audit┘            │
                                  │                       │
                                  ▼                       │
                        HUMAN APPROVAL CHECKPOINT ◄───────┘
                                  │                    spoken confirmation
                                  │                    parsed from app.log
                                  ▼
                            Qodo review  ──►  merge to main
```

Data flows one way until the checkpoint. Nothing merges without a voice from the room.

---

## Component map

| Piece | Port | Status | Where |
|---|---|---|---|
| Reachy daemon | 8000 | **built** (Control app) | volume, mic, test sound |
| Conversation app | 7860 | **built** | `bin/reachy-app start --ui` |
| Control panel | 7870 | **built** | `bin/control-panel` — prompt, transcript, memory |
| TrueForge agent server | 8790 | **built** (upstream) | `npx @truefoundry/trueforge` |
| Bright Data MCP | — | **to build** | register into TrueForge |
| `bin/soc-watch` | — | **to build** | poll TrueForge → drive Reachy |
| Approval parser | — | **to build** | tail `logs/app.log` for the phrase |
| Qodo gate | — | **to build** | PR review before merge |

The four "to build" rows are the demo's actual work. Everything else already runs.

---

## Pre-flight (do this 10 minutes before, not on stage)

```bash
make doctor          # pins: SDK 1.9.0, conversation app 0.10.0, daemon reachable
```

All four checks green or you are debugging in front of judges. Then:

```bash
# 1. Reachy Mini Control app must be open — it owns the daemon on :8000
open -a "Reachy Mini Control"

# 2. Conversation app, UI enabled (the --ui flag is what exposes the prompt API)
make start -- --ui

# 3. Control panel
make panel                        # http://127.0.0.1:7870

# 4. TrueForge
npx @truefoundry/trueforge        # http://localhost:8790
```

Confirm in the panel header: `daemon up` and `app connected` both green. If `app UI off`,
you started without `--ui` — `bin/reachy-app restart --ui`.

**Load the SOC personality** in the panel's System prompt box before the demo starts, so
Reachy is already in character:

> You are the physical security officer for this team. When you are given a CVE briefing,
> state the CVE ID, the severity, and the one-sentence blast radius. Then ask for verbal
> approval by name. Do not approve anything yourself. If the human says anything other
> than a clear approval, treat it as a hold.

Save as `soc-officer`, hit **Save & apply** — it applies live, no restart.

---

## The run (target: 4 minutes)

### Beat 1 — the feed is live (0:00–0:45) · *Bright Data track*

Show the terminal, not a slide.

```bash
bin/soc-watch --once --verbose
```

Bright Data pulls fresh CVE intel through TrueForge's MCP registration:

```bash
curl -s localhost:8790/api/v1/settings/mcp-servers \
  -H 'content-type: application/json' \
  -d '{"name":"brightdata","command":"npx","args":["@brightdata/mcp"]}'
```

**The money shot for this track is resilience.** Have a second source whose layout you've
deliberately broken. Show the scraper failing, the agent noticing the selector no longer
matches, rewriting it, and re-fetching — all inside the terminal. Auto-repair is the
judging criterion; a feed that merely works is table stakes.

### Beat 2 — the agent does the work (0:45–2:00) · *DGX Spark track*

A CRITICAL lands. TrueForge opens a session and goes:

```bash
curl -s localhost:8790/api/v1/sessions/$SID/turns \
  -H 'content-type: application/json' \
  -d '{"input":"CVE-XXXX-XXXXX in the dependency tree. Patch, test, audit."}'
```

Narrate what scrolls past — these are the three things the track rewards:

1. **Sandbox** — patch script written and executed in TrueForge's sandboxed executor,
   not on the host. Test suite runs there. Show a green result.
2. **Subagents** — a fan-out that audits every service file touching the vulnerable
   symbol. Show two or three returning independently.
3. **Held at the gate** — the session pauses on a human approval checkpoint. Nothing has
   merged. Say that out loud: *"it's done, and it's stuck."*

### Beat 3 — Reachy takes the room (2:00–3:15) · **the differentiator**

`bin/soc-watch` sees the pending checkpoint and drives the robot: antennae up, head turns
to the lead dev, and it speaks:

> "CRITICAL. CVE-XXXX-XXXXX. Remote code execution in the request parser — every
> inbound endpoint. Patch is written and tests pass. Aahan, do you approve the merge?"

Then it waits. Let the silence sit — three seconds of a robot staring at a person is the
entire pitch, and rushing past it wastes the only moment nobody else in the bracket has.

The human answers out loud. `bin/soc-watch` tails `logs/app.log`, which already parses
into clean turns (`read_transcript()` in `bin/control-panel` joins the realtime backend's
partial fragments and lets the final line win), matches the approval phrase, and releases
TrueForge's checkpoint.

**Do the negative case first if you have the time.** Say *"no, hold it"* — show the merge
stay blocked — then approve. A gate that only ever says yes isn't a gate, and one judge
will always ask.

### Beat 4 — the patch lands (3:15–4:00)

Qodo reviews the generated diff for regressions, then it merges. Show the panel's
transcript pane: the full exchange is sitting there, timestamped — an audit trail of who
approved what, by voice, at what second.

Close on that. *"Every CRITICAL patch this system ships has a human's voice attached to it."*

---

## Track coverage

| | DGX Spark (TrueForge) | AirPods 4 (Bright Data) |
|---|---|---|
| **Requirement** | Sandbox, human-in-the-loop, subagents | Resilient live web pipeline in the terminal |
| **Where it lands** | Beat 2 (sandbox + fan-out), Beat 3 (Reachy *is* the checkpoint) | Beat 1 (multi-source feed, self-repairing scraper) |
| **The unfair part** | The approval is physical, not a Slack button | Break the layout on purpose, repair it live |

Both tracks are load-bearing in the same four minutes — neither is bolted on.

Embed the Bright Data commands in the project rules file (`CODEX.md` / `.cursor/rules`)
so the pipeline is part of the repo's standing instructions, not a one-off invocation.
Judges check for that.

---

## When it breaks

| Symptom | Cause | Fix |
|---|---|---|
| Prompt editor greyed out | app started without `--ui` | `bin/reachy-app restart --ui` |
| `daemon down` | Control app closed | reopen it; daemon owns :8000 |
| App dies instantly on start | conda's glib shadowing GStreamer | already handled — `cmd_start` scrubs conda from PATH |
| Robot greets the wrong name | stale saved facts | panel → **Clear saved facts** (backs up to `.json.bak`) |
| Robot won't stop | backgrounded app ignores SIGINT | `make stop` (SIGTERM → KILL), never Ctrl-C |
| Approval never registers | log line didn't match the phrase | keep a `--force-approve` flag on `bin/soc-watch` |

**Have a recorded 30-second fallback clip of Beat 3.** Live robot audio in a loud venue is
the single most likely thing to fail, and it's the beat you cannot afford to lose.

---

## Build order

1. `bin/soc-watch` — poll TrueForge for pending checkpoints, tail `logs/app.log` for the
   approval phrase, release or hold. This is the spine; build it first.
2. Bright Data MCP registered into TrueForge + the deliberately-broken second source.
3. `soc-officer` personality, tuned against a real CVE briefing until the phrasing lands.
4. Qodo gate on the generated diff.
5. `--force-approve` and the fallback recording. Not optional.

Rehearse Beat 3 more than the rest combined.
