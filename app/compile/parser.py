"""Simple parser for foundational knowledge-node generation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain import NodeType


SECTION_HEADER = re.compile(r"^(?:#+\s*)?(Topic|Project|Method|Question)\s*:\s*(.+?)\s*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NodeDraft:
    node_type: NodeType
    title: str
    summary: str
    body: str
    related_refs: tuple[str, ...]
    line_start: int
    line_end: int


def parse_source_to_drafts(content: str, *, fallback_title: str | None = None) -> tuple[NodeDraft, ...]:
    lines = content.splitlines()
    sections: list[tuple[NodeType, str, list[str]]] = []
    current: tuple[NodeType, str, list[str]] | None = None

    for index, line in enumerate(lines, start=1):
        match = SECTION_HEADER.match(line.strip())
        if match:
            if current is not None:
                sections.append(current)
            current = (NodeType(match.group(1).lower()), match.group(2).strip(), [index])
            continue
        if current is not None:
            current[2].append(line.rstrip())

    if current is not None:
        sections.append(current)

    if not sections and fallback_title:
        return (
            NodeDraft(
                node_type=NodeType.TOPIC,
                title=fallback_title,
                summary=content.strip().splitlines()[0].strip() if content.strip() else fallback_title,
                body=content.strip() or fallback_title,
                related_refs=(),
                line_start=1,
                line_end=max(1, len(lines)),
            ),
        )

    drafts: list[NodeDraft] = []
    for node_type, title, section_lines in sections:
        line_start = section_lines[0] if isinstance(section_lines[0], int) else 1
        content_lines = [line for line in section_lines[1:]]
        summary = ""
        body_lines: list[str] = []
        related_refs: list[str] = []
        for raw_line in content_lines:
            stripped = raw_line.strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if lower.startswith("summary:"):
                summary = stripped.split(":", 1)[1].strip()
                continue
            if lower.startswith("related:"):
                values = stripped.split(":", 1)[1].strip()
                related_refs.extend(part.strip() for part in values.split(",") if part.strip())
                continue
            body_lines.append(stripped)
        if not summary:
            summary = body_lines[0] if body_lines else title
        body = "\n".join(body_lines) if body_lines else summary
        drafts.append(
            NodeDraft(
                node_type=node_type,
                title=title,
                summary=summary,
                body=body,
                related_refs=tuple(related_refs),
                line_start=line_start,
                line_end=line_start + len(content_lines),
            )
        )
    return tuple(drafts)
