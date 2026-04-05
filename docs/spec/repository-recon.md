# Repository Reconnaissance Baseline

Last verified: 2026-04-06

## Runtime and Tooling Inventory

| Topic | Current baseline | Notes |
| --- | --- | --- |
| Language runtime | Python 3.11+ | Local verification ran on Python 3.13. |
| Package manager | Standard library only | No third-party Python dependencies are required yet. If dependencies are introduced later, use `python3 -m pip` until a dedicated package manager is adopted. |
| Database target | SQLite | Schema and migrations land in `app/storage/`. |
| Source of truth | Local filesystem + GitHub metadata | Raw materials remain on disk; structured state later moves into SQLite. |
| Remote workflow | Git + GitHub CLI (`gh`) | Repo, milestones, issues, and Project provisioning are driven by `scripts/seed_github.py`. |

## Repository Layout

| Path | Purpose |
| --- | --- |
| `docs/spec/` | Canonical PRD, backlog, architecture baseline, and operating policies |
| `docs/reference/` | Supporting source material and implementation references |
| `app/domain/` | Core entities, enums, invariants, and serialization contracts |
| `app/storage/` | SQLite schema, migrations, repositories, and seed data contracts |
| `app/ingest/` | Raw-source import and metadata preservation |
| `app/compile/` | Compiler pipeline and evidence extraction |
| `app/passport/` | Postcard and Passport generation |
| `app/gateway/` | External AI read surface, visa flow, and access constraints |
| `app/review/` | Review candidates, diffs, and audit operations |
| `app/api/` | Local API or service entrypoints |
| `app/mcp/` | Minimal MCP server surface |
| `data/workspaces/` | Local-first workspace storage roots |
| `scripts/` | Repo automation, validation, and bootstrap commands |
| `tests/` | Unit and repo-contract verification |
| `state/` | Derived manifests produced by bootstrap tooling |

## Verified Commands

| Purpose | Command | Result |
| --- | --- | --- |
| Repo status | `git status --short --branch` | Confirms branch and working tree state |
| Migration baseline | `python3 scripts/dev.py migrate` | Applies the tracked SQLite migrations to `data/dev/ai_passport.sqlite3` |
| Seed baseline | `python3 scripts/dev.py seed` | Loads the sample workspace into the default development database |
| Lint baseline | `python3 scripts/dev.py lint` | Validates required repo structure and tracked baseline files |
| Typecheck baseline | `python3 scripts/dev.py typecheck` | Compiles tracked Python modules to catch syntax and import-shape regressions |
| Test baseline | `python3 scripts/dev.py test` | Runs repo-contract and parser tests |
| Full CI baseline | `python3 scripts/dev.py ci` | Runs lint, typecheck, and tests in the same sequence as CI |
| Backlog validation | `python3 scripts/seed_github.py --repo Yiping-Yin/ai-passport --validate-only` | Confirms the backlog still parses as 8 epics, 24 milestones, and 83 tickets |

## Current Constraints

- The repo is still in bootstrap mode: no third-party Python dependencies and no runtime API surface beyond repo, storage, and GitHub bootstrap tooling.
- The repo uses SQLite JSON text columns for tuple/list fields in the bootstrap schema.
- Inbox compile jobs are intentionally queue-only scaffolding; the real compiler lands in Epic 3.
- The compiler now supports section-based node generation, node revisions, evidence links, source-jump lookups, and manual field overrides.
- `scripts/seed_github.py` is the heaviest live script and should remain stable while Milestone 1.2 introduces domain modules.
- The GitHub Project seed now requires `gh` auth with `project` scope.
- Module boundaries are frozen in [architecture-baseline.md](/Users/yinyiping/Desktop/AI passport/docs/spec/architecture-baseline.md) and policy is frozen in [development-policy.md](/Users/yinyiping/Desktop/AI passport/docs/spec/development-policy.md).
