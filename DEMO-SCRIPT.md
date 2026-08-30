# Physical SOC — live demo script

For presenting to judges. [RUNBOOK.md](RUNBOOK.md) is the operational reference;
this is what you *say* and *do*, in order.

**Running time: 4 minutes live**, plus a pre-warm you start before they arrive.

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

## Beat 1 — the hook (0:00–0:30)

**Do:** stand next to the robot. Nothing on screen yet.

**Say:**

> "Every security team already has scanners finding CVEs and bots opening patch
> PRs. Both of those are solved. Here's what isn't: that PR becomes one
> notification among forty, and it either ships four days late or gets
> rubber-stamped by someone who never read the diff.
>
> Approval has no weight. So we gave it weight."

**Do:** turn to the robot.

**Say:** *"Is our code vulnerable right now?"*

**Robot:** narrates that it is checking, then answers — CVE id, severity, one-line
reason. Roughly:

> *"Yes — this code is vulnerable to CVE-2025-29927, critical, CVSS 9.1.
> `authorize()` trusts an attacker-controlled header that can bypass middleware
> authorization."*

**Why this opens the demo:** it is live, it is fast, and it establishes the robot
as a participant rather than a prop — before you ask them to care about a gate.

---

## Beat 2 — what already happened (0:30–1:30)

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

## Beat 3 — where it stops (1:30–2:00)

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

## Beat 4 — the gate holds (2:00–2:45)

This is the beat that wins technical judges. **Do not skip it.**

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

## Beat 5 — the approval (2:45–3:30)

**Do:** let the room go quiet. This is the moment; do not talk over it.

**Robot:** states the CVE, the severity, and asks for approval by commit.

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

## Beat 6 — close (3:30–4:00)

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

**"What would you do next?"**
Consolidate the two orchestration scripts into one state machine. Qodo flagged
this on our own PR — `cve-monitor` and `soc-watch` both implement merge-gate
logic, and duplicated logic in the security-critical path is a real divergence
risk. We'd fix that before anyone ran this for real.
