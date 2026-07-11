# spec2prod — Tasks

## Adoption failure (root finding, 2026-07-10) — FIXED 2026-07-11

**Finding:** the creator had not used spec2prod once since building it. Self-diagnosis: *"I never used the spec2prod things after we created it, and that means bad implementation."*

**Root cause:** capture was OPT-IN and required remembering. `/spec-capture` had to be invoked at the moment you start building — precisely the moment you are thinking about the build, not about tooling. Tooling loses that competition every time, and an un-armed build cannot be distilled afterwards. Distillation had the same defect: `/spec-distill` only ran if you remembered it existed, days later, once the context that made it valuable was already gone.

**Design principle:** capture must be AMBIENT (on by default, zero decision), and distillation must be OFFERED (the tool notices enough has accumulated and proposes it), never remembered.

## Done

- [x] 2026-07-11: Auto-arm capture — `skills/spec-capture/auto-arm.py`, a PostToolUse(Edit|Write) hook. Writes `.spec/tags.json` on the first code-file edit inside a git repo; skips docs-only edits, non-repos, `~/.claude`, `/tmp`, scratch dirs, `node_modules`, bare `$HOME`; silent once armed; fails open on any error. Wired into `~/.claude/settings.json` (backup at `settings.json.bak-spec2prod`). Verified against real repos: arms ✓, idempotent ✓, all four skip guards ✓, fail-open ✓.
- [x] 2026-07-11: Distill nudge — `skills/spec-distill/nudge.py`, a Stop hook. Fires when an armed project has ≥3 captured sessions and no `SPEC.md`; one nudge per project per 3 days; stops permanently once the spec exists. Verified: silent below threshold ✓, fires at threshold ✓, cooldown holds ✓, stops after SPEC.md ✓.
- [x] 2026-07-11: README documents the adoption failure, the design rule, and the hook wiring.

## Open

- [ ] 2026-07-11 **Dogfood gate (the real acceptance test)** — spec2prod is not "done" until the auto-armed capture has produced a distilled SPEC.md on a real build the creator did *without thinking about spec2prod at all*. The hooks are live, so this now happens passively: next real build arms itself, and the nudge fires at 3 sessions. Confirm it actually happened before claiming the tool works.
      Blocks: YT **D11** ("the spec-driven framework you can copy-paste into any project") — its truth gate requires a framework the creator demonstrably uses.

## Downstream

- **YT D11** (`personal/youtube-channel/strategy/TOPIC-LIST.md`) — sequel to published video 02, rides the best keyword door on the board (`spec driven development`, 5.4k/mo, LOW comp). The abandonment story is now an *asset* for that video: "I built this, then never used it — here's why that's the most important thing I learned about tools."
