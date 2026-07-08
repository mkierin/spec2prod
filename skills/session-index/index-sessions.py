#!/usr/bin/env python3
"""
index-sessions.py — build a searchable catalog of ALL Claude Code sessions.

Sessions are stored per-working-directory, so a project's sessions can be
scattered across many folders. This walks every ~/.claude/projects/**/*.jsonl,
pulls one row per session — id, date span, cwd, branch, aiTitle (topic), first
real user prompt, turn count — and writes a catalog you filter by TOPIC, not by
folder.

Usage:
  index-sessions.py                          # rebuild catalog -> ~/.claude/session-index.jsonl
  index-sessions.py --grep hyprswarm         # rebuild + print matching rows (title/prompt/cwd)
  index-sessions.py --grep hyprswarm --md    # ... as a markdown table
  index-sessions.py --since 2026-06-01       # only sessions active on/after date
  index-sessions.py --no-build --grep qlik   # query the existing catalog without rescanning

Match is case-insensitive over aiTitle + first prompt + cwd. Combine filters.
"""
import argparse, json, os, sys, glob
from datetime import datetime

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")
CATALOG = os.path.join(HOME, ".claude", "session-index.jsonl")


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    except Exception:
        return None


def strip_reminders(t):
    while "<system-reminder>" in t and "</system-reminder>" in t:
        a = t.index("<system-reminder>")
        b = t.index("</system-reminder>") + len("</system-reminder>")
        t = t[:a] + t[b:]
    return t.strip()


def first_prompt(msg):
    """Real user prose, or '' for tool-result-only / command-plumbing turns."""
    c = msg.get("message", {}).get("content")
    txt = ""
    if isinstance(c, str):
        txt = c
    elif isinstance(c, list):
        parts, only_tr = [], True
        for it in c:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "text":
                only_tr = False
                parts.append(it.get("text", ""))
            elif it.get("type") != "tool_result":
                only_tr = False
        if only_tr:
            return ""
        txt = "\n".join(p for p in parts if p)
    txt = strip_reminders(txt)
    # skip slash-command scaffolding lines
    lines = [l for l in txt.splitlines() if l.strip() and not l.strip().startswith("<command")]
    txt = "\n".join(lines).strip()
    return txt


def scan_session(fp):
    sid = cwd = branch = title = None
    started = ended = None
    first = ""
    user_turns = 0
    try:
        with open(fp, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("sessionId"):
                    sid = r["sessionId"]
                if r.get("cwd"):
                    cwd = r["cwd"]
                if r.get("gitBranch"):
                    branch = r["gitBranch"]
                if r.get("type") == "ai-title" and r.get("aiTitle"):
                    title = r["aiTitle"]
                ts = parse_iso(r.get("timestamp"))
                if ts:
                    started = ts if not started else min(started, ts)
                    ended = ts if not ended else max(ended, ts)
                if r.get("type") == "user":
                    p = first_prompt(r)
                    if p:
                        user_turns += 1
                        if not first:
                            first = p
    except Exception:
        return None
    if not sid:
        sid = os.path.splitext(os.path.basename(fp))[0]
    return {
        "id": sid,
        "date": started.date().isoformat() if started else None,
        "start": started.isoformat() if started else None,
        "end": ended.isoformat() if ended else None,
        "cwd": cwd,
        "branch": branch,
        "title": title or "",
        "first_prompt": (first[:200] + "…") if len(first) > 200 else first,
        "user_turns": user_turns,
        "file": fp,
    }


def _merge(a, b):
    """Fold fragment b into session a (same sessionId across resumes/sidechains)."""
    for k in ("start",):
        if b.get(k) and (not a.get(k) or b[k] < a[k]):
            a[k] = b[k]
            a["date"] = b.get("date") or a.get("date")
    for k in ("end",):
        if b.get(k) and (not a.get(k) or b[k] > a[k]):
            a[k] = b[k]
    for k in ("title", "first_prompt", "cwd", "branch"):
        if not a.get(k) and b.get(k):
            a[k] = b[k]
    # keep earliest real first_prompt
    if b.get("first_prompt") and b.get("start") and (not a.get("start") or b["start"] <= a["start"]):
        a["first_prompt"] = b["first_prompt"] or a.get("first_prompt")
    a["user_turns"] = a.get("user_turns", 0) + b.get("user_turns", 0)
    a["fragments"] = a.get("fragments", 1) + 1
    return a


def build():
    byid = {}
    for fp in glob.glob(os.path.join(PROJECTS, "**", "*.jsonl"), recursive=True):
        row = scan_session(fp)
        if not row:
            continue
        row["fragments"] = 1
        sid = row["id"]
        byid[sid] = _merge(byid[sid], row) if sid in byid else row
    rows = list(byid.values())
    rows.sort(key=lambda r: r.get("start") or "", reverse=True)
    with open(CATALOG, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def load():
    if not os.path.exists(CATALOG):
        return []
    return [json.loads(l) for l in open(CATALOG) if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grep")
    ap.add_argument("--since")
    ap.add_argument("--branch")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()

    rows = load() if args.no_build else build()
    if not args.no_build:
        print(f"indexed {len(rows)} sessions -> {CATALOG}", file=sys.stderr)

    g = args.grep.lower() if args.grep else None
    since = args.since
    out = []
    for r in rows:
        if g:
            hay = f"{r.get('title','')} {r.get('first_prompt','')} {r.get('cwd','')}".lower()
            if g not in hay:
                continue
        if since and (r.get("date") or "") < since:
            continue
        if args.branch and args.branch != (r.get("branch") or ""):
            continue
        out.append(r)

    if g or since or args.branch:
        if args.md:
            print("| date | topic | turns | id | cwd |")
            print("|---|---|---|---|---|")
            for r in out:
                cwd = (r.get("cwd") or "").replace("/mnt/d/Cascade/Qlik KT/", "…/")
                print(f"| {r.get('date','?')} | {r.get('title','')[:60]} | {r.get('user_turns',0)} | `{r['id'][:8]}` | {cwd} |")
        else:
            for r in out:
                print(f"{r.get('date','?')}  {r['id'][:8]}  turns={r.get('user_turns',0):<3}  {r.get('title','')[:70]}")
        print(f"\n{len(out)} match(es)" + (f" for '{args.grep}'" if g else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
