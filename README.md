# fde-robot-harness

Start/stop tooling for the Reachy Mini conversation app.

The app will not run from the Reachy Mini Control dashboard — that path is broken
upstream (see [Why not the dashboard](#why-not-the-dashboard)). It runs from a
pinned venv instead, and this repo wraps that in a few commands.

## Prerequisites

1. **Reachy Mini Control.app must be running.** It hosts the daemon on
   `127.0.0.1:8000` / `:8443`. The app cannot connect without it.
2. A pinned venv at `~/reachy-conv` containing **conversation app 0.10.0** and
   **reachy-mini 1.9.0**. Override the location with `REACHY_VENV` if it lives
   elsewhere.

Verify both with `make doctor`.

## Commands

From this directory:

```bash
make start      # launch in the background, logged to logs/app.log
make stop       # graceful shutdown
make restart
make status     # running? daemon up? which versions?
make doctor     # verify pins, and whether the dashboard is usable yet
make logs       # follow the log
make panel      # web control panel on http://127.0.0.1:7870
```

The script takes extra flags that `make` doesn't pass through:

```bash
bin/reachy-app start --no-camera   # audio only
bin/reachy-app start --ui          # web UI at http://127.0.0.1:7860/
bin/reachy-app start --debug       # verbose logging
```

## Control panel

```bash
bin/reachy-app start --ui     # --ui is required for the prompt editor
make panel                    # http://127.0.0.1:7870
```

Gives you, in one page: **system prompt** editing (save + apply live, no restart),
**conversation transcript**, **speaker/mic volume**, mic **mute**, and the robot's
**saved memory facts** with a clear button.

There's no single API behind this — the panel stitches together three sources,
which is why it exists rather than just linking you to a built-in page:

| What | Where it actually lives |
|---|---|
| Volume, mic gain, test sound | daemon on `:8000`, under `/api/…` |
| System prompt, voices, mute | the app on `:7860`, under `/api/v1/…` — **only with `--ui`** |
| Transcript | parsed from `logs/app.log` |
| Saved facts | `~/.local/share/reachy_mini_conversation_app/memory.v1.json` |

Volume and transcript work whenever the daemon is up. The prompt editor greys
itself out if the app wasn't started with `--ui`.

### Saved memory facts

The app has `remember`/`forget` tools and persists what it learns to
`memory.v1.json`. Those facts are injected into **every** session, so a stale one
(an old nickname, say) keeps resurfacing long after the conversation that created
it — it is not the system prompt, and restarting won't clear it. The panel lists
them and clears them; cleared facts are backed up to `memory.v1.json.bak` first.

By hand:

```bash
cat ~/.local/share/reachy_mini_conversation_app/memory.v1.json
```

### Known quirk: volume rounding

macOS quantises system volume to 16 steps, so setting 60 reads back as 59. Not a
bug in the panel — the daemon faithfully reports what CoreAudio stored.

## Doing it by hand

If you'd rather not use the harness at all, this is the whole thing:

```bash
# start (foreground)
~/reachy-conv/bin/reachy-mini-conversation-app

# stop
Ctrl-C
```

Two rules if you go manual:

- **Always launch by absolute path.** Do not `conda activate` first, and do not
  rely on `PATH`. Your shell sits in conda `base`, and anaconda's glib is older
  than 2.80 — it shadows GStreamer's copy and the app dies with
  `Symbol not found: _g_once_init_enter_pointer`.
- **To stop it from another shell, use SIGTERM and target the Python process.**
  Two gotchas here, both measured:
  - `pkill -f reachy-mini-conversation-app` also matches the shell wrapper and can
    leave the real process alive. Find the Python pid with
    `pgrep -f "reachy-conv/bin/reachy-mini-conversation-app"`.
  - **SIGINT does nothing to a backgrounded app** — it sat alive for 60s with
    nothing logged. Ctrl-C only works when *you* ran it in the foreground. From
    another shell, `kill -TERM <pid>` — that exits in about a second.

  The harness tracks the pid in `.run/app.pid` and uses SIGTERM, so both gotchas
  are handled for you.

## Health checks

```bash
# daemon listening?
lsof -nP -iTCP -sTCP:LISTEN | grep -E ':8000|:8443'

# what's actually installed in the venv?
~/reachy-conv/bin/python -c \
  "import importlib.metadata as m; print(m.version('reachy-mini'), m.version('reachy-mini-conversation-app'))"
# expect: 1.9.0 0.10.0
```

A healthy startup ends with `Using LOCAL backend (GStreamer IPC camera + GStreamer
audio).` and then goes quiet — silence there is normal, it's listening on the mic.

## Why not the dashboard

The conversation app moved to a JSON-RPC transport on 2026-07-20. Every release
after that (v1.0.0, v1.0.1) requires `reachy-mini>=1.10.0rc5` for the
`reachy_mini.io.jsonrpc` module. The dashboard installs v1.0.1, but the Control
app bundles SDK 1.9.0, which has no such module — so it installs fine and then
dies at launch:

```
ModuleNotFoundError: No module named 'reachy_mini.io.jsonrpc'
```

Reinstalling never fixes it. It's version skew, not a broken install. v0.10.0
(2026-07-15) is the last release before that migration, which is why it's pinned.

**Don't force-upgrade the SDK inside the Control app's own venv.** The daemon
ships as part of the SDK, and 1.10's daemon speaks a different control protocol
than the current Control app expects — you'd trade a broken conversation app for
a broken Control app.

### When can we go back?

Watch the SDK the **Control app bundles**, not the newest version on PyPI:

```bash
"$HOME/Library/Application Support/com.pollen-robotics.reachy-mini/.venv/bin/python3" \
  -c "import importlib.metadata as m; print(m.version('reachy-mini'))"
```

`make doctor` runs this and interprets it. When it reports ≥1.10.0, the dashboard
should work again and the v0.10.0 pin can be dropped.

## Upstream status

Checked 2026-08-29:

| | |
|---|---|
| Conversation app `main` | `531baaa` — identical to `v1.0.1` (2026-08-19) |
| New commits since v1.0.1 | **none** |
| Its SDK requirement | `reachy-mini>=1.10.0rc5` (unchanged) |
| Stable SDK on PyPI | **1.10.0** ✅ |
| SDK the Control app bundles | **1.9.0** ❌ |

Nothing to pull. One thing did change, though: stable 1.10.0 now satisfies
`>=1.10.0rc5`, so the app's dependency is reachable from a stable release for the
first time. The only remaining blocker is the Control app's 1.9.0 daemon. Whether
a 1.10 client can drive a 1.9 daemon is **untested** — try it in a throwaway venv,
never in `~/reachy-conv`.
