# AI Knowledge Passport

Bootstrap repository for the AI Knowledge Passport MVP.

This repo follows the implementation guide's local-first defaults:

- Python 3.11+
- SQLite
- Local filesystem for raw sources and exports
- Minimal MCP surface
- Milestone-by-milestone delivery

## Canonical Planning Inputs

- `docs/spec/product-prd.md`: canonical English PRD and backlog reference
- `docs/spec/execution-backlog.md`: canonical execution backlog for GitHub seeding
- `docs/reference/user-story-prd.md`: overlapping user-story-only reference
- `docs/reference/implementation-guide-cn.pdf`: Chinese implementation guide

## Repository Bootstrap

- `AGENTS.md`: repo contract, boundaries, and done definition
- `PLANS.md`: current active milestone only
- `Documentation.md`: verified local and GitHub bootstrap commands
- `docs/spec/repository-recon.md`: runtime, commands, and repo inventory
- `docs/spec/architecture-baseline.md`: frozen module boundaries
- `docs/spec/development-policy.md`: branch, migration, and seed conventions
- `docs/spec/storage-schema.md`: initial SQLite table layout and key relations
- `docs/spec/domain-serialization.md`: transport mapping for domain objects
- `scripts/seed_github.py`: parse backlog, validate counts, and seed GitHub
- `scripts/dev.py`: local lint, typecheck, test, migrate, and CI commands

## Local Commands

```bash
python3 scripts/dev.py migrate
python3 scripts/dev.py seed
python3 scripts/dev.py ci
python3 scripts/seed_github.py --repo Yiping-Yin/ai-passport --validate-only
python3 scripts/seed_github.py --repo Yiping-Yin/ai-passport --seed
python3 scripts/seed_github.py --repo Yiping-Yin/ai-passport --seed --project-owner Yiping-Yin
```

The script writes:

- `state/backlog-manifest.json`: parsed backlog structure
- `state/github-import-manifest.json`: created GitHub artifact IDs and URLs

If you want the script to provision a GitHub Project as well, refresh the CLI token first:

```bash
gh auth refresh -s read:project
```
