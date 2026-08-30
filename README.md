# Physical SOC

**A robot that makes you say yes out loud before a security patch can merge.**

Scanners that find CVEs and bots that write patches are solved problems. The
approval step is not. A patch PR becomes one notification among forty, and it
either ships days late or gets rubber-stamped by someone who never read the diff.

Approval has no weight. We gave it weight by making it physical.

Every 60 seconds an agent finds newly disclosed CVEs on the live web, checks them
against the actual codebase, writes and sandbox-tests a patch, opens a pull
request, and waits for an independent code review. **Then it stops.** A Reachy
Mini turns to a person, states the CVE and its blast radius out loud, and asks for
approval by exact commit SHA. Nothing merges until a named human says so aloud.

---

## How it works

```
                         ┌───────────────────────┐
                         │        HUMAN          │
                         └──┬─────────────────▲──┘
                     speaks │                 │ hears
                         ┌──▼─────────────────┴──┐
                         │     REACHY MINI       │
                         └──┬─────────────────▲──┘
        ┌───────────────────▼─────────────────┴────────────────────┐
        │  reachy-mini-daemon                               :8000  │
        └──▲──────────────────────▲───────────────────────▲────────┘
           │                      │                       │
   ┌───────┴────────┐   ┌─────────┴────────┐   ┌──────────┴────────┐
   │ conversation   │   │ robot-mcp        │   │ control-panel     │
   │ app     :7860  │   │           :7880  │   │            :7870  │
   │ OpenAI Realtime│   │ 14 robot tools   │   │ prompt·transcript │
   │  POST /say  ◄──┼───┤  say, look,      │   │ volume·memory     │
   │                │   │  play_move, …    │   └───────────────────┘
   │ ask_agent      │   └────────▲─────────┘
   │ check_codebase │            │           ┌──────────────────┐
   │ approve_commit │            │           │ codebase-mcp     │
   └───────┬────────┘            │           │           :7881  │
           │                     │           │ search_code      │
   ┌───────┴──────────┐          │           │ read_file        │
   │ cve-monitor      │          │           │ dependencies     │
   │ every 60s        │          │           └────────▲─────────┘
   └───────┬──────────┘          │                    │
           ▼                     │                    │
   ╔═══════════════════════════════════════════════════════════════╗
   ║  TrueForge                                             :8790  ║
   ║  agent loop · sandbox · subagents · sessions · approvals      ║
   ║                                                               ║
   ║  ┌──────────────────────────┐  ┌───────────────────────────┐  ║
   ║  │ AGENT: physical-soc      │  │ AGENT: robot-operator     │  ║
   ║  │ gpt-5-5 · sandbox ✓      │  │ gpt-5-5 · sandbox ✗       │  ║
   ║  │ ├ reachy-mini (preload)  │  │ ├ reachy-mini (preload)   │  ║
   ║  │ ├ codebase    (preload)  │  │ └ bright-data (deferred)  │  ║
   ║  │ └ bright-data(deferred)  │  │                           │  ║
   ║  │   └ subagents: blast     │  │  answers spoken questions │  ║
   ║  │     radius, regression   │  │  about the live web       │  ║
   ║  └───────────┬──────────────┘  └───────────────────────────┘  ║
   ╚══════════════╪════════════════════════════════════════════════╝
                  │ patch in sandbox · tests 1/2 → 2/2
                  ▼
         git worktree ──► branch ──► push ──► PR
                                              │
                                              ▼
                                   ┌────────────────────┐
                                   │  Qodo (GitHub App) │
                                   │  reviews HEAD SHA  │
                                   └─────────┬──────────┘
                                             │
                 ┌───────────────────────────▼──────────────────────┐
                 │  soc-watch — enforce_gate()                      │
                 │   1  sandbox_tests        passed in TrueForge    │
                 │   2  qodo_followup        review on THIS head    │
                 │   3  trueforge_checkpoint agent paused for human │
                 │   4  commit_matches       every SHA agrees       │
                 │      any one false  ──►  approval LOCKED         │
                 └───────────────────────────┬──────────────────────┘
                                             │ all four true
                                             ▼
                      ╔══════════════════════════════════════╗
                      ║  ROBOT SPEAKS                        ║
                      ║  "CVE-…, critical. Do you approve    ║
                      ║   commit 6d12418?"                   ║
                      ╚═══════════════════╤══════════════════╝
                                          │ human voice
                                          ▼
                    ┌───────────────────────────────────────┐
                    │ "I approve commit 6d12418" → APPROVED │
                    │ "yes go ahead"             → hold     │
                    │ "sounds good, ship it"     → hold     │
                    │ "I approve commit deadbee" → hold     │
                    │ "no, hold the merge"       → DENIED   │
                    │  silence                   → hold     │
                    └───────────────────┬───────────────────┘
                                        │ approved only
                                        ▼
                    gh pr merge --match-head-commit <sha>
                    (Git itself refuses any other commit)
```

Full detail in **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Why four conditions

Each removes a different way of being wrong:

| Condition | Closes |
|---|---|
| `sandbox_tests` | the patch does not actually fix it |
| `qodo_followup` | no independent review — **of this exact commit** |
| `trueforge_checkpoint` | the agent decided for itself that it was done |
| `commit_matches` | tested, reviewed, approved and merged are different commits |

Everything fails closed. Ambiguity, silence, a wrong SHA, and a missing service
all leave the merge locked. The final merge uses `git`'s own
`--match-head-commit`, so the wrong commit is refused at the Git level, not just
by our code.

## Built with

- **[TrueForge](https://trueforge.dev)** — the agent loop, isolated sandbox,
  subagents, MCP connectors, and the native approval checkpoint our gate depends on
- **Bright Data** — live CVE discovery and advisory verification, via MCP
- **Qodo** — reviews every remediation PR; a required gate condition, bound to the head SHA
- **Reachy Mini** (Pollen Robotics) — the physical approver
- **OpenAI Realtime** — the robot's voice and ears

## Quick start

```bash
git clone https://github.com/suhaasteja/fde-robot-harness
cd fde-robot-harness
bin/setup                      # venv, pinned versions, /say patch, .env
# add OPENAI_API_KEY to .env
```

Five services, in order — see **[RUNBOOK.md](RUNBOOK.md)**:

```bash
~/reachy-conv/bin/reachy-mini-daemon                    # :8000
~/reachy-conv/bin/reachy-mini-conversation-app --ui     # :7860  (from repo root)
~/reachy-conv/bin/python bin/robot-mcp                  # :7880
~/reachy-conv/bin/python bin/codebase-mcp               # :7881
npx @truefoundry/trueforge@latest                       # :8790
```

Then:

```bash
bin/demo check     # every service, robot real vs simulated, /say, mic
bin/demo reset     # restore the vulnerable fixture
bin/demo scan      # one CVE run — the robot narrates as it works
bin/demo gate      # poll until approval opens, then speak
```

**No robot?** Everything except motion and audio works against
`reachy-mini-daemon --mockup-sim --headless`.

## Try it in 30 seconds

With the stack up, say to the robot:

> *"Is our code vulnerable right now?"*

It searches your codebase, checks the live web, and answers aloud with the CVE,
severity and reason. Read-only — it assesses, it never patches.

## Docs

| | |
|---|---|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | the as-built system, in full |
| **[RUNBOOK.md](RUNBOOK.md)** | run it, and restart anything you close |
| **[DEMO-SCRIPT.md](DEMO-SCRIPT.md)** | presenting it live, beat by beat |
| **[AGENTS.md](AGENTS.md)** | for whoever picks this up next — rules and gotchas |
| **[INTEGRATE.md](INTEGRATE.md)** | adding the robot to an existing TrueForge |

## What is real, and what is staged

Worth stating plainly:

**Live** — CVE discovery (different runs surface different CVEs), applicability
assessed by reading the actual code, the generated patch, sandbox test runs,
subagent delegation, the pull request, the Qodo review, the gate, and the merge.
The agent genuinely returns `VERDICT: NONE` when nothing applies.

**Staged** — `demo-fixture/` is a deliberately vulnerable service we wrote. It is
a fixture, like any security demo.

**Known rough edge** — `soc-watch` fills the UI's severity and summary strings for
one CVE from a lookup rather than deriving them from the agent's report. It is
gated on a genuine finding, but those two fields are canned.

## What we would do next

Consolidate `cve-monitor` and `soc-watch` into one state machine. Qodo flagged
this on our own PR — both implement merge-gate logic, and duplicated logic in the
security-critical path is a real divergence risk. It was not hypothetical: hours
later the two disagreed about an output format and the approval gate silently
could not open.
