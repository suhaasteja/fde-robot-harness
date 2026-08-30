# Physical SOC — live demo script

For presenting to judges. [RUNBOOK.md](RUNBOOK.md) is the operational reference;
this is what you *say* and *do*, in order.

**Running time: 5 minutes live**, plus a pre-warm you start before they arrive.

---

## The one sentence

> Security bots can already write patches. What they cannot do is decide when a
> human should be in the room. We made approval physical.

If a judge remembers nothing else, that is the sentence.

---

## Timing reality — read this first

A full scan takes about **four minutes**, and Qodo's review takes a few more.
That is dead air you cannot narrate through. So:

**Pre-warm 8–10 minutes before you present:**

```bash
bin/demo reset
bin/demo check          # all eight green
bin/demo scan           # let it finish — this creates the PR and starts Qodo
bin/demo gate           # leave running in a visible terminal
```

By the time judges arrive the gate should be at `waiting`, or one prerequisite
away. **The live part is the approval** — which is the part that matters anyway.

If you have a full ten minutes with them, run the scan live and let the robot's
narration carry it. It talks the whole way through, which is unusual enough to
hold attention.

---

## Act 1 — the hook and the interview (0:00–1:00)

**Do:** stand next to the robot. Nothing on screen yet.

**Say:**

> "Every security team already has scanners finding CVEs and bots opening patch
> PRs. Both of those are solved. Here's what isn't: that PR becomes one
> notification among forty, and it either ships four days late or gets
> rubber-stamped by someone who never read the diff.
>
> Approval has no weight. So we gave it weight — and we started by having it
> learn who it works for."

**Do:** turn to the robot.

**Say:** *"Priya approves changes to our systems."*

Wait for it to acknowledge. Then:

**Say:** *"Our most critical service is payment-service."*

**Pause between the two.** The model streams its tool arguments while you talk;
saying both in one breath can truncate the call, and it will sound like it worked
while saving nothing.

**Do:** show `state/customer_profile.json` — or the panel — with the approver and
critical service now in it.

**Say:**

> "It just wrote that down. It'll matter in ninety seconds."

**Why this opens:** it establishes the robot as a colleague being onboarded rather
than a prop, and it sets up the payoff in Act 4 where it uses both facts.

## Act 2 — what already happened (1:00–2:00)

**Do:** show the TrueForge session (`bin/demo status` prints the URL). Expand
*Agent steps*.

**Say:**

> "Ten minutes ago this ran on a timer. No one asked it to.
>
> TrueForge reached a real Bright Data MCP tool and found the public advisory.
> It reproduced the issue, wrote the smallest patch, and ran the tests **inside
> its own sandbox** — not on my machine. Tests went from one failing to all
> passing.
>
> Then it delegated: two subagents, one on blast radius, one on regression
> coverage. Both came back."

**Point at:** the `bright-data` tool call, the sandbox test table, the two
subagent threads. These are native TrueForge screens — do not narrate over a
diagram, show the real thing.

**Say:**

> "It opened a pull request. Qodo reviewed it — and Qodo had to review *this exact
> commit*, not an earlier one. A stale review on an obsolete SHA cannot unlock
> anything."

**Point at:** the PR, Qodo's review, the SHA.

---

## Act 3 — where it stops (2:00–2:30)

**Do:** switch to the terminal running `bin/demo gate`.

**Say:**

> "And then it stopped.
>
> Four things have to be true before this system will even *ask* a human: sandbox
> tests passed, Qodo reviewed the current head, TrueForge hit its own approval
> checkpoint, and the commit SHAs all match. Three of four isn't enough."

**Point at:** the four `PASS` lines and `merge: locked`.

**Say:**

> "It has a patch it believes in, tests that prove it, and a review that agrees.
> It still will not merge. It is waiting for a person."

---

## Act 4 — the gate holds, twice (2:30–3:45)

This is the beat that wins technical judges. **Do not skip it.**

### 4a — the commit changes after review

**Do:** in a terminal, `bin/demo amend`. It pushes a trivial commit to the open
remediation branch — after Qodo has already reviewed.

**Wait ~10 seconds.** GitHub's API lags a push; the gate self-corrects on its next
poll, but check too early and you will see the old SHA.

**Robot:**

> *"The commit changed after review. I won't ask for approval until Qodo has seen
> this exact code."*

**Do:** point at `qodo_followup` flipping to **false** and the gate returning to
`locked`.

**Say:**

> "That's the attack this whole thing exists to stop: get a clean review, then
> change the code. Nothing here is special-cased — the gate simply noticed that
> the commit it was told about is no longer the commit that exists."

Let Qodo re-review the new head, and it unlocks again.

### 4b — the words have to be exact

**Say to the robot:** *"Yes, go ahead."*

**Do:** point at the terminal. Still locked.

**Say:**

> "Not good enough. That's ambiguous."

**Say to the robot:** *"Sounds good, ship it."*

**Do:** still locked.

**Say:**

> "Also not good enough. And this one matters —"

**Say to the robot:** *"I approve commit deadbee."*

**Do:** still locked.

> "— that's an approval with the wrong SHA. If I approve the wrong commit, nothing
> happens. Silence does the same thing. Everything that isn't an explicit,
> exact-commit approval fails closed."

**Say to the robot:** *"No, hold the merge."*

**Do:** gate shows `denied`, merge stays locked.

---

## Act 5 — the named approval (3:45–4:30)

**Do:** let the room go quiet. This is the moment; do not talk over it.

**Robot:** addresses the approver *by name*, and cites the service they flagged:

> *"Priya, CVE-2025-29927 is verified. It can skip middleware authorization using
> a forged internal header. It's in payment-service, which you flagged as
> critical. Bright Data sourced the evidence. TrueForge confirmed applicability,
> built the patch, and passed sandbox tests. Qodo reviewed exact commit 6d12418
> for quality. Do you approve commit 6d12418?"*

Both of those facts came from Act 1 — it is using what it was told, not a script.
With no profile it falls back to generic wording; the gate is unaffected either
way.

**Say, clearly:**

> **"I approve commit `<sha>`."**

Use the exact seven characters it announced.

**Do:** the gate flips to `approved`. Show the audit record — who said it, the
exact words, the CVE, the SHA, the timestamp.

**Say:**

> "That's a named human, on the record, bound to one specific commit. Not a
> checkbox. Not a Slack thumbs-up."

**Optional, if you want the merge live:** run the `--merge` command from the
runbook. Only that exact reviewed commit can merge — `gh pr merge` is called with
`--match-head-commit`, so the wrong commit is refused at the Git level, not just
by our code.

---

## Act 6 — close (4:30–5:00)

**Say:**

> "Bright Data found it. TrueForge patched, tested, and delegated it. Qodo
> reviewed it. And a robot made sure a human said yes out loud before anything
> irreversible happened.
>
> Autonomy you can stop."

---

## If something breaks

Live demos break. These are the realistic failures and what to say.

| What happens | Say this | Then |
|---|---|---|
| Robot doesn't respond | "It's listening — mic's muted." | `curl -X POST localhost:7860/mic -d '{"muted":false}' -H 'Content-Type: application/json'` |
| Voice comes from the laptop | Don't point it out. Keep going. | `/say` is missing; fix after |
| Robot speaks but doesn't move | Don't point it out. | daemon is in `--mockup-sim` |
| Scan finds nothing | "It already patched this one — that's the fixture being honest." | `bin/demo reset` |
| Gate stuck on `qodo_followup` | "Qodo is still reviewing. It won't let us proceed until it's done — which is the point." | genuinely true; wait or cut to Beat 4 |
| Approval not recognised | "It wants the exact commit." Repeat with the SHA. | this is correct behaviour, use it |
| Robot doesn't remember the interview | "Let me tell it again." Say one fact, pause, say the next. | args truncate if you talk over the tool call |
| Voice comes from the laptop | Don't point it out; keep going. | terminal shows a loud warning; app isn't running |
| Gate still locked after amend | "GitHub hasn't caught up yet." Wait 10s. | API lags a push; it self-corrects |

**The general move:** every failure in this system is a *fail-closed* failure. If
something doesn't proceed, that is the thesis working. Say so and continue — do
not apologise for a gate that refuses to open.

---

## Questions judges will ask

**"Is the merge real?"**
Yes. `gh pr merge --match-head-commit <sha>` against a real GitHub PR. It cannot
merge a different commit than the approved one.

**"What if the robot mishears?"**
Then it fails closed. The classifier needs an explicit approval verb *and* the
exact seven-character SHA. "Yes", "ship it", silence, and a wrong SHA all hold.

**"Could the agent approve its own patch?"**
No. The approval comes from a separate tool that only records what a human said,
and the gate additionally requires Qodo and TrueForge's own checkpoint. The agent
is explicitly instructed it may not declare an incident finished.

**"What's actually autonomous vs scripted?"**
The CVE discovery is live web via Bright Data. The patch is generated. The tests
run in TrueForge's sandbox. The Qodo review is a real GitHub App. Nothing about
the finding or the fix is pre-recorded — the fixture is a deliberately vulnerable
file, and that is the only staged part.

**"Is the CVE hardcoded?"**
No. Discovery is live — different runs surface different CVEs, and it correctly
reports VERDICT: NONE when nothing applies. What is hardcoded is a lookup of
plain-English one-liners for three CVE ids, used only to phrase the spoken alert
more naturally, with a generic fallback for anything else. The finding, severity,
summary and affected service all come from the agent's own report.

**"What would you do next?"**
Consolidate the two orchestration scripts into one state machine. Qodo flagged
this on our own PR — `cve-monitor` and `soc-watch` both implement merge-gate
logic, and duplicated logic in the security-critical path is a real divergence
risk. We'd fix that before anyone ran this for real.
