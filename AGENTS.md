# AGENTS.md

This file tells every agent working in this repository (AI assistants and human collaborators) how to
behave at all times. It is not a product description: what the application does lives in `README.md`, the
per-domain references in `docs/`, and the implementation in the code.

## Start of work

- Work starts from a GitHub issue. Read it before writing anything; if there is no issue, ask for one.
- Read `README.md` for the product and `docs/` for the domain you are about to touch.
- Write or update tests before the implementation.

## Change discipline

- One iteration = one commit; keep each change small, independently buildable and testable.
- Keep the core decoupled (API extraction, prompt building, output parsing) so the interface can evolve
  from the CLI to a web UI.
- Do not introduce a new dependency, provider, or state store without explicit agreement.

## Data & truth

- `Intervals.icu` is the single source of truth for athlete data and calendar state. Never create a second
  source; never persist what can be re-derived.
- Never recompute what the hub owns (CTL/ATL/PMC); read it.

## Safety

- Never write to `Intervals.icu` autonomously: every calendar change is a draft that requires a literal
  `yes` from the operator before it is applied.
- Never cross write families: workout mutations only touch `WORKOUT`, race mutations only touch `RACE_*`.
- Keep writes idempotent by (name, date); read back and compare after every write; skip when unchanged.
- Never log, print, or commit secrets. Never put personal data (athlete profile, health data) in code,
  docs, fixtures, issues, or commit messages.

## Budget & context

- Never build a request that exceeds the model's input budget; any new context section needs an eviction
  rule.
- Keep always-loaded files short (this file, `README.md`); put detail in `docs/` or the code.

## Git & review

- Never commit, stage, amend, rebase, force-push, or open a PR unless explicitly asked.
- A review freezes the SHA it reviewed: after a review, new changes go to a new commit/branch; never
  rewrite the reviewed branch.
- Never commit secrets; inspect `git status` and the diff before any commit.

## Definition of done

A feature is complete only when:

1. it extracts its data scope from `Intervals.icu` without exhausting the model budget;
2. the LLM output parses into the strict validated schema before any write is attempted;
3. user context, when provided, is verifiably injected before the calendar is updated;
4. all new data flows and API usage are documented.
