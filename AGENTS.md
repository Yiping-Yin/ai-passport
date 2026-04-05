# AGENTS.md

## Product Thesis

AI Knowledge Passport is a local-first knowledge compiler plus a controlled AI access interface.
The system compiles scattered materials into structured knowledge, Postcards, and a Passport that
external AI can read before requesting deeper access.

## Non-Goals

- Do not build a heavy graph explorer before the core compiler exists.
- Do not expose whole-workspace search by default.
- Do not introduce capability scores.
- Do not auto-merge AI writeback into canonical knowledge.
- Do not add complex enterprise permission matrices for the MVP.
- Do not turn multi-agent autonomy into the core product.

## Working Rules

- Read `PLANS.md` before implementing.
- Work one milestone at a time.
- Preserve evidence traceability and permission boundaries.
- Prefer simple, testable implementations over broad scaffolding.
- Keep raw source files immutable; only derived objects may be regenerated.

## Repository Structure

- `docs/spec/`: canonical product and execution docs
- `docs/reference/`: supporting research and references
- `data/workspaces/`: local-first workspace data roots
- `app/domain/`: entities, invariants, and serialization contracts
- `app/storage/`: SQLite schema, repositories, migrations
- `app/ingest/`: raw source intake and metadata preservation
- `app/compile/`: compilation pipeline and evidence extraction
- `app/passport/`: Postcard and Passport generation
- `app/gateway/`: controlled AI read surface and visa flow
- `app/review/`: review queue, diff, and audit controls
- `app/api/`: local service or HTTP endpoints
- `app/mcp/`: minimal MCP server surface
- `tests/`: fixtures, golden tests, and integration tests

Baseline references:

- `docs/spec/repository-recon.md`: runtime inventory and verified commands
- `docs/spec/architecture-baseline.md`: frozen module boundaries
- `docs/spec/development-policy.md`: branch, migration, and seed conventions

## Branch and PR Policy

- Branch format: `codex/<ticket-or-milestone-slug>`
- `main` is protected by PR-only updates
- CI check names are reserved as `lint`, `typecheck`, and `test`
- Migration and seed conventions are defined in `docs/spec/development-policy.md`

## Done Definition

A milestone is done only when:

1. The scoped functionality exists in the real repo.
2. Tests for the changed behavior pass.
3. Typecheck and lint pass.
4. Documentation is updated.
5. No new permission or traceability regressions are introduced.
6. Passport-first, read-only-first, evidence-backed, and review-controlled writeback remain intact.
