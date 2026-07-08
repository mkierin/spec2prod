# SPEC — spec2prod

> The recursive first spec: this is the spec that rebuilds spec2prod itself.
> Distilled from the Claude Code session that originally built it.

## 0. Runner contract
You are a fresh Claude session rebuilding **spec2prod** from this spec with no
prior context. spec2prod is a pair of Claude Code skills that treat the prompts
of a build as its real source code: capture which sessions built an app, then
distill those sessions into a runnable spec a cold agent can execute to one-shot
a near-clone.

Fill every `{{SLOT}}` first. Execute phases in order. After each phase run its
done-check before continuing. When done, run the Verify loop in §5. Do not claim
success without it.

## 1. Intent
Most people throw away the prompts after building an app and keep only the code.
spec2prod argues the prompts ARE the source code — the decisions and intent that
generated the result. It (a) marks which Claude Code sessions belong to a build,
and (b) distills them into `SPEC.md`, a machine-executable golden-path spec that a
cold Claude agent runs to reproduce the app. Design/branding enters as an
image-inferred slot, not replayed CSS. Built for the Vibe2Prod channel as an
on-camera "watch a cold agent rebuild the app from its spec" demo, and as OSS.

## 2. Architecture
- **Stack:** Claude Code skills (markdown `SKILL.md` with YAML frontmatter) + one
  Python 3 stdlib script. No dependencies.
- **Runtime substrate (the key insight):** Claude Code already persists every
  session to `~/.claude/projects/<cwd-slug>/*.jsonl` — full prompts, tool calls,
  results. `<cwd-slug>` = the absolute cwd with every `/` and `.` replaced by `-`.
  Each line's `message.content` is a string OR an array of blocks with
  `type ∈ {text, thinking, tool_use, tool_result}`. **Exclude `thinking` blocks**
  from the digest — internal deliberation, not intent or action.
  So **capture is nearly free**: you don't log prompts, you just mark a boundary.
- **Two skills, one script:**
  - `skills/spec-capture/SKILL.md` — thin. At build start, writes `.spec/tags.json`
    (app key, intent, cwd, cwd_slug, `started_at` ISO-8601 UTC, optional session
    allowlist). `started_at` is the primary selector for distill.
  - `skills/spec-distill/SKILL.md` — the intelligence. Reads the marker, runs the
    extractor, reconstructs the golden path, writes `SPEC.md`, offers a verify loop.
  - `skills/spec-distill/extract-sessions.py` — deterministic digest extractor.
- **Key decisions (with reasons):**
  - *Skill DIRECTORIES, not single command `.md` files* — because spec-distill must
    carry a helper script alongside its prose; a bare command file can't.
  - *Raw `.jsonl` NEVER enters the model's context; only a distilled digest does* —
    raw sessions are huge and full of tool_result payloads. The Python extractor
    does the reduction deterministically, keeping distillation cheap on big builds.
  - *Distillation is separate from capture* — capture is a stamp (free); all the
    intelligence lives in distill. Don't build a prompt-logger.
  - *Spec consumer = a cold Claude agent, one-shot* — so SPEC.md is phase-gated and
    machine-executable, not a prose essay.
  - *Design = image-inferred slot* — visual/CSS churn is the noisiest part of any
    log and is NOT the golden path; collapse it to `{{DESIGN:image}}` and let the
    rebuild agent regenerate the look from a mockup.
  - *Provenance stays linked* — SPEC.md is the clean artifact; the raw sessions
    remain the audit trail answering "why did it do X".

## 3. Slots (fill before building)
- `{{HOME}}` — user home; skills install to `{{HOME}}/.claude/skills/`.
- `{{PROJECTS_DIR}}` — `{{HOME}}/.claude/projects/` (Claude Code session store).
- `{{DESIGN:image}}` — n/a here (CLI/markdown tool, no UI).

## 4. Build sequence

### Phase 1 — Learn the session store schema
- Do: inspect an existing `~/.claude/projects/<slug>/*.jsonl`. Confirm each line is
  a JSON object with `type` (`user`|`assistant`|`system`|…), `message.content`
  (string OR array of `{type: text|tool_use|tool_result, …}`), `timestamp`,
  `sessionId`, `cwd`, `gitBranch`. Note the slug rule: cwd with `/` and `.` → `-`.
- Done-check: you can name the fields the extractor must read and how user prose is
  distinguished from tool_result plumbing.

### Phase 2 — Write the extractor (`extract-sessions.py`, stdlib only)
- Files: `skills/spec-distill/extract-sessions.py`
- Do: CLI with `--slug` OR `--dir`, plus `--since <iso>` and `--sessions id,id`.
  (Slugs start with `-`, so callers must use the `--slug=<value>` form.) For each
  matching `*.jsonl`: extract ordered USER prose (strip `<system-reminder>` blocks;
  skip messages that are ONLY tool_result), and for ASSISTANT turns emit trimmed
  prose plus a one-line-per-tool summary — tool name + one short arg drawn from
  `file_path|command|path|pattern|url|prompt|description|skill` (first line of
  commands only, truncated to ~80 chars; assistant prose trimmed to ~400).
  Exclude `thinking` blocks. Selection: `--sessions` allowlist wins; else keep
  sessions whose LAST activity ≥ `--since`; else all. **Digest format** (fixed, so
  distillation reads consistently): a top `# SESSION DIGEST` header, then per
  session `## session <id>` + a `_span: <start> → <end> · N turns_` line, then per
  turn `### USER · <ts>` blocks with prose, and assistant turns as
  `**assistant:** <prose>` + a `` `tools:` `` line listing `Name(key=val)`
  one-liners. Emit to stdout. Never print secret values — reference the slot name,
  not the value.
- Done-check: `python3 extract-sessions.py --slug=<a real slug> --sessions=<an id>`
  prints a readable digest that reconstructs that session's user intents in order,
  and `python3 -m py_compile` passes.

### Phase 3 — Write `spec-capture/SKILL.md`
- Files: `skills/spec-capture/SKILL.md`
- Do: frontmatter (`name`, `description` — say clearly it does NOT log prompts, it
  marks a boundary). Steps: ask what's being built (kebab app key + one-line
  intent); derive slug via `pwd | sed 's#[/.]#-#g'`; write `.spec/tags.json` with
  `app,intent,cwd,cwd_slug,started_at (date -u +%Y-%m-%dT%H:%M:%SZ),sessions:[],note`;
  confirm in one line. Note the "busy shared cwd" gotcha → use the `sessions`
  allowlist instead of time filtering.
- Done-check: running it in a project writes a valid `.spec/tags.json` with a real
  UTC `started_at` and the correct slug.

### Phase 4 — Write `spec-distill/SKILL.md`
- Files: `skills/spec-distill/SKILL.md`
- Do: frontmatter. Steps: (0) point at the extractor, forbid reading raw `.jsonl`;
  (1) read `.spec/tags.json` or ask for slug/window; (2) run extractor, capture
  stdout; (3) reconstruct the golden path — drop dead-ends/reversals, keep
  decisions WITH reasons, collapse design churn into `{{DESIGN:image}}`,
  parameterize the surface, order survivors into phases with done-checks, scrub
  secrets; (4) write `SPEC.md` using the §0–§5 skeleton (this file IS that
  skeleton); (5) offer a cold-build verify loop via a fresh subagent fed ONLY the
  spec; (6) report phases/slots/sessions and verify result.
- Done-check: the skill, given a real capture marker, produces a `SPEC.md` with
  numbered phases and explicit slots — no raw transcript echoed.

### Phase 5 — Register & smoke-test
- Do: skills live in `{{HOME}}/.claude/skills/<name>/`; Claude Code exposes each as
  `/<name>`. Verify `/spec-capture` and `/spec-distill` appear. Run the extractor
  against a known session end-to-end.
- Done-check: both skills invocable; extractor round-trips a real session.

## 5. Verify loop
1. Build spec2prod from this spec in a clean directory.
2. Diff against the original: two skill dirs, one extractor, `.spec/tags.json`
   shape, the "raw jsonl never enters context" property, slug rule, `--slug=` form.
3. For each gap, patch the phase or slot that caused it.
4. Repeat until a cold agent reproduces the pair. The spec is DONE only when a
   fresh session one-shots the clone. That cold run is also the YouTube demo shot.

## Provenance
Distilled from session `3ccf9985-e2f4-40f5-aca5-fe2795db69d1` · slug
`-mnt-c-Users-dok` · Vibe2Prod build, 2026-07-08. Raw trail stays local at
`~/.claude/projects/-mnt-c-Users-dok/`. This spec is the golden path; the raw
session answers "why did it do X".
