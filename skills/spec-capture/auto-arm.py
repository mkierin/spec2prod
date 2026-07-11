#!/usr/bin/env python3
"""spec2prod auto-arm (PostToolUse: Edit|Write). ADVISORY, never blocks.

The adoption problem this solves: /spec-capture was opt-in, so it had to be
remembered at the exact moment you are thinking about the build and not about
tooling. It lost that competition every time, and an un-armed build cannot be
distilled later.

Nothing here records prompts — Claude Code already persists every session to
~/.claude/projects/<cwd-slug>/*.jsonl. Capture was only ever a boundary marker.
So arming it is cheap enough to do without asking: on the first real code edit in
a project, drop .spec/tags.json. Intent stays a placeholder; /spec-distill
refines it from the sessions anyway (that was always the design).

Fail-open on every error: a capture marker is never worth breaking an edit over.
"""
import sys
import os
import json
import subprocess
from datetime import datetime, timezone

# Directories where a build marker is meaningless or unwanted.
SKIP_PREFIXES = [
    os.path.expanduser("~/.claude"),
    "/tmp",
    "/var",
    "/etc",
    "/usr",
]
SKIP_PARTS = {"node_modules", ".git", "scratchpad", "__pycache__", "site-packages"}

# Code-ish files only. Editing a README or a task list is not "starting a build".
CODE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb", ".java", ".kt",
    ".c", ".h", ".cpp", ".cs", ".php", ".swift", ".sh", ".sql", ".vue", ".svelte",
    ".html", ".css", ".scss", ".qvs", ".ipynb",
}


def project_root(start: str):
    """Nearest git repo root at or above `start`, else None (no repo, no build)."""
    try:
        out = subprocess.run(
            ["git", "-C", start, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except Exception:
        pass
    return None


def should_skip(path: str) -> bool:
    real = os.path.realpath(path)
    if any(real.startswith(p) for p in SKIP_PREFIXES):
        return True
    if SKIP_PARTS & set(real.split(os.sep)):
        return True
    # The home dir itself is a shared junk drawer, never one coherent build.
    if real.rstrip(os.sep) == os.path.expanduser("~").rstrip(os.sep):
        return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return 0

    if os.path.splitext(file_path)[1].lower() not in CODE_SUFFIXES:
        return 0
    if should_skip(file_path):
        return 0

    root = project_root(os.path.dirname(os.path.realpath(file_path)) or ".")
    if not root or should_skip(root):
        return 0

    marker = os.path.join(root, ".spec", "tags.json")
    if os.path.exists(marker):
        return 0  # already armed — this is the steady state, stay silent

    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        tags = {
            "app": os.path.basename(root),
            "intent": "(auto-armed — /spec-distill infers real intent from the sessions)",
            "cwd": root,
            "cwd_slug": root.replace("/", "-").replace(".", "-"),
            "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sessions": [],
            "armed_by": "auto-arm hook (PostToolUse Edit|Write)",
        }
        with open(marker, "w") as f:
            json.dump(tags, f, indent=2)
            f.write("\n")
    except Exception:
        return 0

    print(
        f"[spec2prod] capture armed for '{tags['app']}' — sessions from now on are "
        f"part of this build's record. Run /spec-distill at any checkpoint to turn "
        f"them into a runnable SPEC.md.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
