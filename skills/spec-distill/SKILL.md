---
name: spec-distill
description: Synthesize a runnable, machine-executable SPEC.md from the Claude Code sessions that built an app. Reads the boundary marker left by /spec-capture (or a slug/time range you give), extracts a clean golden-path digest from the raw session .jsonl (dropping dead-ends, backtracks, and design churn), then writes SPEC.md — a spec a COLD Claude session can run to one-shot a near-clone. Optionally runs a verify loop: cold-build from the spec in a scratch dir, diff against the original, patch the spec. Run at the end of a build (or any checkpoint). Pairs with /spec-capture.
---

# Spec Distill

Turn the raw session log of a build into `SPEC.md` — a layered, executable spec
that a fresh Claude session (with none of this conversation's memory) can run to
reproduce a near-clone of what was built. Design enters as an image-inferred slot,
not replayed CSS. Provenance (the raw sessions) stays linked as the audit trail.

**Consumer of the spec = a Claude agent, one-shot.** Optimize for machine
execution: explicit phases, done-checks, filled-in-order. Not a prose essay.

## Step 0 — Load the extractor

The deterministic digest extractor lives beside this skill:
`~/.claude/skills/spec-distill/extract-sessions.py`. It reads raw `.jsonl` and
emits a compact markdown digest — ordered USER intents + one-line summaries of
what the assistant DID (tool calls) + trimmed assistant prose. **Only the digest
enters your context**, never the raw jsonl (it's huge and full of tool-result
noise). Do not read `.jsonl` files directly.

## Step 1 — Select the sessions

Find the capture marker in the project working dir:

```bash
cat .spec/tags.json 2>/dev/null || echo "NO MARKER"
```

- **Marker found** → use its `cwd_slug`, `started_at`, and (if non-empty)
  `sessions` allowlist.
- **No marker** → ask the user for the app, then derive the slug from cwd
  (`pwd | sed 's#[/.]#-#g'`) and pick a time window, or list recent sessions:
  `ls -lt ~/.claude/projects/<slug>/*.jsonl | head`.
- **Large / multi-folder project (20+ sessions over weeks)** → do NOT rely on one
  slug + `started_at`; the sessions are scattered across folders (work often runs
  from the home dir, not the project folder). Use the **session index** to select
  by topic:
  ```bash
  python3 ~/.claude/skills/session-index/index-sessions.py --grep <project> --md
  ```
  Collect the matching session ids and pass them to the extractor as an explicit
  `--sessions=id1,id2,...` allowlist (Step 2). This is the correct path for any
  build that spanned more than a couple of sessions.

## Step 2 — Extract the digest

Run the extractor (note the `=` form — slugs start with `-`):

```bash
python3 ~/.claude/skills/spec-distill/extract-sessions.py \
  --slug=<cwd_slug> --since='<started_at>'
# or, with an explicit allowlist:
python3 ~/.claude/skills/spec-distill/extract-sessions.py \
  --slug=<cwd_slug> --sessions=<id1>,<id2>
```

Capture stdout. This is your source material for WHY. Skim it end to end before
writing anything.

## Step 2.5 — Anchor to git (the WHAT)

The digest is intent only. If the build is a git repo, ground it in the artifact —
otherwise the spec will read plausibly and rebuild nothing. Run:

```bash
python3 ~/.claude/skills/spec-distill/git-anchor.py --repo <repo> \
  --sessions=<same ids you distilled>     # or --grep <project> / --since <date>
```

This emits a **build ledger** (each commit = a verified phase boundary, attributed
to the session that caused it) and a **final manifest** (the shipped file tree with
a per-file outline of its defs/classes/headers + line counts). Capture stdout.

Now you have both halves: the digest says *why*, the ledger+manifest say *what and
when*. Distill phases from the COMMITS (real done-states), and pull the reason for
each from the session digest. If the project isn't under git, say so — the spec is
weaker (intent-only) and you should lean harder on the verify loop.

## Step 3 — Reconstruct the golden path

From the digest, mentally rebuild what SUCCEEDED, discarding the journey noise.
This is the core intelligence of the skill. Apply these rules:

1. **Drop dead-ends & reversals.** If the user said "no, do it differently" or a
   file was written then rewritten, keep only the final form. The clone shouldn't
   walk into the same wall.
2. **Keep decisions WITH their reasons.** "Used skill dirs not command files so
   the distiller can carry a script" — the reason is what lets a rebuild handle
   situations the original run never hit. Reasons > steps.
3. **Collapse design/CSS churn into a slot.** Iterative visual tweaks are the
   noisiest part of any log and are NOT the golden path. Replace the entire run of
   them with one `{{DESIGN:image}}` slot. The rebuild agent regenerates the look
   from a mockup; it does not replay 40 style edits.
4. **Parameterize the surface.** Anything that's a user choice — data source, API
   keys, branding, copy, target host, port — becomes a `{{SLOT}}`, never baked in.
5. **Order the survivors into phases — anchored to commits.** When you have a git
   ledger, each commit IS a phase: its files are the phase's deliverable, its
   subject is the goal, and "this commit exists and matches the manifest" is a real
   done-check. Merge trivial fixup commits; split a giant commit only if the
   session shows distinct sub-goals. Each phase = goal + files + done-check.
6. **Scrub secrets.** Never carry a key/token value into the spec. Reference the
   slot (`{{GROQ_API_KEY}}`) and where the original pulled it from, not the value.

## Step 4 — Write SPEC.md

Write `SPEC.md` in the project working dir (ships with the code). Use this exact
skeleton:

```markdown
# SPEC — <app>

## 0. Runner contract
You are a fresh Claude session rebuilding "<app>" from this spec with no prior
context. Fill every {{SLOT}} first (ask the user or infer from provided image).
Execute phases in order. After each phase, run its done-check before continuing.
Do not skip verification. When done, run the Verify loop in §5.

## 1. Intent
<3–5 lines: what it does, who for, the north star>

## 2. Architecture
- Stack: <languages, frameworks, runtime>
- Data model / key entities: <...>
- Module map: <files/dirs and their responsibility>
- Key decisions (with reasons):
  - <decision> — because <reason>
  - ...

## 3. Slots (fill before building)
- `{{DESIGN:image}}` — hand a screenshot/mockup; infer the design system from it.
- `{{DATA_SOURCE}}` — <what/where>
- `{{SECRET:NAME}}` — <what it's for; where the original sourced it>
- ... (one line each)

## 4. Build sequence
### Phase 1 — <goal>
- Files: <...>
- Do: <the essential actions, distilled — not the raw transcript>
- Done-check: <observable proof it worked, prefer real data>
### Phase 2 — ...
...

## 5. Verify loop (scored)
1. Build from this spec in a clean directory.
2. Diff against §6 Manifest: for each listed file, did the cold build produce it,
   with units (defs/classes/headers) matching by name/role? Run any test commands.
3. **Score = fraction of manifest files reproduced with a matching outline.** List
   per-file misses and failed tests explicitly. Do not round up.
4. For each gap, patch the phase or slot that caused it. Repeat. The spec is DONE
   only when a fresh agent reaches the target score (aim 100%; state the number).

## 6. Manifest (golden anchor — paste from git-anchor.py output)
<the final-manifest block: every shipped file + its outline + line count. This is
what §5 scores against. If no git repo, hand-list the key files and their roles.>

## Provenance
Distilled from sessions: <session ids> · slug <cwd_slug> · captured <started_at>.
Git ledger: <N commits, first..last hash>. Raw trail stays local at
~/.claude/projects/<cwd_slug>/. This spec is the golden path; the raw sessions
answer "why did it do X", the commits answer "what shipped when".
```

Keep phases tight and executable. If the build was large, it's better to have 8
crisp phases with real done-checks than 30 that echo the transcript.

## Step 5 — Offer the verify loop (optional but recommended)

Ask the user: run a cold-build verification now? If yes:

1. `mkdir -p /tmp/claude-*/…/spec-verify-<app>` (use the session scratchpad).
2. Spawn a **fresh subagent** (Task, model sonnet) whose entire prompt is the
   contents of `SPEC.md` and nothing else — no hints from this conversation. It
   must build only from the spec.
3. Diff its output against the original. Record gaps.
4. Score the rebuild against §6 Manifest (fraction of files reproduced with a
   matching outline; run any test commands). Report the number, not a vibe.
5. Patch `SPEC.md` for each gap (missing decision, ambiguous phase, unmarked slot).
   Note what you changed, then re-run until the score is satisfactory.
6. Report: cold-build score (e.g. "8/8 files, 2/2 tests"), what was missing before
   patching. This is the honest proof — and the exact footage the YouTube demo
   needs ("watch it hit 100%").

Do NOT claim the spec works without this loop, or say plainly that it's unverified.

## Step 6 — Report

Tell the user: SPEC.md written (path), N phases, M slots, distilled from K
sessions. Whether the verify loop ran and its result. One line on the strongest
and weakest phase.

## Notes

- The spec is the clean artifact; the raw `.jsonl` sessions are the audit trail —
  keep both. Don't delete sessions.
- If the digest is thin (few user turns), say so — a spec is only as good as the
  trail. Suggest capturing more deliberately next time.
- Model routing: extraction + writing SPEC.md is fine in the main thread if
  context is loaded; the cold-build verify subagent uses sonnet.
