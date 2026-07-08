---
name: spec-capture
description: Start capturing an app build for later spec distillation. Stamps a lightweight marker (.spec/tags.json) that records which cwd and which point in time this build began, so /spec-distill knows exactly which Claude sessions to synthesize into a runnable SPEC.md. Run this ONCE at the start of building something you'll want to clone or turn into a YouTube demo. Near-zero cost — it does not log prompts (Claude Code already writes every session to disk); it just tags the boundary.
---

# Spec Capture

The premise: the prompts that built an app are the real source code. Claude Code
already persists every session to `~/.claude/projects/<cwd-slug>/*.jsonl` — full
prompts, tool calls, results. So capture is nearly free. This skill does NOT
re-log anything. It drops a **boundary marker** so that later, `/spec-distill`
can select exactly the sessions belonging to *this* build and no others.

Pair: `/spec-capture` (now, at build start) → `/spec-distill` (later, at build end).

## Step 1 — Confirm what's being captured

Ask the user one line if not obvious from context: **"What are we building?"**
Get a short kebab-case app key (e.g. `spec-driven-design`, `budget-tracker`) and
a one-sentence intent. Don't over-interrogate — the intent gets refined at distill
time from the actual sessions.

## Step 2 — Resolve the cwd slug

The session logs for the current project live under a slug = cwd with `/` and `.`
replaced by `-`. Derive it:

```bash
pwd
SLUG=$(pwd | sed 's#[/.]#-#g')
echo "slug: $SLUG"
ls -dt ~/.claude/projects/"$SLUG"/ 2>/dev/null && echo "session dir exists" || echo "WARN: no session dir yet (fine — it appears once this session writes)"
```

If the session dir doesn't exist yet, that's fine on a brand-new project — it's
created as soon as the session persists. Record the slug anyway.

## Step 3 — Write the marker

Write `.spec/tags.json` **in the project working directory** (the app's own repo,
so the provenance ships with the code):

```bash
mkdir -p .spec
```

Then write `.spec/tags.json` with this shape (fill the values; use the real
current timestamp from `date -u +%Y-%m-%dT%H:%M:%SZ`):

```json
{
  "app": "<kebab-app-key>",
  "intent": "<one sentence>",
  "cwd": "<absolute pwd>",
  "cwd_slug": "<slug from step 2>",
  "started_at": "<iso8601 UTC>",
  "sessions": [],
  "note": "<optional: what phase / branch this build covers>"
}
```

`started_at` is the primary selector: `/spec-distill` picks every session in the
slug dir whose activity falls at or after this time. That naturally spans a
multi-day, multi-session build — exactly the point. Leave `sessions` empty; it's
an optional manual allowlist for when several unrelated things share one cwd.

## Step 4 — Confirm

Tell the user in one line: capture is armed for `<app>`, started at `<time>`,
watching slug `<slug>`. From here every session in this directory is part of the
record. When the build is done (or at any checkpoint), run `/spec-distill` to
synthesize the runnable spec.

## Notes / gotchas

- **Multiple builds in one cwd**: `started_at` filtering assumes this cwd is
  mostly this build. If you interleave unrelated work in the same directory, fill
  the `sessions` allowlist at distill time instead (session IDs are the `.jsonl`
  filenames). Flag this to the user if the cwd is a busy shared dir like a home
  folder.
- **Don't commit secrets**: `.spec/tags.json` holds no secrets, but the sessions
  it points at may reference paths/keys. `/spec-distill` scrubs those into slots;
  the raw `.jsonl` stays only on your machine, never in the spec.
- This skill is idempotent-ish: re-running it resets `started_at`. Only re-run if
  you deliberately want to start the capture window over.
