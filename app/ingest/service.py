"""Source intake and raw preservation services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.domain import PrivacyLevel, Source, SourceType, Workspace
from app.storage.sources import SourceRepository, create_source
from app.storage.workspaces import WorkspaceRepository


EXTENSIONS = {
    SourceType.WEB_PAGE: ".txt",
    SourceType.MARKDOWN: ".md",
    SourceType.PDF: ".pdf.txt",
    SourceType.PLAIN_TEXT: ".txt",
    SourceType.PROJECT_DOCUMENT: ".txt",
}


@dataclass(frozen=True, slots=True)
class SourceImportRequest:
    workspace_id: str
    source_type: SourceType | str
    title: str
    origin: str
    content: str
    imported_at: datetime
    privacy_level: PrivacyLevel | str | None = None
    tags: tuple[str, ...] = ()


def parse_source_type(value: SourceType | str) -> SourceType:
    if isinstance(value, SourceType):
        return value
    try:
        return SourceType(value)
    except ValueError as exc:
        raise ValueError(f"Invalid source type: {value}") from exc


def parse_privacy_level(value: PrivacyLevel | str | None, *, default: PrivacyLevel) -> PrivacyLevel:
    if value is None:
        return default
    if isinstance(value, PrivacyLevel):
        return value
    try:
        return PrivacyLevel(value)
    except ValueError as exc:
        raise ValueError(f"Invalid privacy level: {value}") from exc


class RawSourceStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write_raw_source(self, workspace: Workspace, source_id: str, source_type: SourceType, content: str) -> Path:
        raw_dir = self.root / workspace.workspace_type.value / workspace.id / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        path = raw_dir / f"{source_id}{EXTENSIONS[source_type]}"
        if path.exists():
            raise FileExistsError(f"Raw source already exists: {path}")
        path.write_text(content)
        return path

    def read_raw_source(self, raw_blob_ref: str) -> str:
        return Path(raw_blob_ref).read_text()


class SourceImportService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        source_repository: SourceRepository,
        raw_store: RawSourceStore,
    ) -> None:
        self.workspaces = workspace_repository
        self.sources = source_repository
        self.raw_store = raw_store

    def import_source(self, request: SourceImportRequest) -> Source:
        workspace = self._get_workspace(request.workspace_id)
        source_type = parse_source_type(request.source_type)
        privacy_level = parse_privacy_level(request.privacy_level, default=workspace.privacy_default)
        source_id = f"src-{uuid4().hex[:12]}"
        raw_path = self.raw_store.write_raw_source(workspace, source_id, source_type, request.content)
        source = create_source(
            source_id=source_id,
            source_type=source_type,
            title=request.title,
            origin=request.origin,
            imported_at=request.imported_at,
            workspace_id=workspace.id,
            raw_blob_ref=str(raw_path),
            privacy_level=privacy_level,
            tags=request.tags,
        )
        return self.sources.create(source)

    def recompile_placeholder(self, source_id: str) -> Source:
        source = self.sources.get(source_id)
        if source is None:
            raise KeyError(f"Unknown source: {source_id}")
        return source

    def _get_workspace(self, workspace_id: str) -> Workspace:
        workspace = self.workspaces.get(workspace_id)
        if workspace is None:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        if workspace.archived_at is not None:
            raise ValueError(f"Archived workspace cannot accept new sources: {workspace_id}")
        return workspace
