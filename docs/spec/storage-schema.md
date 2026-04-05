# Storage Schema Overview

Last updated: 2026-04-06

## Migration Baseline

- Migration runner: `app/storage/migrate.py`
- Default database path: `data/dev/ai_passport.sqlite3`
- Initial migration: `app/storage/migrations/202604061600__initial_schema.sql`
- Rollback pair: `app/storage/migrations/202604061600__initial_schema.down.sql`

## Tables

| Table | Purpose | Key relations |
| --- | --- | --- |
| `workspaces` | Workspace root records | Referenced by `sources`, `knowledge_nodes`, `capability_signals`, `mistake_patterns`, `focus_cards`, `postcards`, `passports`, `visa_bundles` |
| `sources` | Raw imported artifacts | `workspace_id -> workspaces.id` |
| `knowledge_nodes` | Structured topic/project/method/question nodes | `workspace_id -> workspaces.id` |
| `evidence_fragments` | Traceable source excerpts | `source_id -> sources.id` |
| `capability_signals` | Evidence-backed observations | `workspace_id -> workspaces.id` |
| `mistake_patterns` | Recurring error patterns | `workspace_id -> workspaces.id` |
| `focus_cards` | Active user goals | `workspace_id -> workspaces.id` |
| `postcards` | Versioned topic summaries | `workspace_id -> workspaces.id` |
| `passports` | High-level knowledge manifests | `workspace_id -> workspaces.id` |
| `visa_bundles` | Scoped read permissions | `workspace_id -> workspaces.id` |
| `mount_sessions` | External AI session trail | `visa_id -> visa_bundles.id` |
| `review_candidates` | AI writeback candidates | `session_id -> mount_sessions.id` |
| `audit_logs` | Append-only governance trail | Polymorphic `object_id` reference |
| `schema_migrations` | Applied migration history | Managed by the migration runner |

## Serialization Strategy

- Scalar enums and timestamps are stored as plain text.
- Array-like fields and nested objects are stored as JSON text columns.
- Foreign keys are used where the relation is concrete and non-polymorphic.
- `review_candidates.target_object` and `audit_logs.object_id` remain polymorphic references and are kept as text identifiers.

## Seed Baseline

- Sample seed file: `app/storage/seeds/sample_workspace.json`
- Seed runner: `app/storage/seed.py`
- The sample data creates one workspace, one source, one node, one evidence fragment, one signal, one mistake pattern, one focus card, one postcard, one passport, one visa bundle, one mount session, one review candidate, and one audit log.
