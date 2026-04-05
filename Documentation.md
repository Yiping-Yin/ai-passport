# Documentation

## Verified Local Commands

```bash
git status --short --branch
python3 scripts/seed_github.py --repo Yiping-Yin/ai-passport --validate-only
python3 scripts/seed_github.py --repo Yiping-Yin/ai-passport --seed
```

## Verified GitHub Commands

```bash
gh auth status
gh repo view Yiping-Yin/ai-passport --json name,visibility,url,defaultBranchRef
gh issue list --repo Yiping-Yin/ai-passport --limit 200
gh api repos/Yiping-Yin/ai-passport/milestones?state=all&per_page=100
```

## Repository Notes

- The repo is initialized on `main`.
- The GitHub bootstrap script is the source of truth for labels, milestones, issues, and import manifest state.
- Project board creation depends on GitHub project permissions and API availability in the authenticated `gh` session.
