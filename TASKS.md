# spec2prod — Tasks

## Adoption failure (root finding, 2026-07-10) — FIXED 2026-07-11

**Finding:** the creator had not used spec2prod once since building it. Self-diagnosis: *"I never used the spec2prod things after we created it, and that means bad implementation."*

**Root cause:** capture was OPT-IN and required remembering. `/spec-capture` had to be invoked at the moment you start building — precisely the moment you are thinking about the build, not about tooling. Tooling loses that competition every time, and an un-armed build cannot be distilled afterwards. Distillation had the same defect: `/spec-distill` only ran if you remembered it existed, days later, once the context that made it valuable was already gone.

**Design principle:** capture must be AMBIENT (on by default, zero decision), and distillation must be OFFERED (the tool notices enough has accumulated and proposes it), never remembered.

## Done

- [x] 2026-07-11: Auto-arm capture — `skills/spec-capture/auto-arm.py`, a PostToolUse(Edit|Write) hook. Writes `.spec/tags.json` on the first code-file edit inside a git repo; skips docs-only edits, non-repos, `~/.claude`, `/tmp`, scratch dirs, `node_modules`, bare `$HOME`; silent once armed; fails open on any error. Wired into `~/.claude/settings.json` (backup at `settings.json.bak-spec2prod`). Verified against real repos: arms ✓, idempotent ✓, all four skip guards ✓, fail-open ✓.
- [x] 2026-07-11: Distill nudge — `skills/spec-distill/nudge.py`, a Stop hook. Fires when an armed project has ≥3 captured sessions and no `SPEC.md`; one nudge per project per 3 days; stops permanently once the spec exists. Verified: silent below threshold ✓, fires at threshold ✓, cooldown holds ✓, stops after SPEC.md ✓.
- [x] 2026-07-11: README documents the adoption failure, the design rule, and the hook wiring.

## /spec — the forward half (SPEC written 2026-07-11, not yet implemented)

Design locked at `skills/spec/SPEC.md`. Completes spec2prod: **/spec = specify BEFORE you build (forward)** · **/spec-capture + /spec-distill = recover the spec FROM what you built (backward)**.

Five differentiators, each aimed at a hole the field has not filled (researched 2026-07-11):
1. **It notices** — hook-triggered on a young repo, not a command you must remember (every competitor is opt-in; an opt-in tool is an off tool — proven by this repo's own adoption failure).
2. **It right-sizes** — T0 (no spec) → T3 (full tree). Over-planning small tasks is the field's most-mocked failure and NO tool triages for you.
3. **It grills** — model interviews the user; the one mechanism with research behind it (*Active Task Disambiguation with LLMs*, ICLR 2025 spotlight). Lever is question QUALITY: reason over candidate implementations, ask only what disambiguates.
4. **It writes back** — `DISCOVERED:` notes + an automatic drift gate. **Spec staleness is the field's #1 trust-killer and nobody ships a fix. This is the unclaimed idea.**
5. **It feeds the swarm** — emits a task graph with `[P]` parallel markers + gates. Spec Kit emits parallel markers with nothing to run them; we already have the orchestrator.

Anti-bloat is mechanical, not aspirational: 200-line hard cap per spec file, archetype-selected branches (a CLI tool never gets a "UI and feel" spec), EARS-form acceptance criteria that feed the real gates.

- [ ] 2026-07-11 Implement `/spec` per `skills/spec/SPEC.md` (trigger hook → triage → interview → adaptive tree → orchestration handoff)
- [ ] 2026-07-11 Implement the drift gate + `DISCOVERED:` write-back (§7) — advisory first, promote to automatic once false-positive rate is known
- [ ] 2026-07-11 Tune the young-repo thresholds (12 files / 5 commits are guesses) against real repos before trusting them

## Open

- [ ] 2026-07-11 **Dogfood gate (the real acceptance test)** — spec2prod is not "done" until the auto-armed capture has produced a distilled SPEC.md on a real build the creator did *without thinking about spec2prod at all*. The hooks are live, so this now happens passively: next real build arms itself, and the nudge fires at 3 sessions. Confirm it actually happened before claiming the tool works.
      Blocks: YT **D11** ("the spec-driven framework you can copy-paste into any project") — its truth gate requires a framework the creator demonstrably uses.

## Downstream

- **YT D11** (`personal/youtube-channel/strategy/TOPIC-LIST.md`) — sequel to published video 02, rides the best keyword door on the board (`spec driven development`, 5.4k/mo, LOW comp). Its shared pain is *"you can't get the AI to build autonomously"*; the framework is the fix.
  **The adoption failure above is an INTERNAL engineering lesson only — it never goes on camera.** It is a self-own, and the channel's pain-selection rule (CANON v3) requires pains the viewer already shares, never the creator's personal failings. The dogfood gate still blocks D11's truth gate; the story behind it does not get told.
