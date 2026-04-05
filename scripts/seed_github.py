#!/usr/bin/env python3
"""Parse the execution backlog and seed GitHub artifacts idempotently."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent.parent
BACKLOG_PATH = ROOT / "docs" / "spec" / "execution-backlog.md"
BACKLOG_MANIFEST_PATH = ROOT / "state" / "backlog-manifest.json"
IMPORT_MANIFEST_PATH = ROOT / "state" / "github-import-manifest.json"

EXPECTED_COUNTS = {"epics": 8, "milestones": 24, "tickets": 83}
DOC_LINKS = {
    "product_prd": "docs/spec/product-prd.md",
    "execution_backlog": "docs/spec/execution-backlog.md",
}
AREA_LABELS = {
    1: "area:foundations",
    2: "area:workspace-intake",
    3: "area:compiler-evidence",
    4: "area:signals-focus",
    5: "area:postcards-passport",
    6: "area:mounting-access",
    7: "area:review-governance",
    8: "area:pilot-readiness",
}
LABEL_SPECS = {
    "type:epic": {"color": "5319e7", "description": "Backlog parent issue for an epic."},
    "type:ticket": {"color": "0e8a16", "description": "Execution ticket scoped to one milestone."},
    "area:foundations": {"color": "1d76db", "description": "Foundation, domain, and storage work."},
    "area:workspace-intake": {"color": "0052cc", "description": "Workspace lifecycle, inbox, and source intake."},
    "area:compiler-evidence": {"color": "0366d6", "description": "Compilation core and evidence traceability."},
    "area:signals-focus": {"color": "5319e7", "description": "Capability signals, mistake patterns, and focus work."},
    "area:postcards-passport": {"color": "fbca04", "description": "Postcards and Passport generation."},
    "area:mounting-access": {"color": "d93f0b", "description": "Mounting, visas, sessions, and access control."},
    "area:review-governance": {"color": "b60205", "description": "Review queue, audit, export, and recovery."},
    "area:pilot-readiness": {"color": "0e8a16", "description": "Thin UI, quality gates, and pilot readiness."},
    "blocked": {"color": "000000", "description": "Blocked by dependency, scope, or external state."},
}


def run(cmd: list[str], *, capture: bool = True, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=check,
    )


def gh_json(args: list[str], *, check: bool = True) -> Any:
    result = run(["gh", *args], check=check)
    output = result.stdout.strip()
    return json.loads(output) if output else None


def gh_api(path: str, *, method: str = "GET", fields: dict[str, Any] | None = None, check: bool = True) -> Any:
    cmd = [
        "gh",
        "api",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2026-03-10",
        path,
    ]
    if method != "GET":
        cmd.extend(["-X", method])
    if fields:
        for key, value in fields.items():
            if isinstance(value, list):
                for item in value:
                    cmd.extend(["-f", f"{key}[]={item}"])
                continue
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, (dict, list)):
                value = json.dumps(value)
            else:
                value = str(value)
            cmd.extend(["-f", f"{key}={value}"])
    result = run(cmd, check=check)
    output = result.stdout.strip()
    return json.loads(output) if output else None


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def parse_backlog(text: str) -> dict[str, Any]:
    epic_split = re.split(r"(?m)^# (Epic \d+\. .+)$", text)
    if len(epic_split) < 3:
        raise ValueError("No epic sections found in execution backlog.")

    epics: list[dict[str, Any]] = []
    for index in range(1, len(epic_split), 2):
        epic_title = epic_split[index].strip()
        epic_body = epic_split[index + 1]
        epic_number_match = re.search(r"Epic (\d+)\.", epic_title)
        if not epic_number_match:
            raise ValueError(f"Unable to parse epic number from {epic_title!r}")
        epic_number = int(epic_number_match.group(1))
        goal = extract_block(epic_body, "Goal")
        related_prd = extract_block(epic_body, "Related PRD")
        milestones = parse_milestones(epic_body, epic_title, epic_number)
        epics.append(
            {
                "number": epic_number,
                "title": epic_title,
                "goal": goal,
                "related_prd": related_prd,
                "area_label": AREA_LABELS[epic_number],
                "milestones": milestones,
            }
        )

    definition_of_done = parse_numbered_list(text, "## 5. Definition of Done")
    manifest = {
        "epics": epics,
        "definition_of_done": definition_of_done,
        "counts": {
            "epics": len(epics),
            "milestones": sum(len(epic["milestones"]) for epic in epics),
            "tickets": sum(len(milestone["tickets"]) for epic in epics for milestone in epic["milestones"]),
        },
    }
    return manifest


def extract_block(section: str, label: str) -> str:
    pattern = re.compile(rf"\*\*{re.escape(label)}\*\*\s*\n(.+?)(?=\n\n\*\*|\n\n### |\n\n# |\Z)", re.S)
    match = pattern.search(section)
    if not match:
        raise ValueError(f"Missing block {label!r}")
    return normalize_whitespace(match.group(1))


def parse_milestones(epic_body: str, epic_title: str, epic_number: int) -> list[dict[str, Any]]:
    milestone_split = re.split(r"(?m)^### (Milestone \d+\.\d+ — .+)$", epic_body)
    milestones: list[dict[str, Any]] = []
    for index in range(1, len(milestone_split), 2):
        milestone_title = milestone_split[index].strip()
        milestone_body = milestone_split[index + 1]
        outcome = extract_block(milestone_body, "Outcome")
        tickets = parse_tickets(milestone_body, milestone_title, epic_title)
        milestones.append(
            {
                "title": milestone_title,
                "outcome": outcome,
                "epic_number": epic_number,
                "epic_title": epic_title,
                "tickets": tickets,
            }
        )
    return milestones


def parse_tickets(milestone_body: str, milestone_title: str, epic_title: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"^\- \*\*(E\d+\-M\d+\-T\d+)\s+—\s+(.+?)\*\*\s*\n"
        r"\s+(.+?)\s*\n"
        r"\s+\*\*Acceptance:\*\*\s+(.+?)\s*(?=\n\n- \*\*E|\n\n### |\n\n---|\Z)",
        re.M | re.S,
    )
    tickets: list[dict[str, Any]] = []
    for match in pattern.finditer(milestone_body):
        code, title, summary, acceptance = match.groups()
        tickets.append(
            {
                "code": code,
                "title": f"{code} — {normalize_whitespace(title)}",
                "short_title": normalize_whitespace(title),
                "summary": normalize_whitespace(summary),
                "acceptance": normalize_whitespace(acceptance),
                "milestone": milestone_title,
                "epic_title": epic_title,
            }
        )
    if not tickets:
        raise ValueError(f"No tickets parsed for {milestone_title!r}")
    return tickets


def parse_numbered_list(text: str, heading: str) -> list[str]:
    pattern = re.compile(rf"{re.escape(heading)}\n\n.+?:\n((?:\d+\..+\n)+)", re.M)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Missing numbered list under {heading!r}")
    return [normalize_whitespace(line.split(".", 1)[1]) for line in match.group(1).strip().splitlines()]


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("→", "->")).strip()


def validate_counts(manifest: dict[str, Any]) -> None:
    for key, expected in EXPECTED_COUNTS.items():
        actual = manifest["counts"][key]
        if actual != expected:
            raise ValueError(f"Expected {expected} {key}, found {actual}")


def repo_web_base(repo: str) -> str:
    return f"https://github.com/{repo}/blob/main"


def build_epic_body(epic: dict[str, Any], definition_of_done: list[str], repo: str, ticket_links: dict[str, dict[str, Any]]) -> str:
    lines = [
        "## Goal",
        epic["goal"],
        "",
        "## Related PRD",
        f"- {epic['related_prd']}",
        "",
        "## Milestones",
    ]
    for milestone in epic["milestones"]:
        lines.append(f"- [ ] {milestone['title']} — {milestone['outcome']}")

    lines.extend(["", "## Child Tickets"])
    for milestone in epic["milestones"]:
        lines.append(f"### {milestone['title']}")
        for ticket in milestone["tickets"]:
            ticket_meta = ticket_links.get(ticket["code"])
            if ticket_meta:
                lines.append(f"- [ ] #{ticket_meta['number']} {ticket['title']}")
            else:
                lines.append(f"- [ ] {ticket['title']}")

    lines.extend(["", "## Exit Criteria"])
    for item in definition_of_done:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Source Docs",
            f"- [`{DOC_LINKS['product_prd']}`]({repo_web_base(repo)}/{DOC_LINKS['product_prd']})",
            f"- [`{DOC_LINKS['execution_backlog']}`]({repo_web_base(repo)}/{DOC_LINKS['execution_backlog']})",
        ]
    )
    return "\n".join(lines).strip()


def build_ticket_body(ticket: dict[str, Any], epic_issue: dict[str, Any], related_prd: str, repo: str) -> str:
    return "\n".join(
        [
            "## Summary",
            ticket["summary"],
            "",
            "## Acceptance Criteria",
            f"- {ticket['acceptance']}",
            "",
            "## Related PRD",
            f"- {related_prd}",
            "",
            "## Parent Epic",
            f"- #{epic_issue['number']} {epic_issue['title']}",
            "",
            "## Milestone",
            f"- {ticket['milestone']}",
            "",
            "## Dependencies",
            "- Respect the execution order in `docs/spec/execution-backlog.md` and do not build outside the active milestone.",
            "",
            "## Source Docs",
            f"- [`{DOC_LINKS['product_prd']}`]({repo_web_base(repo)}/{DOC_LINKS['product_prd']})",
            f"- [`{DOC_LINKS['execution_backlog']}`]({repo_web_base(repo)}/{DOC_LINKS['execution_backlog']})",
        ]
    ).strip()


def ensure_labels(repo: str, state: dict[str, Any]) -> None:
    existing = {label["name"]: label for label in gh_api(f"repos/{repo}/labels?per_page=100")}
    for name, spec in LABEL_SPECS.items():
        payload = {"name": name, "color": spec["color"], "description": spec["description"]}
        if name in existing:
            gh_api(
                f"repos/{repo}/labels/{quote(name, safe='')}",
                method="PATCH",
                fields=payload,
            )
            label = gh_api(f"repos/{repo}/labels/{quote(name, safe='')}")
        else:
            label = gh_api(f"repos/{repo}/labels", method="POST", fields=payload)
        state["labels"][name] = {
            "name": label["name"],
            "url": label["url"],
            "color": label["color"],
        }


def ensure_milestones(repo: str, manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    existing = {item["title"]: item for item in gh_api(f"repos/{repo}/milestones?state=all&per_page=100")}
    result: dict[str, Any] = {}
    for epic in manifest["epics"]:
        for milestone in epic["milestones"]:
            title = milestone["title"]
            description = f"{milestone['outcome']} Parent epic: {epic['title']}."
            if title in existing:
                item = gh_api(
                    f"repos/{repo}/milestones/{existing[title]['number']}",
                    method="PATCH",
                    fields={"title": title, "description": description, "state": "open"},
                )
            else:
                item = gh_api(
                    f"repos/{repo}/milestones",
                    method="POST",
                    fields={"title": title, "description": description},
                )
            result[title] = item
            state["milestones"][title] = {
                "number": item["number"],
                "url": item["html_url"],
                "description": item["description"],
            }
    return result


def list_existing_issues(repo: str) -> dict[str, Any]:
    issues = gh_api(f"repos/{repo}/issues?state=all&per_page=100")
    return {issue["title"]: issue for issue in issues if "pull_request" not in issue}


def sync_issue(repo: str, title: str, body: str, labels: list[str], milestone_number: int | None, existing_issue: dict[str, Any] | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": title, "body": body, "labels": labels}
    if milestone_number is not None:
        payload["milestone"] = milestone_number
    if existing_issue:
        issue = gh_api(f"repos/{repo}/issues/{existing_issue['number']}", method="PATCH", fields=payload)
    else:
        issue = gh_api(f"repos/{repo}/issues", method="POST", fields=payload)
    return issue


def ensure_epics_and_tickets(repo: str, manifest: dict[str, Any], milestones: dict[str, Any], state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    existing = list_existing_issues(repo)
    epic_issues: dict[str, Any] = {}
    ticket_issues: dict[str, Any] = {}

    for epic in manifest["epics"]:
        body = build_epic_body(epic, manifest["definition_of_done"], repo, {})
        issue = sync_issue(repo, epic["title"], body, ["type:epic", epic["area_label"]], None, existing.get(epic["title"]))
        epic_issues[epic["title"]] = issue
        state["epics"][epic["title"]] = {"number": issue["number"], "url": issue["html_url"]}
        existing[epic["title"]] = issue

    for epic in manifest["epics"]:
        parent_issue = epic_issues[epic["title"]]
        for milestone in epic["milestones"]:
            milestone_number = milestones[milestone["title"]]["number"]
            for ticket in milestone["tickets"]:
                body = build_ticket_body(ticket, parent_issue, epic["related_prd"], repo)
                issue = sync_issue(
                    repo,
                    ticket["title"],
                    body,
                    ["type:ticket", epic["area_label"]],
                    milestone_number,
                    existing.get(ticket["title"]),
                )
                ticket_issues[ticket["code"]] = issue
                state["tickets"][ticket["code"]] = {
                    "number": issue["number"],
                    "url": issue["html_url"],
                    "milestone": milestone["title"],
                    "epic": epic["title"],
                }
                existing[ticket["title"]] = issue

    for epic in manifest["epics"]:
        refreshed_body = build_epic_body(epic, manifest["definition_of_done"], repo, state["tickets"])
        issue = epic_issues[epic["title"]]
        updated_issue = gh_api(
            f"repos/{repo}/issues/{issue['number']}",
            method="PATCH",
            fields={"title": epic["title"], "body": refreshed_body, "labels": ["type:epic", epic["area_label"]]},
        )
        epic_issues[epic["title"]] = updated_issue
        state["epics"][epic["title"]] = {"number": updated_issue["number"], "url": updated_issue["html_url"]}

    return epic_issues, ticket_issues


def can_manage_projects(owner: str) -> tuple[bool, str | None]:
    result = run(["gh", "project", "list", "--owner", owner], check=False)
    if result.returncode == 0:
        return True, None
    message = (result.stderr or result.stdout).strip()
    return False, message


def ensure_project(repo: str, state: dict[str, Any], owner: str, all_issue_numbers: list[int]) -> None:
    ok, reason = can_manage_projects(owner)
    if not ok:
        state["warnings"].append(f"Project provisioning skipped: {reason}")
        return

    projects = gh_json(["project", "list", "--owner", owner, "--format", "json"]) or {"projects": []}
    existing_project = next((item for item in projects["projects"] if item["title"] == "AI Knowledge Passport Delivery"), None)
    if existing_project:
        project = existing_project
    else:
        project = gh_json(
            [
                "project",
                "create",
                "--owner",
                owner,
                "--title",
                "AI Knowledge Passport Delivery",
                "--format",
                "json",
            ]
        )

    project_number = project["number"]
    state["project"] = {
        "owner": owner,
        "number": project_number,
        "title": project["title"],
        "id": project.get("id"),
        "url": project.get("url"),
        "views": ["Current Milestone", "By Epic", "Blocked"],
    }

    run(["gh", "project", "link", str(project_number), "--owner", owner, "--repo", repo], capture=True, check=False)

    fields = gh_json(["project", "field-list", str(project_number), "--owner", owner, "--format", "json"]) or {"fields": []}
    status_field = next((item for item in fields["fields"] if item["name"] == "Status"), None)
    if not status_field:
        gh_json(
            [
                "project",
                "field-create",
                str(project_number),
                "--owner",
                owner,
                "--name",
                "Status",
                "--data-type",
                "SINGLE_SELECT",
                "--single-select-options",
                "Backlog,Ready,In Progress,In Review,Done,Blocked",
                "--format",
                "json",
            ]
        )

    existing_items = gh_json(["project", "item-list", str(project_number), "--owner", owner, "--format", "json"]) or {"items": []}
    existing_content_ids = {
        item.get("content", {}).get("number")
        for item in existing_items["items"]
        if isinstance(item.get("content"), dict)
    }
    for number in all_issue_numbers:
        if number in existing_content_ids:
            continue
        run(
            [
                "gh",
                "project",
                "item-add",
                str(project_number),
                "--owner",
                owner,
                "--url",
                f"https://github.com/{repo}/issues/{number}",
            ],
            capture=True,
            check=False,
        )

    state["warnings"].append(
        "GitHub project saved views are not exposed through the current CLI workflow; create the named views in the web UI if they are still missing."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub repository in OWNER/REPO format.")
    parser.add_argument("--validate-only", action="store_true", help="Parse and validate backlog counts only.")
    parser.add_argument("--seed", action="store_true", help="Seed labels, milestones, issues, and project data.")
    parser.add_argument("--project-owner", default="Yiping-Yin", help="GitHub project owner for project provisioning.")
    args = parser.parse_args()

    if args.validate_only and args.seed:
        parser.error("Choose only one of --validate-only or --seed.")
    if not args.validate_only and not args.seed:
        parser.error("One of --validate-only or --seed is required.")

    text = BACKLOG_PATH.read_text()
    manifest = parse_backlog(text)
    validate_counts(manifest)
    write_json(BACKLOG_MANIFEST_PATH, manifest)

    if args.validate_only:
        print(json.dumps({"status": "ok", "counts": manifest["counts"]}, indent=2))
        return 0

    state = load_json(
        IMPORT_MANIFEST_PATH,
        {"repo": None, "labels": {}, "milestones": {}, "epics": {}, "tickets": {}, "project": None, "warnings": []},
    )
    state["repo"] = args.repo
    state["warnings"] = []

    ensure_labels(args.repo, state)
    milestones = ensure_milestones(args.repo, manifest, state)
    epic_issues, ticket_issues = ensure_epics_and_tickets(args.repo, manifest, milestones, state)
    ensure_project(
        args.repo,
        state,
        args.project_owner,
        [issue["number"] for issue in [*epic_issues.values(), *ticket_issues.values()]],
    )
    write_json(IMPORT_MANIFEST_PATH, state)
    print(json.dumps({"status": "ok", "warnings": state["warnings"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
