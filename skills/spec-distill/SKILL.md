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

## Step 2 — Extract the digest

Run the extractor (note the `=` form — slugs start with `-`):

```bash
python3 ~/.claude/skills/spec-distill/extract-sessions.py \
  --slug=<cwd_slug> --since='<started_at>'
# or, with an explicit allowlist:
python3 ~/.claude/skills/spec-distill/extract-sessions.py \
  --slug=<cwd_slug> --sessions=<id1>,<id2>
```

Capture stdout. This is your source material. Skim it end to end before writing
anything — you're reconstructing the golden path from the real trail.

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
5. **Order the survivors into phases.** Each phase = a goal + the files it touches
   + a done-check (how a cold agent knows it worked, ideally against real data).
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

## 5. Verify loop
1. Build from this spec in a clean directory.
2. Diff the result against the original (structure, behavior, key outputs).
3. For each gap, patch the phase or slot that caused it.
4. Repeat until a cold run reproduces the app. The spec is DONE only when a fresh
   agent one-shots the clone.

## Provenance
Distilled from sessions: <session ids> · slug <cwd_slug> · captured <started_at>.
Raw trail stays local at ~/.claude/projects/<cwd_slug>/. This spec is the golden
path; the raw sessions answer "why did it do X".
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
4. Patch `SPEC.md` for each gap (missing decision, ambiguous phase, unmarked
   slot). Note what you changed.
5. Report: did a cold agent reproduce it? What was missing? This is the honest
   proof — and the exact footage the YouTube demo needs.

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
