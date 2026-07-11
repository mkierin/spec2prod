# spec2prod

**Your prompts are the source code. Stop throwing them away.**

Most people build an app with an AI coding agent, ship the code, and discard the
prompts. But the prompts — the decisions, the intent, the reasons — are what
actually generated the result. spec2prod treats them as the real artifact.

Two core Claude Code skills, plus a helper:

- **`/spec-capture`** — drops a boundary marker (`.spec/tags.json`) recording which
  working directory and moment the build began. It does **not** log your prompts —
  Claude Code already persists every session to `~/.claude/projects/<cwd-slug>/*.jsonl`.
  Capture just marks the boundary. Free.
  **You do not normally run this yourself.** Since capture is only a marker, it is
  cheap enough to arm automatically: the `auto-arm` hook drops the marker on the
  first real code edit in any git project (see *Automatic capture* below). Run the
  skill by hand only to re-arm a build or set an explicit intent.

- **`/spec-distill`** — run at the end (or any checkpoint). Reads the marker,
  extracts a clean **golden-path digest** from the raw sessions (dropping
  dead-ends, backtracks, and design churn), and writes **`SPEC.md`** — a
  machine-executable spec a *cold* Claude agent can run to one-shot a near-clone.
  Then optionally runs a verify loop: cold-build from the spec in a scratch dir,
  diff against the original, patch the spec. The spec is done only when a fresh
  agent reproduces the app from nothing but the spec.

- **session-index** (`skills/session-index/`) — a helper for `/spec-distill` on
  large, multi-session builds. Claude Code sessions are stored per working
  directory, so a project spanning weeks can scatter across several folders.
  This catalogs every session by topic (`~/.claude/session-index.jsonl`) so
  `/spec-distill` can select the right sessions by grepping topic/prompt/cwd
  instead of relying on one folder's time window.

Design/branding enters as an image-inferred slot, not replayed CSS. Provenance
(the raw sessions) stays linked as the audit trail — the clean spec answers
"what to build", the sessions answer "why it did X".

## Layout

```
skills/spec-capture/SKILL.md
skills/spec-distill/SKILL.md
skills/spec-distill/extract-sessions.py   # stdlib-only digest extractor
skills/spec-distill/git-anchor.py         # grounds the spec in the built artifact, not just intent
skills/session-index/SKILL.md
skills/session-index/index-sessions.py    # stdlib-only session catalog builder
SPEC.md                                    # the recursive first spec: spec2prod's own spec
```

## Automatic capture (why you never have to remember it)

The first version of this tool was opt-in, and it was not used once after it was
built. The reason is structural, not lazy: `/spec-capture` had to be invoked at the
exact moment you start building — the moment you are thinking about the build and
not about tooling. Tooling loses that competition every time, and a build that was
never armed cannot be distilled afterwards. An opt-in capture tool is a capture tool
that is off.

So both halves are now automatic:

- **`skills/spec-capture/auto-arm.py`** — a `PostToolUse` hook on `Edit|Write`. On the
  first edit to a *code* file inside a *git repo*, it writes `.spec/tags.json` and says
  so once. It skips docs-only edits, non-repo files, `~/.claude`, `/tmp`, scratch dirs,
  `node_modules`, and the bare home directory. Already armed → silent. Any error → fails
  open (a capture marker is never worth breaking an edit over). Intent stays a
  placeholder, because `/spec-distill` infers real intent from the sessions anyway.

- **`skills/spec-distill/nudge.py`** — a `Stop` hook. When an armed project has ≥3
  captured sessions and still has no `SPEC.md`, it suggests `/spec-distill` — once,
  with a 3-day cooldown per project, and never again after the spec exists. Distillation
  is *offered at the moment it becomes worth doing*, rather than remembered days later
  once the context that made it valuable is gone.

Wire them up in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Edit|Write",
        "hooks": [{ "type": "command",
                    "command": "python3 '<path>/spec2prod/skills/spec-capture/auto-arm.py'" }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command",
                    "command": "python3 '<path>/spec2prod/skills/spec-distill/nudge.py'" }] }
    ]
  }
}
```

Design rule, learned the hard way: **capture must be ambient (on by default, no
decision), and distillation must be offered (the tool notices), never remembered.**
Adoption is the acceptance test — a tool you built and abandoned is a failed tool.

## Install

Copy the skill dirs into `~/.claude/skills/`. Claude Code exposes each as a slash
command: `/spec-capture`, `/spec-distill`. `session-index` is a plain script,
invoked directly (see `skills/session-index/SKILL.md`).

## The proof

`SPEC.md` in this repo is spec2prod's own spec. It was distilled from the single
session that built spec2prod, then verified by handing it to a fresh agent with no
other context — which rebuilt the whole tool from the spec alone. The tool's first
clone is the tool.

---
Part of the Vibe2Prod project. Free, MIT licensed (see [LICENSE](LICENSE)) —
Kierin Dougoud.
