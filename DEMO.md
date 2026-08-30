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
  Bright Data                TrueForge (:8790)                 Qodo
  ───────────                ─────────────────              ───────────
  CVE feeds        ──┐                                   ┌─ speaks the alert
  vendor advisories  ├──►  agent session                 │  (antennae + head turn)
  breach forums      │     ├─ scan dependencies          │
  release notes    ──┘     ├─ write patch  ┐             │
                           ├─ run tests    ├─ sandbox    │
                           └─ subagent audit┘                 │
                                  │                           ▼
                                  └──────────────────► PR review
                                                               │
                                  Reachy Mini                   │
                                  ───────────                   │
                                  speaks alert ◄────────────────┘
                                  captures named approval
                                           │
                                           ▼
                                HUMAN APPROVAL CHECKPOINT
                                           │
                                           ▼
                                      merge to main
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
| Bright Data MCP | — | **configured** | authenticated read-only connector in TrueForge |
| `bin/soc-watch` | — | **built** | TrueForge + GitHub/Qodo evidence bridge |
| Approval parser | — | **built** | fail-closed, exact-SHA parsing from `logs/app.log` |
| Qodo gate | — | **in validation** | initial review complete; fixture follow-up queued |

The software path is built. The remaining pre-shoot checks are Qodo's follow-up review on
the corrected fixture and the final Reachy hardware connection.

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

## Demo north star

The audience should be able to repeat this sentence after 15 seconds:

> **Physical SOC finds a critical vulnerability, safely prepares the fix, and brings a
> human into the room before it can ship.**

This is a product film with technical proof, not a narrated terminal session. Reachy is the
hero, the control panel is the product, and TrueForge is visibly the engine. Every shot must
either advance the incident or prove a judging criterion.

### Non-negotiable reveal order

Before Reachy begins the approval interaction or speaks, the film must visibly prove—in
the products' native interfaces—that the agent completed its work:

1. **TrueForge first:** show the named session receiving the task, calling Bright Data MCP,
   generating the patch, running the failing and passing tests in the isolated sandbox,
   receiving both subagent results, and stopping at its native approval checkpoint.
2. **Qodo second:** show the actual GitHub pull request with Qodo's completed initial review,
   the finding and team response, the corrective commit, and Qodo's follow-up review on the
   exact final SHA.
3. **Reachy third:** only after the UI visibly says `SANDBOX PASSED`, `QODO REVIEWED`, and
   `APPROVAL REQUIRED` may Reachy turn toward the approver and speak.

Do not replace steps 1 or 2 with narration, the custom dashboard, a terminal log, or logos.
Use readable screen recordings of TrueForge and the Qodo PR itself. Brief zooms and callouts
may direct attention, but the authentic interface, URL/PR number, session ID, and commit SHA
must remain visible.

### Visual language

- Use one clean 16:9 capture at 1440p or 4K. Record screen and camera separately and edit;
  do not film a laptop screen with a phone.
- Keep the control panel full-screen for most of the film. Use a consistent right-side
  **TrueForge activity rail** with six labeled events: `MCP`, `SANDBOX`, `SUBAGENTS`,
  `SESSION RESTORED`, `APPROVAL`, `MERGE`.
- Use only three semantic colors: neutral blue for work, amber for waiting, green for
  approved. Reserve red for the critical CVE. Avoid hacker-green terminal aesthetics.
- Show readable outcomes, not logs: source and timestamp, failing test → patch → passing
  test, two named subagent conclusions, exact commit SHA, and gate state.
- Add restrained captions for product terms the first time they appear. Never put more
  than one sentence on screen. No architecture slide in the film.
- Frame Reachy at eye level in a tidy environment with soft front light. Record its audio
  with a nearby microphone, then mix dialogue above music. Antennae and head movement
  should begin before it speaks so the audience looks at it.
- Use quiet, low-tempo music only under setup and autonomous work. Cut it completely at
  the approval checkpoint; the silence is part of the interface.

### The single product screen

Build or stage the control panel as one legible incident timeline rather than several tabs:

```text
PHYSICAL SOC                                      TRUEFORGE ACTIVITY
Critical incident · CVE-XXXX-XXXXX                ✓ MCP · Bright Data
Remote code execution · request parser            ✓ Sandbox · isolated

1  Detected     public advisory · just now         ✓ 2 subagents returned
2  Reproduced   1 security test failing            ✓ session restored
3  Patched      commit 7f3a21c · 18 tests passing
4  Reviewed     Qodo review complete               ■ APPROVAL REQUIRED
5  Approval     WAITING FOR AAHAN
6  Merge        LOCKED
```

The state transition must be unmistakable: while waiting, the approval row pulses amber
and `MERGE · LOCKED` remains visible. After approval, both become green and the audit card
appears. This screen also makes the Best UI criteria—what it is doing, waiting on, and did—
understandable without narration.

## Final three-minute film

The timings include breathing room. Use match cuts to compress real waiting, but never
fabricate a result or imply two events happened in an order they did not.

| Time | Picture | Exact narration/dialogue | Requirement proved |
|---|---|---|---|
| **0:00–0:12** | Cold open: Reachy turns toward camera; fast cut to `CRITICAL` incident card | “Security bots can write patches. The dangerous part is deciding when to trust them.” | Clear problem; originality |
| **0:12–0:24** | One uninterrupted view of the six-step product timeline; merge visibly locked | “Physical SOC uses TrueForge to investigate, patch, test, and stop before the irreversible step.” | Product understood; TrueForge central |
| **0:24–0:42** | **Native TrueForge session:** task appears, then the Bright Data MCP tool call expands with public advisory URL, fetched-at time, and CVE summary | “This TrueForge agent reaches a real Bright Data MCP tool and finds a critical advisory affecting our service.” | Real external tool; TrueForge central; authorized public data |
| **0:42–1:03** | **Native TrueForge execution:** agent-generated patch diff, explicit isolated-sandbox badge, failing security test, then `18/18 PASS`; keep session ID visible | “It reproduces the exploit, writes the smallest patch, and runs it inside TrueForge’s isolated sandbox—not on our machine.” | Visible agent work; generated code; sandbox |
| **1:03–1:18** | **Native TrueForge subagent view:** `Blast radius` and `Regression audit` return different, useful conclusions; end on native `APPROVAL REQUIRED` checkpoint | “Two subagents independently map the blast radius and audit the change. Then TrueForge stops.” | Real delegation; native approval gate |
| **1:18–1:29** | Refresh/reconnect the **TrueForge interface**; same session ID, results, and native approval checkpoint return | “We reconnect. TrueForge restores the same session, including the locked approval.” | Persistent session |
| **1:29–1:44** | **Native GitHub/Qodo PR:** show PR number and matching SHA, initial Qodo finding, team response and fix, then completed follow-up review; cut back to dashboard showing `QODO REVIEWED · APPROVAL REQUIRED` | “The exact patch has tests and a completed Qodo review. But good automation still knows where its authority ends.” | Visible Qodo checks; code quality; control |
| **1:44–2:12** | Music stops. Reachy raises antennae, faces Aahan, and speaks; UI remains visible in a picture-in-picture | Reachy: “Critical. CVE-XXXX-XXXXX. Remote code execution in the request parser. The patch passed 18 tests and Qodo review. Aahan, do you approve commit 7f3a21c?” | Physical, informed, commit-bound approval |
| **2:12–2:27** | Aahan denies. Transcript prints the words; gate stays amber and merge stays locked for two full seconds | Aahan: “No. Hold the merge.” Narrator: “A no—and anything ambiguous—fails closed.” | Negative path; safety is real |
| **2:27–2:42** | Reachy asks again only after an explicit retry action; Aahan approves exact commit | Aahan: “I approve commit 7f3a21c.” | Explicit human approval |
| **2:42–2:53** | Gate turns green; real team-owned PR merges; deployed/merged SHA matches approved SHA | “Only that exact reviewed commit can now merge.” | Irreversible action occurs after approval |
| **2:53–3:00** | Beautiful audit card beside Reachy: actor, words, CVE, SHA, test count, Qodo PR, time | “Every critical fix ships with evidence—and a human voice attached.” End card: `PHYSICAL SOC · AUTONOMY YOU CAN STOP.` | Auditability; memorable close |

### What must be visible—not merely said

1. The TrueForge session identifier persists across reconnect.
2. Bright Data appears as the MCP tool that returned a real public source and timestamp.
3. The generated patch and tests execute under an explicit isolated-sandbox label.
4. Two subagents return different, decision-useful outputs.
5. The same commit SHA appears in the patch, Qodo-reviewed PR, spoken approval, merge,
   and audit record.
6. Denial leaves the merge locked; ambiguous speech and silence behave the same way.
7. Approval is a native TrueForge checkpoint. `soc-watch` translates the physical voice
   interaction into a decision; it does not implement a parallel or bypass gate.
8. Qodo evidence is real and completed before merge. The required hackathon development
   PR history is also linked separately in README; runtime Qodo use does not replace it.
9. The native TrueForge work and native Qodo review both appear before the first frame in
   which Reachy begins its approval movement or speech.

### Capture and edit plan

Record each proof as a clean take, then assemble the causal sequence above. A recorded
demo may compress actual sandbox, Qodo, or network wait time with a labeled `time passes`
match cut; it may not replace a failed action with a mock. Capture:

- A-roll: one confident narration take and the human denial/approval.
- Robot: wide hero shot, close-up turn/speech, and silent waiting reaction.
- Screen: full end-to-end run plus isolated clean takes of MCP, sandbox, subagents,
  reconnect, Qodo history, denial, approval, merge, and audit card.
- Safety take: no response, ambiguous response, wrong commit SHA, and robot disconnect,
  all visibly remaining locked. Use one in the main film and the rest for judge Q&A.
- Room tone and clean robot dialogue. Add captions to every spoken line.

Export once with subtitles burned in and once without. Watch the final export muted,
then audio-only: the story must work both ways. Test all text at phone size because judges
may watch the first pass on a small screen.

---

## Prize strategy and honest validation

| Target | What actually wins it | Our evidence |
|---|---|---|
| **NVIDIA DGX Spark — Best Use of TrueForge** | TrueForge visibly owns real MCP calls, generated code in an isolated sandbox, human approval before an irreversible action, subagent delegation, and session continuity across reconnects | Beats 1–3 show every capability; Beat 3 turns the required approval into a memorable physical interaction |
| **AirPods 4** | **Not listed on the official hackathon rules/prize page reviewed on 2026-08-29. Confirm the in-room award and criteria with an organizer before optimizing for it.** | Reachy's embodied voice interaction is likely strong for a creativity/experience award, but this is not a verified submission track |

**Verdict:** this is a credible DGX contender now that the core TrueForge run is real and
captured; final readiness depends on the Qodo follow-up and Reachy hardware rehearsal. The
idea is stronger than a standard incident
responder because the physical, named, audible approval makes safety legible in seconds.
It will lose on technical excellence if the merge is simulated, if TrueForge merely sits
behind `soc-watch`, or if reconnect persistence is only narrated. Make each one observable.

Embed the Bright Data commands in the project rules file (`CODEX.md` / `.cursor/rules`)
so the pipeline is part of the repo's standing instructions, not a one-off invocation.

---

## Official requirement checklist (submission blocker list)

This checklist mirrors the published hackathon rules. A checked box needs public,
inspectable evidence; prose in this runbook alone does not satisfy it.

- [ ] Register; participate solo or with no more than four people, with each person on
  only one team; follow the WeMakeDevs Code of Conduct.
- [ ] Build the original code and design during the August 24–30, 2026 hackathon window.
  Pre-event planning and diagrams are allowed; dependencies, templates, public APIs, and
  public assets are allowed.
- [ ] Run the agent itself on TrueForge. In the video, visibly show TrueForge reaching the
  real Bright Data MCP tool, executing agent-generated code in its isolated sandbox,
  pausing before merge, delegating to subagents, and preserving the session across a
  refresh/reconnect. A thin wrapper or mocked tool does not qualify.
- [ ] Put **every substantive change** on a branch and through a GitHub pull request before
  merge. Qodo must complete its review; resolve every valid High finding or explain a
  dismissal in its thread; push fixes; request a follow-up review; then have a human merge.
  Do not push substantive work directly to `main`.
- [ ] Make the repository public and open source, with a license and a README that lets a
  stranger understand, install, configure, and run the project.
- [ ] Add an exact `## Qodo Code Review Evidence` section to README containing: a public
  link to at least one representative merged PR with meaningful hackathon code; one or two
  sentences saying what Qodo found and what was fixed or intentionally dismissed; and PR
  history showing the initial review, team decisions, fixes, and follow-up review on the
  final code. Screenshots do not replace the public link.
- [ ] Use only tools, accounts, and data the team owns or has permission to access. Keep
  secrets, private/personal data, and login-protected information out of the public repo
  and demo video. Use public CVE/vendor sources and redact tokens, usernames, and local
  paths from terminal capture.
- [ ] Disclose all AI coding assistants used in the README/write-up.
- [ ] Ensure every team member understands and can explain the code, architecture, agent
  behavior, and technical decisions; record meaningful human contribution and verification.
- [ ] Publish an approximately three-minute demo video showing the real end-to-end agent,
  the problem, TrueForge's role, a real tool call, sandbox execution, negative then positive
  approval behavior, the irreversible merge only after approval, and the final audit trail.
- [ ] Submit the public repository, demo-video link, and a short write-up explaining what
  the agent does and how it uses TrueForge before **August 30, 2026 at 8:00 PM London time**.
- [ ] If pursuing Best Blog Post, publish and submit its link. Explain the job, implementation,
  TrueForge's role, failures, and lessons, with screenshots or a clip.

## Six-criterion judge check

All six criteria are equally weighted; rehearse one visible proof for each.

| Criterion | Proof to put in the demo/submission |
|---|---|
| Potential impact | State the current CVE-to-merge delay and show the agent reducing it while retaining accountable human control; use one measured before/after number if available |
| Creativity and originality | Reachy makes an otherwise invisible software gate physical, directed, and socially difficult to rubber-stamp |
| Technical excellence | One command or documented setup, deterministic fixture fallback, automated tests for allow/deny/ambiguous speech and failure modes, structured audit log, and a real end-to-end run |
| Sponsor tools | TrueForge visibly orchestrates MCP, sandbox, approval, subagents, and persistent state; public PRs show repeated Qodo review and responses |
| Control and safety | Least-privilege GitHub token; fail closed on silence/ambiguity; negative case first; merge permission exists only behind TrueForge's approval gate; approval records actor, CVE, commit SHA, and timestamp |
| Presentation | Three-minute causal story: fresh threat → safe autonomous work → reconnect survives → physical stop → reject → named approval → reviewed merge and audit record |

## Definition of demo-real (no narrated substitutes)

- The CVE is a pinned, reproducible public fixture for reliability, while one separate field
  proves Bright Data fetched live data. Never depend on a surprise live critical CVE.
- The repository and branch are disposable and team-owned; the merge is real.
- The patch changes a vulnerable dependency or fixture-backed sample app, and its tests
  fail before and pass after inside the TrueForge sandbox.
- Subagents produce independently visible, useful results; they are not decorative prompts.
- The TrueForge approval object is the authoritative gate. Parsing Reachy's transcript may
  request approval or denial, but `soc-watch` cannot bypass it.
- Ambiguous speech, timeout, parser failure, robot failure, MCP failure, and Qodo failure all
  fail closed. `--force-approve` is for rehearsal only and must not appear in the judged run.
- The final audit record binds the approver identity and words to the CVE, exact commit SHA,
  test result, Qodo-reviewed PR, decision, and timestamp.

---

## When it breaks

| Symptom | Cause | Fix |
|---|---|---|
| Prompt editor greyed out | app started without `--ui` | `bin/reachy-app restart --ui` |
| `daemon down` | Control app closed | reopen it; daemon owns :8000 |
| App dies instantly on start | conda's glib shadowing GStreamer | already handled — `cmd_start` scrubs conda from PATH |
| Robot greets the wrong name | stale saved facts | panel → **Clear saved facts** (backs up to `.json.bak`) |
| Robot won't stop | backgrounded app ignores SIGINT | `make stop` (SIGTERM → KILL), never Ctrl-C |
| Approval never registers | log line didn't match the phrase | fail closed; retry explicit voice approval or use the fallback clip—never bypass the judged gate |

**Have a recorded 30-second fallback clip of Beat 3.** Live robot audio in a loud venue is
the single most likely thing to fail, and it's the beat you cannot afford to lose.

---

## Build order

1. `bin/soc-watch` — poll TrueForge for pending checkpoints, tail `logs/app.log` for the
   approval phrase, release or hold. This is the spine; build it first.
2. Bright Data MCP registered into TrueForge, with source URL and fetch timestamp exposed
   in the incident timeline.
3. `soc-officer` personality, tuned against a real CVE briefing until the phrasing lands.
4. Qodo gate on the generated diff.
5. A fallback recording plus a rehearsal-only bypass that is disabled and inaccessible in
   the judged build. The real workflow must always fail closed.

Rehearse Beat 3 more than the rest combined.

## Final cut go/no-go

Do not submit until every answer is yes:

- [ ] Can a new viewer explain the product after the first 15 seconds?
- [ ] Is Reachy visible before the first technical detail and during the full approval?
- [ ] Before Reachy speaks, did viewers clearly see the agent working in native TrueForge
  and the completed checks in the native GitHub/Qodo pull request?
- [ ] Does every TrueForge capability have readable, authentic on-screen evidence?
- [ ] Is the exact commit SHA consistent from patch through approval, merge, and audit?
- [ ] Does the denial visibly keep the merge locked for at least two seconds?
- [ ] Is Qodo’s initial review, response, fix, and follow-up review readable and public?
- [ ] Are all secrets, notifications, usernames, tabs, local paths, and personal data hidden?
- [ ] Are subtitles accurate, audio clean, text readable on a phone, and runtime 2:50–3:00?
- [ ] Does the final frame include product name, one-line promise, public repo URL, and team?
- [ ] Has someone unfamiliar with the project watched it once and correctly described both
  the user value and why TrueForge—not merely an LLM—is essential?

## Explicit shooting manifest

Record these as separate clean clips so the editor can preserve authentic evidence while
keeping the final film under three minutes.

| Clip | Screen or camera | Must remain readable |
|---|---|---|
| 1 | Reachy hero camera shot | Robot movement, clean environment, no laptop glare |
| 2 | Physical SOC **Incident** tab | CVE severity, affected service, six-stage timeline, `MERGE LOCKED` |
| 3 | Native TrueForge session | TrueForge branding, session ID, Bright Data MCP call, public source and timestamp |
| 4 | Native TrueForge sandbox activity | Generated patch, isolated-sandbox label, failing test before fix, passing suite after fix |
| 5 | Native TrueForge subagent activity | Two distinct subagents and their decision-useful conclusions |
| 6 | Native TrueForge persistence proof | Same session ID before and after browser refresh/reconnect |
| 7 | Native TrueForge approval checkpoint | Exact pending action and commit SHA; execution visibly paused |
| 8 | Native GitHub PR **Conversation** tab | PR number, Qodo initial review, meaningful finding, team reply |
| 9 | Native GitHub PR **Files changed/Checks** | Corrective commit, Qodo follow-up review, successful final SHA |
| 10 | Split shot: Reachy + Incident UI | Reachy speaking while `APPROVAL REQUIRED` and `MERGE LOCKED` remain visible |
| 11 | Negative approval shot | Spoken denial in transcript; no state advances; merge stays locked |
| 12 | Positive approval shot | Spoken exact SHA, TrueForge approval release, matching UI transition |
| 13 | Native GitHub merged PR | Human merge, merged SHA identical to reviewed and spoken SHA |
| 14 | Physical SOC audit card | Approver, exact words, CVE, SHA, tests, Qodo PR, timestamp |

### Required screen order in the final edit

```text
Reachy cold open
→ Incident UI: critical alert
→ native TrueForge: MCP → sandbox → tests → subagents → reconnect → checkpoint
→ native GitHub/Qodo: finding → fix → follow-up review on final SHA
→ Incident UI + Reachy: deny → remain locked → explicitly retry → approve exact SHA
→ native GitHub: merge
→ Incident UI: immutable audit card + closing line
```

Never show Qodo as a generic logo or custom animation instead of its actual GitHub review.
Never crop out the TrueForge session ID, GitHub PR number, or commit SHA. Use zoom callouts,
not replacement graphics. Blur API keys, notifications, usernames not needed for the story,
local filesystem paths, and browser profile details before export.
