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

---

# Feedback questions

## Which TrueForge feature was the most useful while building your project, and why?

> **The native approval checkpoint.** Our entire product is "an agent must not
> decide for itself that its own patch is safe to merge," and TrueForge already
> had the primitive: the agent calls `ask_user_question`, the turn pauses with
> `tool.response_required`, and it stays paused until a human answers. We didn't
> have to build a parallel gate and hope the agent respected it — we made "did
> TrueForge actually stop and ask?" one of four required conditions, then
> delivered the human's spoken answer back into that pending checkpoint through
> the sessions API. The safety property is enforced by the harness, not by our
> prompt.
>
> Close second: MCP connectors made a physical robot a first-class tool. We
> exposed the Reachy Mini as an MCP server, and any agent could control it
> alongside Bright Data and GitHub with no robot-specific code in the agent.

## Where did you get stuck while building with TrueForge, and what would you improve about the developer experience?

> Three things, all of which cost us real time because they fail silently.
>
> **Deferred tool loading.** Our agent had a `say` tool and simply never called
> it. We put the instruction in the system prompt, verified it was stored, and
> still nothing. The cause is that agents see only tool *names* and must call
> `get_tool_info` to expand one — so a tool the model doesn't bother expanding is
> effectively invisible, and no amount of prompting fixes it. The fix is
> `preload_tools`, which we found by reading the agent manifest rather than from
> an error. Suggestion: surface this in the UI — mark preloaded vs deferred tools
> per server, or warn when instructions reference a tool that is deferred.
>
> **Paused turns have no `state.output`.** A turn stopped at an approval
> checkpoint reports `status: done`, but its report lives in the turn's messages.
> We read `state.output`, got an empty string, and silently lost the entire
> evidence chain from the very run requesting approval. Suggestion: either
> populate `output` with the partial report, or state prominently in the docs that
> a paused turn's content is in its messages. The docs note that "a done turn
> carrying requiredActions is paused, not complete" — but the practical
> consequence for reading output isn't spelled out.
>
> **Agent updates are by id, not name.** `PUT /api/v1/agents/robot-operator`
> returns `Agent not found: robot-operator`, which reads as "the agent doesn't
> exist" when it does. Suggestion: accept the name, or return a 400 saying to use
> the id.
>
> Smaller: TrueForge binds IPv6-only, so a health check against
> `127.0.0.1:8790` reports it down while it is serving fine on `[::1]`.

## How useful was Qodo's code review feedback while building your project?

**5**

## What was the most useful or frustrating part of working with Qodo, and what would you change?

> The most useful thing Qodo did was predict a bug we hadn't hit yet. Reviewing
> our PR, it flagged that our two orchestration scripts each implemented Qodo
> verification, checkpoint release, voice parsing and merge behaviour, and warned
> this "creates divergence risk in the most security-sensitive path."
>
> A few hours later we hit exactly that. The two scripts disagreed about the
> agent's expected output format, so two of our four gate conditions could never
> pass and the approval gate could never open — silently, with no error anywhere.
> Qodo had named the failure class before we experienced it. That is a materially
> different kind of value from style feedback, and it changed what we are doing
> next.
>
> Most frustrating: binding a review to a specific commit. Our merge gate requires
> that Qodo reviewed the *current head SHA* — a stale review of an older commit
> must not unlock a merge. But `gh pr view --json reviews` omits the reviewed
> commit entirely, so we had to drop to
> `gh api repos/{owner}/{repo}/pulls/{n}/reviews` to get `commit_id`. What I would
> change: expose the reviewed SHA in the standard review object, and provide a
> first-class "is this PR's current head reviewed and approved?" check. Every team
> gating a merge on review freshness has to reimplement that.
>
> Minor: the notification flow is noisy — "New Review Started", "Qodo is busy
> working" and "review superseded" arrived as separate emails for one review.

## How easy was it to use Bright Data?

**4**

## What was the most useful or frustrating part of working with Bright Data, and what would you change?

> Most useful: it made the vulnerability discovery genuinely live rather than
> staged. Through the MCP connector our agent searched for recently disclosed CVEs
> and fetched the authoritative advisories behind them — NVD, GitHub Security
> Advisories, vendor pages — with zero scraping code on our side. In one run it
> used Bright Data to establish that our pinned `next@15.2.3` was patched at
> framework level but that our own middleware reintroduced the vulnerable pattern.
> That distinction required reading the real advisory; it is not something a model
> could assert safely from memory.
>
> Most frustrating: some sources will not fetch directly, and the agent has to
> notice and route around it. We watched it announce, out loud, "Reuters would not
> open directly, so I'm checking search headlines and CNBC" — good recovery, but
> it burns turns and time, and on a broad query one run made 41 tool calls before
> finishing.
>
> What I would change: the tool surface is large enough that our agent spent
> several calls on `list_tools` and `get_tool_info` before its first real search. A
> small number of high-level entry points — "search the web", "fetch this page as
> markdown" — with the specialised tools behind them would cut latency noticeably
> for agents that just need a fact. And a clearer signal distinguishing "this site
> blocked us" from "no results" would let an agent fall back immediately instead
> of retrying.
