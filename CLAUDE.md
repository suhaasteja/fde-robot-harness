See [AGENTS.md](AGENTS.md) for everything: what this repo is, setup, how to run it
(with or without the robot), the TrueForge integration, and the rules.

Two things worth not learning the hard way:

- **Do not upgrade the conversation app past v0.8.0 or the SDK past 1.9.x.** Both
  pins are deliberate and both failures are silent. See Rules 1 and 2.
- **Never `pip install` without targeting the venv explicitly** — the default shell
  is conda `base` and installs clobber it. See Rule 3.
