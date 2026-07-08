# spec2prod

**Your prompts are the source code. Stop throwing them away.**

Most people build an app with an AI coding agent, ship the code, and discard the
prompts. But the prompts — the decisions, the intent, the reasons — are what
actually generated the result. spec2prod treats them as the real artifact.

Two Claude Code skills:

- **`/spec-capture`** — run once at the start of a build. Drops a boundary marker
  (`.spec/tags.json`) recording which working directory and moment the build began.
  It does **not** log your prompts — Claude Code already persists every session to
  `~/.claude/projects/<cwd-slug>/*.jsonl`. Capture just marks the boundary. Free.

- **`/spec-distill`** — run at the end (or any checkpoint). Reads the marker,
  extracts a clean **golden-path digest** from the raw sessions (dropping
  dead-ends, backtracks, and design churn), and writes **`SPEC.md`** — a
  machine-executable spec a *cold* Claude agent can run to one-shot a near-clone.
  Then optionally runs a verify loop: cold-build from the spec in a scratch dir,
  diff against the original, patch the spec. The spec is done only when a fresh
  agent reproduces the app from nothing but the spec.

Design/branding enters as an image-inferred slot, not replayed CSS. Provenance
(the raw sessions) stays linked as the audit trail — the clean spec answers
"what to build", the sessions answer "why it did X".

## Layout

```
skills/spec-capture/SKILL.md
skills/spec-distill/SKILL.md
skills/spec-distill/extract-sessions.py   # stdlib-only digest extractor
SPEC.md                                    # the recursive first spec: spec2prod's own spec
```

## Install

Copy the skill dirs into `~/.claude/skills/`. Claude Code exposes each as a slash
command: `/spec-capture`, `/spec-distill`.

## The proof

`SPEC.md` in this repo is spec2prod's own spec. It was distilled from the single
session that built spec2prod, then verified by handing it to a fresh agent with no
other context — which rebuilt the whole tool from the spec alone. The tool's first
clone is the tool.

---
Part of the Vibe2Prod project. MIT, Kierin Dougoud.
