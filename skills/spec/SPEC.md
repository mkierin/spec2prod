# /spec — the forward half of spec2prod

```
status: SPEC v0.1 (2026-07-11) — design locked, not yet implemented
author: Kierin Dougoud
completes: spec2prod. /spec = specify BEFORE you build (forward).
           /spec-capture + /spec-distill = recover the spec FROM what you built (backward).
```

## The gap this fills

Every spec-driven tool on the market (GitHub Spec Kit, Amazon Kiro, BMAD, OpenSpec, Tessl) is a
**manual slash command applying fixed ceremony**. That produces the field's two most-cited failures:

1. **Spec bloat — "the illusion of work."** Long specs feel like progress but *degrade* agent
   compliance. GitHub's own Spec Kit discussion (#1784) has a user specifying an exact JSON shape
   and the agent still getting it wrong, because the detail was buried in a wall of generated text.
   Practitioners report compliance collapsing somewhere past ~150–200 standing instructions.
2. **Spec drift.** Specs are written once and consumed forever. Code moves; the spec doesn't; the
   agent trusts the stale doc and confidently does the wrong thing. Universally cited as the #1
   trust-killer. **Nobody ships a fix.**

And a third, quieter one: **over-planning small things.** Running constitution → specify → clarify →
plan → tasks for a one-line fix is the single most mocked failure mode in the field, and no tool
right-sizes for you. It is all-or-nothing ceremony.

**What research DOES support:** agent-initiated clarifying questions before generation measurably
improve correctness (*Active Task Disambiguation with LLMs*, ICLR 2025 spotlight). Making the model
interview you is the one part of the folklore with evidence behind it — and the lever is question
QUALITY (reason over candidate solutions first, then ask what actually disambiguates), not question
volume.

## The five differentiators

| # | What | Why it is new |
|---|---|---|
| 1 | **It notices.** Hook-triggered on a new project, not a command you must remember. | Every competitor is opt-in. An opt-in tool is an off tool — proven by spec2prod's own adoption failure. |
| 2 | **It right-sizes.** A triage ladder picks the ceremony (T0 none → T3 full tree). | The #1 practitioner complaint. No tool does this. |
| 3 | **It grills.** The model interviews you until no blanks are left for it to guess. | The only research-backed mechanism in the field (ICLR 2025). |
| 4 | **It writes back.** Implementation discoveries update the spec; drift is a gate, not a chore. | The biggest unclaimed idea in the field. Nobody has shipped bidirectional specs. |
| 5 | **It feeds the swarm.** Emits a task graph with parallel markers the orchestrator executes. | My unfair advantage: I already have the orchestrator. Spec Kit emits `[P]` markers with nothing to run them. |

## 1. Trigger — it notices

A `PostToolUse(Edit|Write)` hook, same shape as the shipped `spec-capture/auto-arm.py`.

Fires when ALL hold:
- the edit is a code file inside a git repo (reuse auto-arm's skip guards: no `~/.claude`, `/tmp`,
  scratch dirs, `node_modules`, bare `$HOME`, docs-only edits)
- the repo has **no `.spec/tree/`** yet
- the repo looks **young**: fewer than N tracked code files (default 12) OR fewer than M commits
  (default 5). A mature repo mid-flight must NOT be ambushed with an interview.

Then it does exactly ONE thing: prints a single line offering the spec.

```
[spec] new build detected — 'flowtrack'. Want me to spec it before we go further? (/spec)
```

**It never auto-interviews and never blocks.** A hook that hijacks a session is a hook that gets
removed. Suggest once, respect the answer, record the decline in `.spec/declined` so it stays quiet.

## 2. Triage — it right-sizes (the core innovation)

The FIRST thing `/spec` does is decide how much ceremony this deserves. It asks one question — *"what
are we building?"* — and classifies:

| Tier | Trigger | Ceremony | Emits |
|---|---|---|---|
| **T0 — none** | one-line fix, config, typo, rename | none. **Say so and get out of the way.** | nothing |
| **T1 — inline** | single-file change, one behaviour, < ~200 lines | 5-line intent block, in the commit body | nothing on disk |
| **T2 — light tree** | a tool / script / CLI / internal utility | north star + 2–4 module specs | `.spec/tree/` (small) |
| **T3 — full tree** | an app / product with real users | full adaptive tree (below) | `.spec/tree/` + task graph |

**T0 must exist and must be used.** A spec skill whose answer is always "yes, let's spec it" is the
ceremony problem wearing a new hat. Bias toward the lower tier when uncertain; the user can escalate
with `/spec --deep`.

## 3. The tree — modular, and it ADAPTS to the archetype

Always rooted in **vision + north star** (T2 and T3). Everything else is selected, not fixed.

```
.spec/tree/
  00-north-star.md        ← ALWAYS. vision, who it is for, the one thing it must do,
                            what "done" means, what it will NOT do.
  <archetype branches>
  99-orchestration.md     ← how an agent should build from this tree (see §6)
```

Branches are chosen by archetype — a CLI tool has no "UI and feel"; a data pipeline has no "user
journey" but lives or dies on data contracts:

| Archetype | Branches |
|---|---|
| **CLI / tool** | interface (commands, flags) · behaviour · failure modes · install |
| **Web app / SaaS** | audience · the pain · UI and feel · user journey · frontend · backend · data · auth · ops |
| **API / service** | contracts · data model · failure modes · limits · ops |
| **Data pipeline** | sources · contracts · transforms · idempotency · failure modes · schedule |
| **Agent / automation** | trigger · tools · guardrails · failure modes · human gate |
| **Content site** | audience · IA · content model · design system · SEO |

**Hard cap: any single spec file ≤ 200 lines.** If a branch outgrows it, it splits into children.
This is a direct, mechanical defence against the bloat failure mode — enforced by the skill, not by
the user's good intentions.

## 4. The interview — it grills you

For each selected branch, the model interviews the user until there are no blanks left for it to
guess. Per ICLR 2025, quality beats volume:

- **Reason first, then ask.** Internally sketch 2–3 plausible implementations of the branch, find
  where they DIVERGE, and ask only the questions whose answers change the outcome. Never ask
  questions the code or the north star already answers.
- **Ask about decisions, not preferences.** "What happens when the upload fails halfway?" beats
  "how should errors be handled?"
- **Stop when the remaining unknowns are reversible.** Do not interrogate to exhaustion; a spec is
  not a contract with the universe.
- Offer `/spec --fast` (one pass, best-guess defaults, marked `ASSUMED:`) for people who want to move.

Every guess the model makes is written into the spec as `ASSUMED: <x>` so assumptions are visible and
falsifiable rather than silently baked in.

## 5. Acceptance criteria — testable, not prose (stolen from Kiro's EARS)

Every branch ends with acceptance criteria in the form:

```
WHEN <event/condition> THE SYSTEM SHALL <observable behaviour>
```

Vague adjectives ("fast", "user-friendly", "robust") are rejected by the skill at write time — they
are unverifiable and they are how specs become decoration. These criteria are the input to the
verification gates (reality-check / prodcheck), so the spec and the gate speak the same language.

## 6. Orchestration handoff — it feeds the swarm

`99-orchestration.md` is written FOR the orchestrator, not for a human:

- the build order, with **`[P]` parallel markers** on independent tasks
- per-task: which spec files to read, what "done" means (the EARS criteria), which gate must pass
- worktree strategy: one task per worker, handoff + commit + report on completion
- **task size cap: 50–250 line diffs.** Bigger tasks get split at spec time, not discovered at build
  time.

This is the piece the competition structurally cannot ship: Spec Kit emits parallel markers with
nothing to execute them. The swarm is already built.

## 7. Bidirectional — the spec maintains itself (the unclaimed idea)

Drift is the field's #1 killer and every tool leaves it to human diligence, which is exactly the thing
humans reliably will not do.

- **Write-back.** When a worker's implementation contradicts or extends the spec ("the auth context
  already existed, wired into that instead"), it appends a `DISCOVERED:` note to the relevant branch
  and reports it. The spec learns from the build.
- **Drift gate (automatic, not a command).** On `Stop`, if code changed under a spec'd module and the
  spec's acceptance criteria were not touched, emit ONE advisory line:
  `[spec] backend changed; 00-north-star + 04-backend criteria untouched. /spec sync?`
- **Human reviews spec diffs, not just code diffs.** The spec is version-controlled and the write-back
  arrives as a reviewable diff — which is the whole point.

Same discipline as auto-arm: advisory, self-silencing, cooldowned, fail-open. Never blocks.

## 8. Files

```
.spec/
  tags.json               # existing, from /spec-capture (auto-armed)
  declined                # user said no; stay quiet
  tree/
    00-north-star.md
    NN-<branch>.md        # archetype-selected, each ≤200 lines
    99-orchestration.md   # task graph + [P] markers + gates, for the swarm
```

## 9. Failure modes this skill MUST avoid (from the field's own scar tissue)

| Failure | Defence built in |
|---|---|
| Spec bloat / illusion of work | T0–T1 tiers; 200-line hard cap per file; archetype branch selection (never emit branches that do not apply) |
| Spec drift / staleness | §7 write-back + automatic drift gate. **This is the differentiator, not an afterthought.** |
| Over-planning small tasks | T0 exists and is the default under uncertainty. "This needs no spec" is a valid, common answer. |
| Sequential rigidity | Any tier is skippable; `--fast` exists; the user can always say no and it records the no |
| Rubber-stamp tests | Acceptance criteria are EARS-form and feed the real gates (reality-check), which observe behaviour rather than assert trivially |
| Hook over-eagerness | ONE hook, ONE line, once per project, records declines, fails open |
| Interview fatigue | Reason-then-ask; stop when remaining unknowns are reversible; `ASSUMED:` for anything guessed |

## 10. Acceptance criteria for the skill itself (dogfood)

```
WHEN a code file is first edited in a young git repo with no .spec/tree
  THE SYSTEM SHALL print exactly one advisory line offering /spec, and never block.

WHEN the user declines
  THE SYSTEM SHALL record the decline and not offer again for that project.

WHEN /spec runs and the work is a one-line fix
  THE SYSTEM SHALL classify it T0, say no spec is needed, and write nothing.

WHEN /spec builds a tree for a CLI tool
  THE SYSTEM SHALL NOT emit "UI and feel" or "user journey" branches.

WHEN any spec file would exceed 200 lines
  THE SYSTEM SHALL split it into child files rather than growing it.

WHEN the model must guess an unspecified decision
  THE SYSTEM SHALL write it into the spec prefixed ASSUMED:.

WHEN a worker's implementation contradicts a spec branch
  THE SYSTEM SHALL append a DISCOVERED: note to that branch and surface it as a diff.

WHEN code under a spec'd module changes and its acceptance criteria are untouched
  THE SYSTEM SHALL emit one advisory drift line on Stop, cooldowned per project.
```

## 11. Open questions (decide at build)

- **Young-repo thresholds** (12 files / 5 commits) are guesses. Tune by observing false-fire rate on
  real repos before trusting them.
- **Where does the north star live** when a repo already has a `CLAUDE.md`? Probably: north star is
  the product truth, CLAUDE.md is the working agreement. They should link, not duplicate. Confirm.
- **`/spec sync` vs automatic write-back** — start with advisory (safe), promote to automatic once the
  false-positive rate is known.
- Should the drift gate ever BLOCK (like the reality-check gate does for deploys)? Probably only for
  a spec'd module going to production. Not v1.
