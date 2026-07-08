#!/usr/bin/env python3
"""
git-anchor.py — ground a spec in the ARTIFACT, not just the prompts.

The session digest gives WHY (intent). Git gives WHAT (verified final state) and
WHEN (real phase boundaries). This tool cross-references the two:

  - reads git log (commits, dates, files changed) from a repo
  - attributes each commit to the session(s) active at that time, using the
    session catalog (~/.claude/session-index.jsonl from /session-index)
  - emits a BUILD LEDGER pairing each commit (what) with its session (why)
  - emits a FINAL MANIFEST: the shipped file tree + a cheap per-file outline
    (defs/classes/headers) + line counts — the golden anchor a scored verify
    diffs against.

Feed the ledger to /spec-distill ALONGSIDE the session digest. The distiller then
writes phases anchored to commits (each with a real done-state) and embeds the
manifest into the spec's verify section.

Usage:
  git-anchor.py --repo ~/spec2prod
  git-anchor.py --repo ~/myapp --since 2026-06-01 --grep myapp
  git-anchor.py --repo ~/myapp --sessions id1,id2       # explicit session window
"""
import argparse, json, os, subprocess, sys, glob
from datetime import datetime

HOME = os.path.expanduser("~")
CATALOG = os.path.join(HOME, ".claude", "session-index.jsonl")

# per-language "outline" patterns: lines that declare a unit of code.
import re
OUTLINE = [
    re.compile(r"^\s*(?:async\s+)?def\s+\w+"),                 # python
    re.compile(r"^\s*class\s+\w+"),                            # python/js/ts
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+\w+"),  # js/ts
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*="),  # js/ts
    re.compile(r"^\s*(?:export\s+)?(?:interface|type|enum)\s+\w+"),# ts
    re.compile(r"^\s*\w+\s*\(\)\s*\{"),                        # shell functions
    re.compile(r"^#{1,3}\s+\S"),                               # markdown headers
]
SKIP_EXT = {".lock", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".pyc",
            ".woff", ".woff2", ".ttf", ".ico", ".map"}
SKIP_NAME = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    except Exception:
        return None


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, errors="replace").stdout


def load_sessions(repo, grep, since, sessions):
    """Candidate sessions that could have produced commits in this repo."""
    if not os.path.exists(CATALOG):
        print(f"WARN: no session catalog at {CATALOG}. Run /session-index first "
              f"(commit attribution will be empty).", file=sys.stderr)
        return []
    rows = [json.loads(l) for l in open(CATALOG) if l.strip()]
    allow = set(x.strip() for x in sessions.split(",")) if sessions else None
    g = grep.lower() if grep else None
    repo_abs = os.path.realpath(os.path.expanduser(repo))
    out = []
    for r in rows:
        if allow is not None:
            if r["id"] not in allow:
                continue
        else:
            if since and (r.get("date") or "") < since:
                continue
            hay = f"{r.get('title','')} {r.get('first_prompt','')} {r.get('cwd','')}".lower()
            if g and g not in hay:
                continue
        r["_start"] = parse_iso(r.get("start"))
        r["_end"] = parse_iso(r.get("end"))
        if r["_start"]:
            out.append(r)
    out.sort(key=lambda r: r["_start"])
    return out


def attribute(commit_dt, sessions):
    """Session active AT the commit, else the most recent one that ended before it."""
    if not commit_dt:
        return None
    containing = [s for s in sessions if s["_start"] and s["_end"]
                  and s["_start"] <= commit_dt <= s["_end"]]
    if containing:
        return max(containing, key=lambda s: s["_start"])
    prior = [s for s in sessions if s["_end"] and s["_end"] <= commit_dt]
    return max(prior, key=lambda s: s["_end"]) if prior else None


def read_commits(repo, since):
    args = ["log", "--no-merges", "--date=iso-strict",
            "--pretty=format:@@C@@%H%x1f%aI%x1f%s", "--numstat"]
    if since:
        args.append(f"--since={since}")
    raw = git(repo, *args)
    commits, cur = [], None
    for line in raw.splitlines():
        if line.startswith("@@C@@"):
            if cur:
                commits.append(cur)
            h, dt, subj = line[len("@@C@@"):].split("\x1f", 2)
            cur = {"hash": h, "dt": parse_iso(dt), "subj": subj, "files": []}
        elif line.strip() and cur is not None and "\t" in line:
            add, rem, path = (line.split("\t", 2) + ["", "", ""])[:3]
            cur["files"].append((add, rem, path))
    if cur:
        commits.append(cur)
    return commits


def outline(repo, path):
    fp = os.path.join(repo, path)
    _, ext = os.path.splitext(path)
    if ext in SKIP_EXT or os.path.basename(path) in SKIP_NAME:
        return None, 0
    try:
        with open(fp, "r", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return None, 0
    picks = []
    for ln in lines:
        s = ln.rstrip("\n")
        if any(p.match(s) for p in OUTLINE):
            picks.append(s.strip()[:80])
        if len(picks) >= 12:
            break
    return picks, len(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--since")
    ap.add_argument("--grep")
    ap.add_argument("--sessions")
    args = ap.parse_args()

    repo = os.path.expanduser(args.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        print(f"ERROR: not a git repo: {repo}", file=sys.stderr)
        sys.exit(1)

    sessions = load_sessions(repo, args.grep, args.since, args.sessions)
    commits = read_commits(repo, args.since)
    tracked = [p for p in git(repo, "ls-files").splitlines() if p.strip()]

    print(f"# GIT BUILD LEDGER — {os.path.basename(repo.rstrip('/'))}")
    print(f"_repo: {repo} · {len(commits)} commits · {len(tracked)} tracked files · "
          f"{len(sessions)} candidate sessions_\n")
    print("Each commit is a verified phase boundary (WHAT shipped). The attributed "
          "session is the WHY. Distill phases from commits; take reasons from the "
          "session digest.\n")

    print("## Build ledger (oldest → newest)")
    for c in reversed(commits):
        s = attribute(c["dt"], sessions)
        when = c["dt"].isoformat() if c["dt"] else "?"
        print(f"\n### {c['hash'][:8]} · {when[:16]} · {c['subj']}")
        if s:
            print(f"- session: `{s['id'][:8]}` \"{s.get('title','')}\"")
            fp = (s.get("first_prompt") or "").strip().replace("\n", " ")
            if fp:
                print(f"- intent: {fp[:160]}")
        else:
            print("- session: (unattributed — outside catalog window)")
        touched = [p for _, _, p in c["files"] if p]
        if touched:
            shown = ", ".join(touched[:20])
            more = f" … (+{len(touched) - 20} more)" if len(touched) > 20 else ""
            print(f"- files ({len(touched)}): {shown}{more}")

    print("\n## Final manifest (golden anchor for verify)")
    total_lines = 0
    for p in sorted(tracked):
        picks, n = outline(repo, p)
        total_lines += n
        if picks is None:
            print(f"- `{p}` (binary/lock — presence only)")
            continue
        head = f"- `{p}` ({n} lines)"
        if picks:
            print(head + " — outline: " + "; ".join(picks[:8]))
        else:
            print(head)
    print(f"\n_manifest: {len(tracked)} files · ~{total_lines} lines total_")
    print("\nVerify contract: a cold rebuild must reproduce this file tree and, per "
          "file, units with matching names/roles. Score = fraction of manifest files "
          "reproduced with a matching outline; report per-file misses.")


if __name__ == "__main__":
    main()
