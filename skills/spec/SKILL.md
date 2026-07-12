---
name: spec
description: Spec a build BEFORE it starts — the forward half of spec2prod. Triages how much ceremony the work deserves (a one-line fix gets none; an app gets a full tree), then interviews you until nothing important is left for the model to guess, and writes a modular .spec/tree/ an agent can build from. Use when starting a new project, when the user says "spec this" / "let's spec it first" / "/spec", or before handing a build to agents. Flags: --fast (one pass, best-guess defaults marked ASSUMED), --deep (escalate one tier).
---

# /spec — specify before you build

Forward half of spec2prod: `/spec` before the build, `/spec-capture` + `/spec-distill`
to recover a spec from a finished build. Full design: `SPEC.md` in this folder.

Two rules override everything else:

1. **Right-size the ceremony.** "This needs no spec" is a valid and common answer.
2. **Never guess silently.** Anything you assume goes into the spec as `ASSUMED: <x>`.

## Step 1 — Triage (always first)

Ask one question if the answer isn't already in context: **"What are we building?"**
Then classify — and bias toward the LOWER tier when uncertain (the user can escalate
with `/spec --deep`):

| Tier | Looks like | Ceremony |
|---|---|---|
| **T0** | one-line fix, config change, typo, rename | none — say so and get out of the way |
| **T1** | single-file change, one behaviour, < ~200 lines | 5-line intent block in chat (goal, non-goal, edge case, done-when, assumption) — nothing on disk |
| **T2** | a tool / script / CLI / internal utility | north star + 2–4 branch specs → `.spec/tree/` |
| **T3** | an app / product with real users | full adaptive tree + orchestration file → `.spec/tree/` |

State the tier and why in one line ("T2 — internal CLI, no users but real behaviour
surface"). If T0: stop here. If `.spec/tree/` already exists, you are updating, not
starting over — read it first.

## Step 2 — Pick branches by archetype (T2/T3 only)

The tree is always rooted in `00-north-star.md`. Every other file is SELECTED, not
fixed — never emit a branch that doesn't apply to the archetype:

| Archetype | Branches |
|---|---|
| CLI / tool | interface (commands, flags) · behaviour · failure modes · install |
| Web app / SaaS | audience · the pain · UI and feel · user journey · frontend · backend · data · auth · ops |
| API / service | contracts · data model · failure modes · limits · ops |
| Data pipeline | sources · contracts · transforms · idempotency · failure modes · schedule |
| Agent / automation | trigger · tools · guardrails · failure modes · human gate |
| Content site | audience · IA · content model · design system · SEO |

T2 keeps it to the 2–4 branches that matter. A CLI tool has no "UI and feel"; a data
pipeline has no "user journey".

## Step 3 — The interview

For the north star, then each branch, interview the user until nothing important is
left for you to guess. Quality over volume (the research-backed lever):

- **Reason first, then ask.** Privately sketch 2–3 plausible implementations of the
  branch, find where they DIVERGE, and ask only the questions whose answers change
  the outcome. Never ask what the code, the repo, or the north star already answers.
- **Ask about decisions, not preferences.** "What happens when the upload fails
  halfway?" beats "how should errors be handled?"
- **Batch 2–4 questions at a time**, not one-by-one and not a wall of twenty.
- **Stop when the remaining unknowns are reversible.** A spec is not a contract with
  the universe.
- On `--fast`: one question pass, then best-guess everything else, each guess written
  as `ASSUMED: <x>`.

Every assumption you make — in any mode — is written into the spec prefixed
`ASSUMED:` so it is visible and falsifiable, never silently baked in.

## Step 4 — Write the tree

```
.spec/tree/
  00-north-star.md        # ALWAYS: vision, who it's for, the one thing it must do,
                          # what "done" means, what it will NOT do
  NN-<branch>.md          # archetype-selected branches, NN = build-order-ish
  99-orchestration.md     # T3 (and T2 when agents will build it) — see Step 5
```

Rules enforced at write time:

- **Hard cap: ≤ 200 lines per file.** If a branch outgrows it, split into children
  (`04-backend.md` → `04a-backend-api.md`, `04b-backend-jobs.md`). Never grow past
  the cap.
- **Every branch ends with acceptance criteria in EARS form:**
  `WHEN <event/condition> THE SYSTEM SHALL <observable behaviour>`
  Reject vague adjectives ("fast", "user-friendly", "robust") — if you can't observe
  it, it isn't a criterion. Rewrite it as something observable or drop it.
- North star vs `CLAUDE.md`: the north star is the product truth, `CLAUDE.md` is the
  working agreement. Link, don't duplicate.

## Step 5 — Orchestration handoff (99-orchestration.md)

Written FOR an agent orchestrator, not for a human:

- Build order as a task list; mark independent tasks `[P]` (parallel-safe).
- Per task: which spec files to read, what "done" means (point at the branch's EARS
  criteria), which gate must pass (e.g. reality-check / project verify).
- **Task size cap: 50–250 line diffs.** Split bigger tasks now, at spec time, not at
  build time.
- Worktree strategy for parallel tasks: one task per worker, commit + report on
  completion.

## Step 6 — Hand off

Close with a 3-line summary: tier, files written, and the single next command
(e.g. "hand `.spec/tree/` to a fresh agent" or "launch the swarm on
`99-orchestration.md`"). If the build is starting now, suggest `/spec-capture` so the
sessions that build it are tagged for later distillation.

## v0 limits (by design — see SPEC.md §1, §7)

Not in v0: the new-project notice hook ("it notices") and the drift write-back /
`DISCOVERED:` gate ("it writes back"). Until those ship, run `/spec` manually at
project start and re-run it after big pivots.
