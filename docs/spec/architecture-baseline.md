# Architecture Baseline

Last updated: 2026-04-06

## System Shape

AI Knowledge Passport is organized as a local-first pipeline:

1. Raw sources are imported into workspace-specific filesystem locations.
2. Storage records source metadata, derived objects, and audit state in SQLite.
3. Compilation converts raw sources into structured knowledge and evidence-backed outputs.
4. Passport and gateway layers expose only controlled, permissioned read models.
5. Review flows accept AI writeback only as candidates, never direct canonical mutations.

## Module Boundaries

| Module | Responsibility | Allowed dependencies |
| --- | --- | --- |
| `app/domain` | Canonical vocabulary, enums, invariants, serialization contracts | Standard library only |
| `app/storage` | SQLite schema, migrations, repository interfaces, seed loading | `app/domain` |
| `app/ingest` | Source import, raw file preservation, privacy defaults, metadata capture | `app/domain`, `app/storage` |
| `app/ingest.inbox` | Inbox projection, compile-job state, source/evidence preview, and retry actions | `app/ingest`, `app/storage`, `app/domain` |
| `app/compile` | Knowledge-node derivation, evidence extraction, compile jobs, revisions | `app/domain`, `app/storage`, `app/ingest` |
| `app/passport` | Postcards, Passport manifests, readiness signals | `app/domain`, `app/storage`, `app/compile` |
| `app/gateway` | Passport-first reads, visa bundles, mount sessions, access enforcement | `app/domain`, `app/storage`, `app/passport` |
| `app/review` | Review candidates, diffs, audit log events, export/restore controls | `app/domain`, `app/storage`, `app/gateway`, `app/passport` |
| `app/api` | Local service endpoints and request/response mapping | All lower layers, but never peer-to-peer shortcuts |
| `app/mcp` | Minimal MCP resources, tools, and prompts backed by `app/api`/gateway services | `app/api`, `app/gateway`, `app/passport` |

## Dependency Rules

- `app/domain` is the only layer allowed to define product vocabulary.
- Higher layers may depend downward only. Sideways imports across peer modules are not allowed.
- Filesystem raw content is immutable after import; regenerated outputs live in structured storage.
- Review state and audit state are append-oriented and must remain traceable to sessions and evidence.
- External AI entrypoints must read Passport or Postcards first before any deeper access path exists.

## Bootstrap Decisions

- Use Python packages for module boundaries now, even before implementation logic exists.
- Keep migration and seed conventions under `app/storage/` so Milestone 1.3 lands without reshaping the repo.
- Persist array-like fields as JSON text at the SQLite layer while the domain stays tuple-based in Python.
- Keep compile job queueing and inbox projection in `app/ingest` until the real compiler pipeline exists in `app/compile`.
- Treat `scripts/dev.py` as the repo-contract entrypoint for lint, typecheck, test, migrate, and CI orchestration.
- Delay UI, MCP behavior, and provider-specific integrations until the lower layers exist.
