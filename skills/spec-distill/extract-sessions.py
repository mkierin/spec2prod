#!/usr/bin/env python3
"""
extract-sessions.py — turn raw Claude Code session .jsonl logs into a compact,
model-readable DIGEST for spec distillation.

The digest is the ONLY thing the distiller LLM reads. Raw .jsonl never enters
context: it's noisy, huge, and full of tool_result payloads. This script keeps
just the golden-path signal — ordered user intents + a one-line summary of what
the assistant DID between them (tool calls), with a little assistant prose.

Usage:
  extract-sessions.py --slug <cwd-slug> [--since <iso8601>] [--sessions id,id]
  extract-sessions.py --dir <project-dir> [--since ...] [--sessions ...]

Selection:
  - --dir / --slug  points at ~/.claude/projects/<slug>/
  - --since         keep only sessions whose LAST activity is >= this time
  - --sessions      explicit comma-separated sessionId allowlist (overrides --since)

Output: markdown digest to stdout. Feed it to the distiller.
"""
import argparse, json, os, sys, glob
from datetime import datetime

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")

# tool_use inputs we surface as the "what happened" one-liner. Everything else
# collapses to just the tool name.
ARG_KEYS = ["file_path", "command", "path", "pattern", "url", "prompt", "description", "skill"]


def parse_iso(s):
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def load_lines(fp):
    out = []
    with open(fp, "r", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def strip_reminders(text):
    """Drop <system-reminder>...</system-reminder> blocks — harness noise, not user intent."""
    while "<system-reminder>" in text and "</system-reminder>" in text:
        a = text.index("<system-reminder>")
        b = text.index("</system-reminder>") + len("</system-reminder>")
        text = (text[:a] + text[b:])
    return text.strip()


def user_text(msg):
    """Extract real user prose. Skip messages that are ONLY tool_result (they're
    tool plumbing, not a human turn)."""
    content = msg.get("message", {}).get("content")
    if isinstance(content, str):
        return strip_reminders(content)
    if isinstance(content, list):
        parts = []
        only_tool_result = True
        for it in content:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "text":
                only_tool_result = False
                parts.append(it.get("text", ""))
            elif it.get("type") != "tool_result":
                only_tool_result = False
        if only_tool_result:
            return ""
        return strip_reminders("\n".join(p for p in parts if p))
    return ""


def short(s, n=140):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def assistant_summary(msg):
    """Return (prose, [tool one-liners]) for an assistant turn."""
    content = msg.get("message", {}).get("content")
    prose, tools = [], []
    if isinstance(content, str):
        prose.append(content)
    elif isinstance(content, list):
        for it in content:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "text":
                prose.append(it.get("text", ""))
            elif it.get("type") == "tool_use":
                name = it.get("name", "tool")
                inp = it.get("input", {}) or {}
                arg = ""
                for k in ARG_KEYS:
                    if k in inp and inp[k]:
                        v = inp[k]
                        if k == "command":
                            v = str(v).splitlines()[0] if str(v).splitlines() else v
                        arg = f"{k}={short(v, 80)}"
                        break
                tools.append(f"{name}({arg})" if arg else name)
    return strip_reminders("\n".join(p for p in prose if p)), tools


def digest_session(fp):
    rows = load_lines(fp)
    if not rows:
        return None, None, None
    sid = None
    started = ended = None
    turns = []  # (role, timestamp, text, tools)
    for r in rows:
        t = r.get("type")
        ts = r.get("timestamp")
        if r.get("sessionId"):
            sid = r["sessionId"]
        if ts:
            dt = parse_iso(ts)
            if dt:
                started = dt if not started else min(started, dt)
                ended = dt if not ended else max(ended, dt)
        if t == "user":
            txt = user_text(r)
            if txt:
                turns.append(("user", ts, txt, []))
        elif t == "assistant":
            prose, tools = assistant_summary(r)
            if prose or tools:
                turns.append(("assistant", ts, prose, tools))
    return sid, (started, ended), turns


def render(sid, span, turns):
    lines = []
    s = span[0].isoformat() if span and span[0] else "?"
    e = span[1].isoformat() if span and span[1] else "?"
    lines.append(f"## session {sid}")
    lines.append(f"_span: {s} → {e} · {len(turns)} turns_\n")
    for role, ts, text, tools in turns:
        tstamp = (ts or "")[:19]
        if role == "user":
            lines.append(f"### USER · {tstamp}")
            lines.append(text.strip())
            lines.append("")
        else:
            if text.strip():
                lines.append(f"**assistant:** {short(text, 400)}")
            if tools:
                lines.append("`tools:` " + ", ".join(tools))
            lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--dir")
    ap.add_argument("--since")
    ap.add_argument("--sessions")
    args = ap.parse_args()

    proj = args.dir or (os.path.join(PROJECTS, args.slug) if args.slug else None)
    if not proj or not os.path.isdir(proj):
        print(f"ERROR: project dir not found: {proj}", file=sys.stderr)
        sys.exit(1)

    since = parse_iso(args.since)
    allow = set(x.strip() for x in args.sessions.split(",")) if args.sessions else None

    files = sorted(glob.glob(os.path.join(proj, "*.jsonl")), key=os.path.getmtime)
    selected = []
    for fp in files:
        sid, span, turns = digest_session(fp)
        if not sid or not turns:
            continue
        if allow is not None:
            if sid not in allow:
                continue
        elif since is not None:
            last = span[1] if span else None
            if not last or last < since:
                continue
        selected.append((sid, span, turns))

    if not selected:
        print("(no matching sessions)", file=sys.stderr)
        sys.exit(2)

    print("# SESSION DIGEST")
    print(f"_project: {proj} · {len(selected)} session(s)_\n")
    total_user = 0
    for sid, span, turns in selected:
        total_user += sum(1 for r in turns if r[0] == "user")
        print(render(sid, span, turns))
        print("\n---\n")
    print(f"_total user turns across sessions: {total_user}_")


if __name__ == "__main__":
    main()
