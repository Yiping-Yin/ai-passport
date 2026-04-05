# Development Policy

Last updated: 2026-04-06

## Branch Policy

- Feature branches use `codex/<ticket-or-milestone-slug>`.
- Keep one ticket or tightly scoped milestone slice per branch.
- Merge to `main` only through pull requests.
- Reference the GitHub ticket number in the PR body and validation section.

## Migration Policy

- Store migration files in `app/storage/migrations/`.
- Migration filename format: `YYYYMMDDHHMM__short_description.sql`.
- Prefer one schema migration per ticket unless a later migration must repair the previous one.
- Every migration must be reversible or document why a reverse operation is intentionally unsupported.
- The bootstrap migration command is `python3 scripts/dev.py migrate`; it verifies the migration directory and reports discovered files.

## Seed Data Policy

- Store seed assets in `app/storage/seeds/`.
- Seed data must be deterministic, small enough for local development, and safe to commit.
- One seed workspace is required for Milestone 1.3, but it must not contain private real-user data.
- Seed data filenames should explain scope, for example `workspace_sample.json`.
- The local seed command is `python3 scripts/dev.py seed`.

## Documentation Policy

- Update `Documentation.md` whenever runnable commands change.
- Update architecture or policy docs when a new module boundary or storage convention is introduced.
- Keep `PLANS.md` to one active milestone only.
