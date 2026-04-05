# Documentation

## Repository Inventory

| Topic | Verified baseline |
| --- | --- |
| Runtime | Python 3.11+ |
| Package manager | Standard library only at bootstrap |
| App layout | `app/{domain,storage,ingest,compile,passport,gateway,review,api,mcp}` |
| Migration command | `python3 scripts/dev.py migrate` |
| Seed command | `python3 scripts/dev.py seed` |
| Lint command | `python3 scripts/dev.py lint` |
| Typecheck command | `python3 scripts/dev.py typecheck` |
| Test command | `python3 scripts/dev.py test` |
| CI command | `python3 scripts/dev.py ci` |
| Local server | `python3 scripts/run_server.py` |
| Pilot script | `python3 scripts/pilot_flow.py` |

## Verified Local Commands

```bash
git status --short --branch
python3 scripts/dev.py migrate
python3 scripts/dev.py seed
python3 scripts/dev.py lint
python3 scripts/dev.py typecheck
python3 scripts/dev.py test
python3 scripts/dev.py ci
python3 scripts/run_server.py
python3 scripts/pilot_flow.py
python3 scripts/seed_github.py --repo Yiping-Yin/ai-passport --validate-only
python3 scripts/seed_github.py --repo Yiping-Yin/ai-passport --seed
```

## Verified GitHub Commands

```bash
gh auth status
gh auth refresh -s read:project
gh repo view Yiping-Yin/ai-passport --json name,visibility,url,defaultBranchRef
gh issue list --repo Yiping-Yin/ai-passport --limit 200
gh api repos/Yiping-Yin/ai-passport/milestones?state=all&per_page=100
```

## Repository Notes

- The repo is initialized on `main`.
- The GitHub bootstrap script is the source of truth for labels, milestones, issues, and import manifest state.
- Project board creation depends on GitHub project permissions and API availability in the authenticated `gh` session.
- Repository reconnaissance details are in `docs/spec/repository-recon.md`.
- Module boundaries are frozen in `docs/spec/architecture-baseline.md`.
- Branch, migration, and seed policies are frozen in `docs/spec/development-policy.md`.
- Storage tables and relations are documented in `docs/spec/storage-schema.md`.
- Release gates and pilot feedback references are in `docs/spec/release-gate-checklist.md` and `docs/spec/pilot-feedback-template.md`.
