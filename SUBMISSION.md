# Hackathon submission — draft answers

Copy into the form. **Deadline: 6 PM San Francisco time.**

Fields marked **YOU** need your input — I don't have them.

---

## Email
`suhaastejav@gmail.com`

## Team name
**YOU** — or `SOLO` if you're submitting alone.

## Name of the person submitting
**YOU**

## Name(s) and Email(s) of all your teammates
**YOU** — Aahan's full name and email.

---

## Track

You can submit to all tracks but only win one. Ranked by how strong the evidence is:

1. **Best Use of TrueForge (NVIDIA DGX Spark)** — strongest. TrueForge owns the
   agent loop, the sandbox, subagents, the MCP connectors, and the native approval
   checkpoint. It isn't a wrapper around one API call.
2. **Best Use of Bright Data (AirPods 4)** — strong. Live CVE discovery is the
   trigger for the whole pipeline, not decoration.
3. **Best Code Quality (Mac Mini)** — credible. Qodo reviewed real PRs, we acted
   on its findings, 13 tests, fail-closed design throughout.
4. **Best UI (iPads)** — weakest. The control panel is functional but plain, and
   the *robot* is the interface rather than a screen. Submit if you like; don't
   optimise for it.
5. **Best LinkedIn post** — **YOU**, needs the post.

---

## GitHub link
`https://github.com/suhaasteja/fde-robot-harness`

Public, 45 commits, real history. `README.md` is currently **empty** —
**fix this before submitting.** The judging criteria explicitly mention a proper
README. Point it at `ARCHITECTURE.md`, `DEMO-SCRIPT.md` and `RUNBOOK.md`, which
are all written.

## Deployed link
Leave blank. It runs on local hardware with a physical robot; there's no URL.

## Video demo link
**YOU** — max 3 minutes, covering: about the project, tech stack and architecture,
demo, and optionally learning. `DEMO-SCRIPT.md` has the beat-by-beat.

The single most important shot: **the gate refusing.** "Yes go ahead" leaves it
locked; only the exact commit SHA opens it. That proves the thesis better than the
approval does.

---

## What does your project do?

> Physical SOC turns a Reachy Mini desk robot into the human-in-the-loop approval
> gate for automated vulnerability remediation.
>
> Scanners that find CVEs and bots that write patches are solved problems. What
> isn't solved is the approval step: the patch PR becomes one notification among
> forty, and it either ships days late or gets rubber-stamped by someone who never
> read the diff. Approval has no weight.
>
> We gave it weight by making it physical. Every 60 seconds an agent finds newly
> disclosed CVEs on the live web, checks them against our actual codebase, writes
> and sandbox-tests a patch, opens a pull request, and waits for an independent
> code review. Then it stops. A robot turns to a person, states the CVE, the
> severity and the blast radius out loud, and asks for approval by exact commit
> SHA. Nothing merges until a named human says so aloud.
>
> The gate is deliberately hard to satisfy. Four independent conditions must all
> hold, and everything else fails closed: an ambiguous "yes, go ahead", silence,
> or an approval naming the wrong commit all leave the merge locked. The final
> merge uses `git`'s own `--match-head-commit`, so a different commit than the one
> approved is refused at the Git level, not just by our code.
>
> It's for teams shipping security patches faster than a human can meaningfully
> review them — where the bottleneck isn't finding or fixing the bug, but knowing
> when a machine's judgment should be trusted.

---

## How did you use TrueForge in your project?

> TrueForge is the engine. Everything the system reasons about runs inside it.
>
> **Two agents.** `physical-soc` runs the incident pipeline with a sandbox
> enabled: it researches disclosures, investigates our codebase, generates a
> patch, and runs the test suite in TrueForge's isolated sandbox rather than on our
> machine. `robot-operator` handles spoken questions and has no sandbox, because
> conversational latency matters more than code execution there.
>
> **Subagents.** `physical-soc` delegates blast-radius and regression analysis to
> two subagents that return independent, decision-useful conclusions.
>
> **MCP connectors.** We registered four: Bright Data, GitHub/Qodo, and two we
> built — `robot-mcp`, exposing the physical robot as 14 tools (speech, head and
> antenna motion, recorded emotions, face tracking), and `codebase-mcp`, exposing
> our repository as searchable tools so the agent can grep and read files rather
> than reason from a snapshot pasted into its prompt.
>
> **The native approval checkpoint is the safety mechanism.** The agent is
> instructed that it may not declare an incident finished; it must pause via
> TrueForge's `ask_user_question`. Our gate requires that pause to have happened —
> `tool.response_required` on the turn — as one of its four conditions. The robot's
> spoken answer is then delivered back into that pending checkpoint through the
> sessions API. TrueForge doesn't sit behind our gate; TrueForge's gate *is* the
> gate, and the robot is how a human reaches it.
>
> **Sessions give the demo continuity.** All delegations share one session, so
> tool calls, arguments, results and subagent threads are inspectable after the
> fact, and the state survives reconnecting.
>
> Two things we learned the hard way. Deferred tool loading means an agent sees
> only tool *names* — a tool it never expands is effectively invisible, and no
> amount of prompt instruction fixes it; you must set `preload_tools`. And a turn
> paused at a checkpoint is `done` with no `state.output`, so its report has to be
> read from the turn's messages — we lost real time to both.

---

## How did you use Qodo in your project?

> Qodo is a required condition in the merge gate, and it also reviewed our own
> development.
>
> **In the pipeline:** when the agent opens a remediation PR, Qodo reviews it. Our
> gate does not accept "Qodo reviewed this PR at some point" — it requires a
> completed review bound to the *current head SHA*. A review of an earlier commit
> cannot unlock a merge, which closes the obvious attack of approving a reviewed
> commit and then pushing something else.
>
> **On our own code:** Qodo reviewed our PRs during the hackathon and its findings
> changed what we built. Its most useful comment identified that our two
> orchestration scripts each implemented Qodo verification, checkpoint release,
> voice parsing and merge behaviour — "which creates divergence risk in the most
> security-sensitive path."
>
> That was not hypothetical. Hours later we hit exactly that divergence: the two
> scripts disagreed about the agent's output format, so two of four gate
> conditions could never pass and the approval gate could never open, silently.
> Qodo had named the failure class before we experienced it. Fixing it is the top
> item on our list of what to do next.

---

## How did you use Bright Data in your project?

> Bright Data is what makes the vulnerability discovery real rather than staged.
>
> The scheduled agent uses the Bright Data MCP connector to search for CVEs
> disclosed or updated since its last run, and to fetch the authoritative advisory
> pages behind them — NVD entries, GitHub Security Advisories, and vendor
> advisories such as Vercel's for the Next.js middleware bypass our demo service
> is vulnerable to.
>
> It is used at two decision points. First, discovery: find what is newly public.
> Second, verification: before the agent claims a CVE applies to us, it must
> confirm the details against a real source — the prompt explicitly forbids
> inventing a match. In a live run, the agent used Bright Data to establish that
> our pinned `next@15.2.3` was patched at framework level but that our own
> middleware reintroduced the vulnerable pattern, which is a distinction it could
> only draw by reading the actual advisory.
>
> Nothing about the finding is pre-recorded. Different runs surface different
> CVEs, and the agent correctly reports `VERDICT: NONE` when nothing applies —
> including immediately after it has patched the fixture, which is how we
> discovered our demo was one-shot.

---

## LinkedIn post links
**YOU** — selfie, tag WeMakeDevs, Qodo, TrueFoundry, Bright Data.

---

## Before you submit

- [ ] **Write the README** — it's empty, and judges are told to look for one
- [ ] Record the video (≤3 min)
- [ ] Team name, teammate names/emails
- [ ] LinkedIn posts if going for that track
- [ ] Confirm the repo is public
