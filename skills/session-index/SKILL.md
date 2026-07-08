---
name: session-index
description: Build and search a catalog of ALL your Claude Code sessions by TOPIC, not by folder. Sessions are stored per working-directory, so one project's work scatters across many folders (e.g. HyprSwarm runs from the home dir, the bot dir, and the dashboard dir). This harvests every ~/.claude/projects/**/*.jsonl into one searchable index — id, date, topic (aiTitle), first prompt, cwd, turn count — merged per session across resume/sidechain fragments. Use when the user asks "find all my <X> sessions", "how many sessions on <project>", "list what I worked on since <date>", or before /spec-distill on a big multi-session project.
---

# Session Index

Claude Code writes every session to `~/.claude/projects/<cwd-slug>/*.jsonl`, and
each session carries an `aiTitle` (auto-generated topic). But sessions are grouped
by working directory, so a project spanning weeks lives in several folders and you
can't find it by path. This builds a topic index you grep instead.

Tool: `~/.claude/skills/session-index/index-sessions.py` (Python 3, stdlib only).
Catalog is written to `~/.claude/session-index.jsonl` (one JSON row per session).

## Usage

```bash
# rebuild the catalog (scans all sessions; ~15s for ~1700 files)
python3 ~/.claude/skills/session-index/index-sessions.py

# find every session on a topic (matches aiTitle + first prompt + cwd)
python3 ~/.claude/skills/session-index/index-sessions.py --grep hyprswarm

# markdown table, only recent
python3 ~/.claude/skills/session-index/index-sessions.py --grep qlik --since 2026-06-01 --md

# query the existing catalog WITHOUT rescanning (fast)
python3 ~/.claude/skills/session-index/index-sessions.py --no-build --grep newo
```

Each row: `id, date, start, end, cwd, branch, title, first_prompt, user_turns,
fragments, file`. Fragments = how many `.jsonl` pieces merged into that session
(resumes/sidechains).

## How to answer common asks

- **"find all my X sessions"** → run with `--grep X`. Report the count and the
  table (dates + topics). Note if they span multiple cwds.
- **"how much did I work on X"** → `--grep X`, sum `user_turns`, give date range.
- **"what did I do since <date>"** → `--since <date>` (optionally `--grep`).
- **Feeding /spec-distill a big project** → run `--grep <project> --md`, collect
  the matching session ids, and hand that id list to `/spec-distill` as its
  `--sessions=` allowlist. This is how a 20+-session, month-long project gets
  distilled by TOPIC across scattered folders instead of by one folder's
  `started_at` window.

## Notes

- The index is a cache. Rebuild it when you want it current (it's cheap). `/wrapup`
  can refresh it once per session so it stays warm without a manual rebuild.
- Empty-title rows with `user_turns` low are usually tool/handoff stubs — real
  work has a topic and multiple turns.
- Match is case-insensitive substring over title+first_prompt+cwd. For a project
  with an ambiguous name, grep the cwd too (e.g. `--grep hyperswarm` vs the
  product spelling).
