"""Wiki-first vault configuration, scanning, and generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import json
import re
import subprocess
from pathlib import Path

from app.compile.parser import parse_source_to_drafts
from app.domain import NodeType, Workspace
from app.storage.workspaces import WorkspaceRepository
from app.utils.time import utc_now


INDEX_FILENAME = ".wiki-index.json"
SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf", ".pdf.txt"}


class AIGenerationStatus(str):
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    ENHANCED = "enhanced"


@dataclass(frozen=True, slots=True)
class VaultConfig:
    workspace_id: str
    source_root: str | None
    wiki_root: str
    watcher_enabled: bool
    ai_enabled: bool
    watch_interval_seconds: float
    last_scan_at: str | None = None
    last_build_status: str = "not_started"
    last_error: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScannedSource:
    id: str
    relative_path: str
    absolute_path: str
    source_type: str
    title: str
    content_hash: str
    content: str


@dataclass(frozen=True, slots=True)
class WikiPage:
    kind: str
    slug: str
    title: str
    relative_path: str
    source_ids: tuple[str, ...]
    backlinks: tuple[str, ...]
    source_refs: tuple[str, ...]
    summary: str
    body: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WikiBuildResult:
    workspace_id: str
    generated_at: str
    scanned_file_count: int
    changed_file_count: int
    removed_file_count: int
    skipped_files: tuple[str, ...]
    warnings: tuple[str, ...]
    ai_status: str
    home_page: str
    pages: tuple[WikiPage, ...]


class WikiService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        raw_root: Path,
    ) -> None:
        self.workspaces = workspace_repository
        self.raw_root = raw_root

    def get_or_create_vault(self, workspace_id: str) -> VaultConfig:
        workspace = self._get_workspace(workspace_id)
        path = self._vault_config_path(workspace)
        if path.exists():
            return VaultConfig(**json.loads(path.read_text()))
        config = VaultConfig(
            workspace_id=workspace_id,
            source_root=None,
            wiki_root=str(self._workspace_root(workspace) / "wiki"),
            watcher_enabled=False,
            ai_enabled=False,
            watch_interval_seconds=2.0,
        )
        self._write_vault(config)
        return config

    def update_vault(
        self,
        workspace_id: str,
        *,
        source_root: str | None = None,
        wiki_root: str | None = None,
        watcher_enabled: bool | None = None,
        ai_enabled: bool | None = None,
        watch_interval_seconds: float | None = None,
        last_scan_at: str | None = None,
        last_build_status: str | None = None,
        last_error: str | None = None,
        warnings: tuple[str, ...] | None = None,
    ) -> VaultConfig:
        current = self.get_or_create_vault(workspace_id)
        updated = VaultConfig(
            workspace_id=current.workspace_id,
            source_root=source_root if source_root is not None else current.source_root,
            wiki_root=wiki_root if wiki_root is not None else current.wiki_root,
            watcher_enabled=watcher_enabled if watcher_enabled is not None else current.watcher_enabled,
            ai_enabled=ai_enabled if ai_enabled is not None else current.ai_enabled,
            watch_interval_seconds=watch_interval_seconds if watch_interval_seconds is not None else current.watch_interval_seconds,
            last_scan_at=last_scan_at if last_scan_at is not None else current.last_scan_at,
            last_build_status=last_build_status if last_build_status is not None else current.last_build_status,
            last_error=last_error if last_error is not None else current.last_error,
            warnings=warnings if warnings is not None else current.warnings,
        )
        self._write_vault(updated)
        return updated

    def scan_and_build(self, workspace_id: str) -> WikiBuildResult:
        config = self.get_or_create_vault(workspace_id)
        if not config.source_root:
            raise ValueError(f"Workspace {workspace_id} has no source folder configured")
        source_root = Path(config.source_root).expanduser()
        if not source_root.exists():
            raise ValueError(f"Source folder does not exist: {source_root}")
        wiki_root = Path(config.wiki_root).expanduser()
        wiki_root.mkdir(parents=True, exist_ok=True)

        previous_index = self._read_index(wiki_root)
        previous_files = previous_index.get("files", {}) if previous_index else {}
        scanned, skipped, warnings = self._scan_sources(source_root)
        current_files = {source.relative_path: source.content_hash for source in scanned}
        changed_count = sum(1 for path, content_hash in current_files.items() if previous_files.get(path) != content_hash)
        removed_paths = [path for path in previous_files if path not in current_files]
        removed_count = len(removed_paths)

        pages, ai_status, ai_warnings = self._build_pages(scanned, config.ai_enabled)
        warnings = (*warnings, *ai_warnings)
        self._write_pages(wiki_root, pages)
        self._cleanup_removed_pages(wiki_root, previous_index, {page.relative_path for page in pages})
        self._write_indexes(
            wiki_root,
            workspace_id=workspace_id,
            scanned=scanned,
            pages=pages,
            warnings=warnings,
            skipped=skipped,
            ai_status=ai_status,
        )
        result = WikiBuildResult(
            workspace_id=workspace_id,
            generated_at=utc_now().isoformat(),
            scanned_file_count=len(scanned),
            changed_file_count=changed_count,
            removed_file_count=removed_count,
            skipped_files=tuple(skipped),
            warnings=tuple(warnings),
            ai_status=ai_status,
            home_page="_index.md",
            pages=tuple(pages),
        )
        self.update_vault(
            workspace_id,
            last_scan_at=result.generated_at,
            last_build_status="ready",
            last_error=None,
            warnings=result.warnings,
        )
        return result

    def status(self, workspace_id: str) -> dict[str, object]:
        config = self.get_or_create_vault(workspace_id)
        wiki_root = Path(config.wiki_root)
        index = self._read_index(wiki_root)
        return {
            "vault": asdict(config),
            "build": index,
        }

    def page_index(self, workspace_id: str) -> dict[str, object]:
        config = self.get_or_create_vault(workspace_id)
        index = self._read_index(Path(config.wiki_root))
        if index is None:
            return {
                "workspace_id": workspace_id,
                "home_page": None,
                "pages": [],
                "files": {},
                "warnings": [],
            }
        return index

    def read_page(self, workspace_id: str, relative_path: str) -> str:
        config = self.get_or_create_vault(workspace_id)
        page_path = Path(config.wiki_root) / relative_path
        if not page_path.exists():
            raise KeyError(f"Unknown wiki page: {relative_path}")
        return page_path.read_text()

    def _scan_sources(self, source_root: Path) -> tuple[list[ScannedSource], list[str], list[str]]:
        scanned: list[ScannedSource] = []
        skipped: list[str] = []
        warnings: list[str] = []
        for path in sorted(source_root.rglob("*")):
            if path.is_dir():
                continue
            suffix = self._source_suffix(path)
            if suffix not in SUPPORTED_SUFFIXES:
                skipped.append(str(path.relative_to(source_root)))
                continue
            try:
                content = self._read_source_content(path)
            except RuntimeError as exc:
                skipped.append(str(path.relative_to(source_root)))
                warnings.append(str(exc))
                continue
            relative_path = str(path.relative_to(source_root))
            scanned.append(
                ScannedSource(
                    id=f"src-{self._hash(relative_path)[:12]}",
                    relative_path=relative_path,
                    absolute_path=str(path),
                    source_type=self._source_type_for_path(path),
                    title=path.stem.replace("_", " ").replace("-", " "),
                    content_hash=self._hash(content),
                    content=content,
                )
            )
        return scanned, skipped, warnings

    def _build_pages(self, scanned: list[ScannedSource], ai_enabled: bool) -> tuple[list[WikiPage], str, tuple[str, ...]]:
        nodes: dict[tuple[str, str], dict[str, object]] = {}
        source_refs: dict[str, list[str]] = {}
        warnings: list[str] = []
        ai_status = AIGenerationStatus.DISABLED
        ai_available = ai_enabled and bool(__import__("os").environ.get("OPENAI_API_KEY"))
        if ai_enabled and not ai_available:
            ai_status = AIGenerationStatus.UNAVAILABLE
            warnings.append("AI enhancement requested but OPENAI_API_KEY is not set; using deterministic generation.")
        elif ai_enabled and ai_available:
            ai_status = AIGenerationStatus.ENHANCED

        for source in scanned:
            drafts = parse_source_to_drafts(source.content, fallback_title=source.title)
            source_refs[source.id] = []
            for draft in drafts:
                key = (draft.node_type.value, draft.title.strip().lower())
                page_slug = self._slug(draft.title)
                page_path = f"{draft.node_type.value}s/{page_slug}.md"
                source_refs[source.id].append(page_path)
                if key not in nodes:
                    summary = draft.summary
                    body = draft.body
                    if ai_status == AIGenerationStatus.ENHANCED:
                        summary, body = self._enhance(summary, body)
                    nodes[key] = {
                        "kind": draft.node_type.value,
                        "slug": page_slug,
                        "title": draft.title,
                        "summary": summary,
                        "body_sections": [f"### Source: {source.relative_path}\n\n{body}"],
                        "related_refs": set(draft.related_refs),
                        "source_ids": {source.id},
                        "source_paths": {source.relative_path},
                    }
                else:
                    nodes[key]["body_sections"].append(f"### Source: {source.relative_path}\n\n{draft.body}")
                    nodes[key]["related_refs"].update(draft.related_refs)
                    nodes[key]["source_ids"].add(source.id)
                    nodes[key]["source_paths"].add(source.relative_path)

        id_map = {
            (kind, title): f"{kind}s/{self._slug(title)}.md"
            for kind, title in nodes
        }
        backlinks: dict[str, set[str]] = {path: set() for path in id_map.values()}
        related_targets: dict[str, set[str]] = {path: set() for path in id_map.values()}

        for (kind, title), data in nodes.items():
            current_path = id_map[(kind, title)]
            for ref in data["related_refs"]:
                target = self._resolve_ref(ref, id_map)
                if target is None or target == current_path:
                    continue
                related_targets[current_path].add(target)
                backlinks[target].add(current_path)

        pages: list[WikiPage] = []
        for (kind, title), data in sorted(nodes.items()):
            page_path = id_map[(kind, title)]
            pages.append(
                WikiPage(
                    kind=kind,
                    slug=data["slug"],
                    title=title,
                    relative_path=page_path,
                    source_ids=tuple(sorted(data["source_ids"])),
                    backlinks=tuple(sorted(backlinks[page_path])),
                    source_refs=tuple(sorted(data["source_paths"])),
                    summary=data["summary"],
                    body="\n\n".join(data["body_sections"]),
                    warnings=(),
                )
            )

        pages.extend(self._source_pages(scanned, source_refs))
        pages.extend(self._index_pages(pages, scanned))
        return pages, ai_status, tuple(warnings)

    def _source_pages(self, scanned: list[ScannedSource], source_refs: dict[str, list[str]]) -> list[WikiPage]:
        pages: list[WikiPage] = []
        for source in scanned:
            slug = self._slug(source.title)
            excerpt = "\n".join(source.content.splitlines()[:10]).strip()
            pages.append(
                WikiPage(
                    kind="source",
                    slug=slug,
                    title=source.title,
                    relative_path=f"sources/{slug}.md",
                    source_ids=(source.id,),
                    backlinks=(),
                    source_refs=tuple(sorted(source_refs[source.id])),
                    summary=f"Source file {source.relative_path}",
                    body=f"**Path:** `{source.relative_path}`\n\n## Linked Pages\n" + "\n".join(f"- [{ref}]({ref})" for ref in sorted(source_refs[source.id])) + f"\n\n## Excerpt\n\n{excerpt}",
                )
            )
        return pages

    def _index_pages(self, pages: list[WikiPage], scanned: list[ScannedSource]) -> list[WikiPage]:
        by_kind = {"topic": [], "project": [], "method": [], "question": [], "source": []}
        for page in pages:
            if page.kind in by_kind:
                by_kind[page.kind].append(page)
        generated_at = utc_now().isoformat()
        index_pages = [
            WikiPage(
                kind="index",
                slug="_index",
                title="Wiki Home",
                relative_path="_index.md",
                source_ids=(),
                backlinks=(),
                source_refs=(),
                summary="Knowledge wiki home",
                body=(
                    f"_Last generated: {generated_at}_\n\n"
                    f"- Sources: {len(scanned)}\n"
                    f"- Topics: {len(by_kind['topic'])}\n"
                    f"- Projects: {len(by_kind['project'])}\n"
                    f"- Methods: {len(by_kind['method'])}\n"
                    f"- Questions: {len(by_kind['question'])}\n\n"
                    "## Browse\n"
                    + "\n".join(
                        [
                            "- [Sources](sources/_index.md)",
                            "- [Topics](topics/_index.md)",
                            "- [Projects](projects/_index.md)",
                            "- [Methods](methods/_index.md)",
                            "- [Questions](questions/_index.md)",
                        ]
                    )
                ),
            )
        ]
        for kind in ("source", "topic", "project", "method", "question"):
            index_pages.append(
                WikiPage(
                    kind=f"{kind}_index",
                    slug="_index",
                    title=f"{kind.title()} Index",
                    relative_path=f"{kind}s/_index.md" if kind != "source" else "sources/_index.md",
                    source_ids=(),
                    backlinks=(),
                    source_refs=(),
                    summary=f"All {kind} pages",
                    body="\n".join(
                        [f"# {kind.title()} Index", ""] +
                        [f"- [{page.title}]({Path(page.relative_path).name})" for page in by_kind[kind]]
                    ),
                )
            )
        return index_pages

    def _write_pages(self, wiki_root: Path, pages: list[WikiPage]) -> None:
        for page in pages:
            page_path = wiki_root / page.relative_path
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_text(self._render_page(page))

    def _write_indexes(
        self,
        wiki_root: Path,
        *,
        workspace_id: str,
        scanned: list[ScannedSource],
        pages: list[WikiPage],
        warnings: tuple[str, ...],
        skipped: list[str],
        ai_status: str,
    ) -> None:
        index = {
            "workspace_id": workspace_id,
            "generated_at": utc_now().isoformat(),
            "home_page": "_index.md",
            "warnings": list(warnings),
            "skipped_files": skipped,
            "ai_status": ai_status,
            "files": {source.relative_path: source.content_hash for source in scanned},
            "pages": [
                {
                    "kind": page.kind,
                    "title": page.title,
                    "slug": page.slug,
                    "path": page.relative_path,
                    "source_ids": list(page.source_ids),
                    "backlinks": list(page.backlinks),
                    "source_refs": list(page.source_refs),
                    "summary": page.summary,
                }
                for page in pages
            ],
        }
        (wiki_root / INDEX_FILENAME).write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")

    def _cleanup_removed_pages(self, wiki_root: Path, previous_index: dict[str, object] | None, current_paths: set[str]) -> None:
        if not previous_index:
            return
        for page in previous_index.get("pages", []):
            relative = page["path"]
            if relative not in current_paths:
                stale = wiki_root / relative
                if stale.exists():
                    stale.unlink()

    def _render_page(self, page: WikiPage) -> str:
        lines = [f"# {page.title}", "", page.summary, "", page.body]
        if page.source_refs:
            lines.extend(["", "## Source References"])
            lines.extend(f"- [{ref}](../sources/{self._slug(Path(ref).stem)}.md)" if not ref.startswith("sources/") else f"- [{ref}]({Path(ref).name})" for ref in page.source_refs)
        if page.backlinks:
            lines.extend(["", "## Backlinks"])
            lines.extend(f"- [{Path(ref).stem.replace('-', ' ').title()}](../{ref})" for ref in page.backlinks)
        lines.extend(["", f"_Last generated: {utc_now().isoformat()}_"])
        return "\n".join(lines).strip() + "\n"

    def _read_index(self, wiki_root: Path) -> dict[str, object] | None:
        path = wiki_root / INDEX_FILENAME
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _enhance(self, summary: str, body: str) -> tuple[str, str]:
        lines = [segment.strip() for segment in body.splitlines() if segment.strip()]
        intro = lines[0] if lines else summary
        return (
            f"{summary} This page was enriched with optional AI-style heuristics.",
            f"## Overview\n\n{intro}\n\n## Details\n\n{body}",
        )

    def _resolve_ref(self, ref: str, id_map: dict[tuple[str, str], str]) -> str | None:
        ref = ref.strip()
        if ":" in ref:
            raw_kind, raw_title = ref.split(":", 1)
            kind = raw_kind.strip().lower()
            title = raw_title.strip().lower()
            return id_map.get((kind, title))
        for (kind, title), path in id_map.items():
            if title == ref.lower():
                return path
        return None

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:64] or "page"

    def _source_suffix(self, path: Path) -> str:
        if path.name.endswith(".pdf.txt"):
            return ".pdf.txt"
        return path.suffix.lower()

    def _source_type_for_path(self, path: Path) -> str:
        suffix = self._source_suffix(path)
        if suffix in {".md"}:
            return "markdown"
        if suffix in {".txt", ".pdf.txt"}:
            return "plain_text" if suffix == ".txt" else "pdf_text"
        if suffix == ".pdf":
            return "pdf"
        return "unknown"

    def _read_source_content(self, path: Path) -> str:
        suffix = self._source_suffix(path)
        if suffix in {".md", ".txt", ".pdf.txt"}:
            return path.read_text()
        if suffix == ".pdf":
            result = subprocess.run(
                ["pdftotext", str(path), "-"],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to extract PDF text from {path}")
            return result.stdout
        raise RuntimeError(f"Unsupported source type: {path}")

    def _get_workspace(self, workspace_id: str) -> Workspace:
        workspace = self.workspaces.get(workspace_id)
        if workspace is None:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        return workspace

    def _workspace_root(self, workspace: Workspace) -> Path:
        return self.raw_root / workspace.workspace_type.value / workspace.id

    def _vault_config_path(self, workspace: Workspace) -> Path:
        root = self._workspace_root(workspace)
        root.mkdir(parents=True, exist_ok=True)
        return root / "vault.json"

    def _write_vault(self, config: VaultConfig) -> None:
        workspace = self._get_workspace(config.workspace_id)
        path = self._vault_config_path(workspace)
        path.write_text(json.dumps(asdict(config), indent=2, sort_keys=True) + "\n")
