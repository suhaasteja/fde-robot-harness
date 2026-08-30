# Architecture — as built

Everything runs on one machine. Six services, two entry points, one physical gate.

```
                         ┌───────────────────────┐
                         │        HUMAN          │
                         └──┬─────────────────▲──┘
                     speaks │                 │ hears
                         ┌──▼─────────────────┴──┐
                         │     REACHY MINI       │   real hardware
                         └──┬─────────────────▲──┘
                            │ USB serial      │ USB audio
        ┌───────────────────▼─────────────────┴────────────────────┐
        │  reachy-mini-daemon                               :8000  │
        │  /api/move  /api/media  /api/volume  /api/state          │
        └──▲──────────────────────▲───────────────────────▲────────┘
           │                      │                       │
   ┌───────┴────────┐   ┌─────────┴────────┐   ┌──────────┴────────┐
   │ conversation   │   │ bin/robot-mcp    │   │ bin/control-panel │
   │ app     :7860  │   │           :7880  │   │            :7870  │
   │ OpenAI Realtime│   │ 14 MCP tools     │   │ prompt·transcript │
   │                │   │  say, look,      │   │ volume·memory     │
   │  POST /say  ◄──┼───┤  play_move, …    │   │ Agent tab ──┐     │
   │  (bin/patch-app)│  └────────▲─────────┘   └─────────────┼─────┘
   │                │           │ MCP                        │ iframe
   │ external tools │           │                            │ follows
   │  ask_agent ────┼───────┐   │                            │ live thread
   │  check_codebase┼─────┐ │   │                            │
   │  approve_commit│     │ │   │                            │
   └────────────────┘     │ │   │                            │
                          │ │   │   ┌──────────────────┐     │
   ┌──────────────────┐   │ │   │   │ bin/codebase-mcp │     │
   │ bin/cve-monitor  │   │ │   │   │           :7881  │     │
   │ every 60s        │   │ │   │   │ search_code      │     │
   └────────┬─────────┘   │ │   │   │ read_file        │     │
            │             │ │   │   │ dependencies     │     │
            │ opens       │ │   │   └────────▲─────────┘     │
            │ session     │ │   │            │ MCP           │
            ▼             ▼ ▼   │            │               ▼
   ╔════════════════════════════┴════════════┴═══════════════════════╗
   ║  TrueForge                                               :8790  ║
   ║  agent loop · sandbox · subagents · sessions · approvals        ║
   ║                                                                 ║
   ║  ┌───────────────────────────┐  ┌────────────────────────────┐  ║
   ║  │ AGENT: physical-soc       │  │ AGENT: robot-operator      │  ║
   ║  │ gpt-5-5 · sandbox ✓       │  │ gpt-5-5 · sandbox ✗        │  ║
   ║  │ ├ reachy-mini  (preload)  │  │ ├ reachy-mini  (preload)   │  ║
   ║  │ ├ codebase     (preload)  │  │ └ bright-data  (deferred)  │  ║
   ║  │ └ bright-data  (deferred) │  │                            │  ║
   ║  │   └ subagents:            │  │  answers spoken questions  │  ║
   ║  │     blast radius,         │  │  about the live web        │  ║
   ║  │     regression audit      │  │                            │  ║
   ║  └────────────┬──────────────┘  └────────────────────────────┘  ║
   ╚═══════════════╪═════════════════════════════════════════════════╝
                   │ patch in sandbox · tests 1/2 → 2/2
                   ▼
          git worktree ──► branch ──► push ──► PR
                                                │
                                                ▼
                                     ┌────────────────────┐
                                     │  Qodo (GitHub App) │
                                     │  reviews HEAD SHA  │
                                     └─────────┬──────────┘
                                               │ gh api
                   ┌───────────────────────────▼──────────────────────┐
                   │  bin/soc-watch — enforce_gate()                  │
                   │   1  sandbox_tests        passed in TrueForge    │
                   │   2  qodo_followup        review on THIS head    │
                   │   3  trueforge_checkpoint agent paused for human │
                   │   4  commit_matches       every SHA agrees       │
                   │                                                  │
                   │   any one false  ──►  approval LOCKED            │
                   └───────────────────────────┬──────────────────────┘
                                               │ all four true
                                               ▼
                        ╔══════════════════════════════════════╗
                        ║  ROBOT SPEAKS  (say → :7860/say)     ║
                        ║  "CVE-…, critical. Do you approve    ║
                        ║   commit 6d12418?"                   ║
                        ╚═══════════════════╤══════════════════╝
                                            │ human voice
                                            ▼
                             tools/approve_commit.py
                    ┌───────────────────────────────────────┐
                    │ "I approve commit 6d12418"  → APPROVED│
                    │ "yes go ahead"              → hold    │
                    │ "sounds good, ship it"      → hold    │
                    │ "I approve commit deadbee"  → hold    │
                    │ "no, hold the merge"        → DENIED  │
                    │  silence                    → hold    │
                    └───────────────────┬───────────────────┘
                                        │ approved only
                                        ▼
                    gh pr merge --match-head-commit <sha>
                    (Git itself refuses any other commit)
```

## Services

| Port | Service | Ours? |
|---|---|---|
| 8000 | `reachy-mini-daemon` | upstream |
| 7860 | conversation app + `POST /say` | upstream v0.8.0 + our patch |
| 7870 | `bin/control-panel` | ours |
| 7880 | `bin/robot-mcp` — 14 robot tools | ours |
| 7881 | `bin/codebase-mcp` — 5 code-search tools | ours |
| 8790 | TrueForge | upstream |

## Two entry points

**Scheduled** — `bin/cve-monitor` opens a session on `physical-soc` every 60s.
Bright Data finds advisories, the codebase tools confirm applicability against our
actual code, the patch and tests run in TrueForge's sandbox, two subagents assess
blast radius and regression risk, a PR is opened, and Qodo reviews it.

**Conversational** — you speak. `ask_agent` reaches `robot-operator` for the live
web; `check_codebase` reaches `physical-soc` for a read-only assessment of our own
repository. Both narrate through `say` while they work.

They converge: whatever the source, nothing merges until a human says an explicit
approval with the exact commit SHA, out loud, to the robot.

## Why the gate is four conditions

Each removes a different way of being wrong:

- **sandbox_tests** — the patch actually fixes it, proven outside our machine
- **qodo_followup** — an independent reviewer agrees, on *this* commit; a stale
  review of an older SHA cannot unlock anything
- **trueforge_checkpoint** — the agent itself stopped and asked, rather than
  deciding it was finished
- **commit_matches** — the thing tested, reviewed, approved and merged are all
  the same commit

Everything fails closed. Ambiguity, silence, a wrong SHA, and a missing service
all leave the merge locked.
