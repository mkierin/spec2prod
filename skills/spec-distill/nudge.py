#!/usr/bin/env python3
"""spec2prod distill nudge (Stop hook). ADVISORY, non-blocking, self-silencing.

Second half of the adoption fix. Arming capture automatically is useless if
distillation still has to be *remembered* days later, once the context that made
it valuable is gone. So the tool watches its own marker and speaks up when enough
has actually accumulated:

  armed build + >= THRESHOLD sessions since started_at + no SPEC.md yet
      -> one line, once per COOLDOWN, suggesting /spec-distill.

Never blocks, never repeats itself into noise, fails open on anything unexpected.
"""
import sys
import os
import json
import time
from datetime import datetime, timezone

THRESHOLD_SESSIONS = 3          # enough of a build to be worth distilling
COOLDOWN_SECONDS = 3 * 86400    # don't nag more than every 3 days per project


def parse_iso(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def sessions_since(slug: str, since: datetime) -> int:
    """Count Claude session logs for this project that postdate the capture marker."""
    d = os.path.expanduser(f"~/.claude/projects/{slug}")
    if not os.path.isdir(d):
        return 0
    n = 0
    cutoff = since.timestamp()
    try:
        for name in os.listdir(d):
            if not name.endswith(".jsonl"):
                continue
            p = os.path.join(d, name)
            try:
                if os.path.getmtime(p) >= cutoff:
                    n += 1
            except OSError:
                continue
    except OSError:
        return 0
    return n


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    marker = os.path.join(cwd, ".spec", "tags.json")
    if not os.path.exists(marker):
        return 0

    try:
        with open(marker) as f:
            tags = json.load(f)
    except Exception:
        return 0

    # Already distilled -> nothing to suggest.
    if os.path.exists(os.path.join(cwd, "SPEC.md")):
        return 0

    started = parse_iso(tags.get("started_at", ""))
    if not started:
        return 0

    # Self-silencing: one nudge per project per cooldown.
    last = tags.get("last_nudged_at")
    if last:
        last_dt = parse_iso(last)
        if last_dt and (time.time() - last_dt.timestamp()) < COOLDOWN_SECONDS:
            return 0

    n = sessions_since(tags.get("cwd_slug", ""), started)
    if n < THRESHOLD_SESSIONS:
        return 0

    try:
        tags["last_nudged_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(marker, "w") as f:
            json.dump(tags, f, indent=2)
            f.write("\n")
    except Exception:
        pass  # nudging once more later is harmless; failing to nudge is not

    app = tags.get("app", os.path.basename(cwd))
    print(
        f"[spec2prod] '{app}' has {n} build sessions captured and no SPEC.md yet. "
        f"Run /spec-distill to turn them into a runnable spec while the context is "
        f"still fresh.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
