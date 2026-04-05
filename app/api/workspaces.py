"""Workspace service and active-workspace state for Milestone 2.1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.domain import PassportReadiness, PrivacyLevel, Source, SourceType, Workspace, WorkspaceType, serialize_entity
from app.storage.sources import SourceRepository, create_source
from app.storage.workspaces import WorkspaceRepository, create_workspace


@dataclass(frozen=True, slots=True)
class WorkspaceReadinessPlaceholder:
    workspace_id: str
    imported_source_count: int
    readiness: PassportReadiness
    dashboard_state: str
    can_generate_passport_draft: bool


def parse_workspace_type(value: WorkspaceType | str) -> WorkspaceType:
    if isinstance(value, WorkspaceType):
        return value
    try:
        return WorkspaceType(value)
    except ValueError as exc:
        raise ValueError(f"Invalid workspace type: {value}") from exc


class WorkspaceService:
    def __init__(self, workspace_repository: WorkspaceRepository, source_repository: SourceRepository) -> None:
        self.workspaces = workspace_repository
        self.sources = source_repository

    def create_workspace(
        self,
        *,
        workspace_type: WorkspaceType | str,
        title: str,
        now: datetime,
        description: str | None = None,
        tags: tuple[str, ...] = (),
        privacy_default: PrivacyLevel = PrivacyLevel.PRIVATE,
    ) -> Workspace:
        workspace = create_workspace(
            workspace_id=f"ws-{uuid4().hex[:12]}",
            workspace_type=parse_workspace_type(workspace_type),
            title=title,
            now=now,
            description=description,
            tags=tags,
            privacy_default=privacy_default,
        )
        return self.workspaces.create(workspace)

    def list_workspaces(self, *, include_archived: bool = False) -> tuple[Workspace, ...]:
        return self.workspaces.list(include_archived=include_archived)

    def get_workspace(self, workspace_id: str) -> Workspace:
        workspace = self.workspaces.get(workspace_id)
        if workspace is None:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        return workspace

    def update_workspace(
        self,
        workspace_id: str,
        *,
        now: datetime,
        title: str | None = None,
        description: str | None = None,
        tags: tuple[str, ...] | None = None,
        privacy_default: PrivacyLevel | None = None,
        passport_readiness: PassportReadiness | None = None,
    ) -> Workspace:
        current = self.get_workspace(workspace_id)
        updated = Workspace(
            id=current.id,
            workspace_type=current.workspace_type,
            title=title if title is not None else current.title,
            created_at=current.created_at,
            updated_at=now,
            description=description if description is not None else current.description,
            tags=tags if tags is not None else current.tags,
            privacy_default=privacy_default if privacy_default is not None else current.privacy_default,
            passport_readiness=passport_readiness if passport_readiness is not None else current.passport_readiness,
            archived_at=current.archived_at,
        )
        return self.workspaces.update(updated)

    def archive_workspace(self, workspace_id: str, *, archived_at: datetime) -> Workspace:
        return self.workspaces.archive(workspace_id, archived_at)

    def readiness_placeholder(self, workspace_id: str) -> WorkspaceReadinessPlaceholder:
        workspace = self.get_workspace(workspace_id)
        imported_source_count = self.sources.count_by_workspace(workspace_id)

        if workspace.passport_readiness is PassportReadiness.READY:
            dashboard_state = "ready_for_draft"
            can_generate_passport_draft = True
        elif imported_source_count == 0:
            dashboard_state = "not_started"
            can_generate_passport_draft = False
        else:
            dashboard_state = "in_progress"
            can_generate_passport_draft = False

        return WorkspaceReadinessPlaceholder(
            workspace_id=workspace_id,
            imported_source_count=imported_source_count,
            readiness=workspace.passport_readiness,
            dashboard_state=dashboard_state,
            can_generate_passport_draft=can_generate_passport_draft,
        )


class ActiveWorkspaceState:
    def __init__(self, workspace_service: WorkspaceService, source_repository: SourceRepository) -> None:
        self.workspace_service = workspace_service
        self.source_repository = source_repository
        self._active_workspace_id: str | None = None

    @property
    def active_workspace_id(self) -> str | None:
        return self._active_workspace_id

    def set_active_workspace(self, workspace_id: str) -> Workspace:
        workspace = self.workspace_service.get_workspace(workspace_id)
        if workspace.archived_at is not None:
            raise ValueError(f"Archived workspace cannot become active: {workspace_id}")
        self._active_workspace_id = workspace_id
        return workspace

    def active_workspace(self) -> Workspace | None:
        if self._active_workspace_id is None:
            return None
        return self.workspace_service.get_workspace(self._active_workspace_id)

    def visible_sources(self) -> tuple[Source, ...]:
        if self._active_workspace_id is None:
            return ()
        return self.source_repository.list_by_workspace(self._active_workspace_id)

    def switcher_snapshot(self) -> dict[str, object]:
        workspace = self.active_workspace()
        placeholder = (
            self.workspace_service.readiness_placeholder(workspace.id)
            if workspace is not None
            else None
        )
        return {
            "active_workspace": serialize_entity(workspace) if workspace is not None else None,
            "visible_source_ids": [source.id for source in self.visible_sources()],
            "readiness": {
                "workspace_id": placeholder.workspace_id,
                "imported_source_count": placeholder.imported_source_count,
                "readiness": placeholder.readiness.value,
                "dashboard_state": placeholder.dashboard_state,
                "can_generate_passport_draft": placeholder.can_generate_passport_draft,
            }
            if placeholder is not None
            else None,
        }


class WorkspaceAPI:
    def __init__(self, service: WorkspaceService, state: ActiveWorkspaceState) -> None:
        self.service = service
        self.state = state

    def create_workspace(self, **kwargs: object) -> dict[str, object]:
        workspace = self.service.create_workspace(**kwargs)
        return serialize_entity(workspace)

    def list_workspaces(self, *, include_archived: bool = False) -> list[dict[str, object]]:
        return [serialize_entity(workspace) for workspace in self.service.list_workspaces(include_archived=include_archived)]

    def read_workspace(self, workspace_id: str) -> dict[str, object]:
        return serialize_entity(self.service.get_workspace(workspace_id))

    def update_workspace(self, workspace_id: str, **kwargs: object) -> dict[str, object]:
        return serialize_entity(self.service.update_workspace(workspace_id, **kwargs))

    def archive_workspace(self, workspace_id: str, *, archived_at: datetime) -> dict[str, object]:
        return serialize_entity(self.service.archive_workspace(workspace_id, archived_at=archived_at))

    def switch_active_workspace(self, workspace_id: str) -> dict[str, object]:
        self.state.set_active_workspace(workspace_id)
        return self.state.switcher_snapshot()


def create_demo_source_for_workspace(
    *,
    source_repository: SourceRepository,
    workspace_id: str,
    source_id: str,
    now: datetime,
    title: str,
) -> Source:
    return source_repository.create(
        create_source(
            source_id=source_id,
            source_type=SourceType.MARKDOWN,
            title=title,
            origin=f"{title.lower().replace(' ', '_')}.md",
            imported_at=now,
            workspace_id=workspace_id,
            raw_blob_ref=f"data/workspaces/{workspace_id}/{source_id}.md",
        )
    )
