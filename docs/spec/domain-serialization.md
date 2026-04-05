# Domain Serialization Contracts

Last updated: 2026-04-06

## Mapping Rules

- Internal entities are frozen Python dataclasses under `app/domain/models.py`.
- Enums serialize to lowercase string values.
- `datetime` fields serialize to ISO 8601 strings.
- Tuple-backed collections serialize to JSON arrays to keep storage and API shapes aligned.
- `machine_manifest` and `meta` stay as JSON-compatible object maps.

## Versioned Records

The following records are versioned and must serialize with `version >= 1`:

- `KnowledgeNode`
- `Postcard`
- `Passport`
- `VisaBundle`
- `ReviewCandidate`
- `CompileJob.attempt_number`

## Transport Assumptions

- `Workspace`, `Source`, `FocusCard`, `MountSession`, and `AuditLog` keep stable object IDs and explicit timestamps.
- `CompileJob.status` serializes as one of `not_started`, `queued`, `running`, `succeeded`, or `failed`.
- `VisaBundle.permission_levels` is serialized as a list of stable permission strings: `passport_read`, `topic_read`, `writeback_candidate`.
- `AccessMode` is serialized as either `read_only` or `candidate_writeback`.
- `WritebackPolicy` is serialized as `review_required`; there is intentionally no auto-merge value.
- Reviewability metadata uses `FieldProvenance` values `generated`, `human_edited`, and `mixed`, plus override modes `replace` and `merge`.

## Invariant Notes

- Read-only-first is encoded through `VisaBundle.access_mode`, `permission_levels`, and `writeback_policy`.
- Whitelist-only access is encoded through explicit `included_postcards` and `included_nodes`; wildcard values are invalid.
- Mount sessions and review candidates remain separate records so writeback is always traceable to a concrete session.
- Generated nodes remain distinct from manual overrides so the system can show both effective content and generated revision diffs.
