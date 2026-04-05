"""Manual edit views and compile diff support for generated nodes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import difflib

from app.domain import FieldProvenance, KnowledgeNode, OverrideMode, serialize_entity
from app.storage.knowledge_nodes import KnowledgeNodeRepository, KnowledgeNodeRevision
from app.storage.node_overrides import KnowledgeNodeFieldOverride, KnowledgeNodeOverrideRepository


EDITABLE_FIELDS = {"title", "summary", "body", "related_node_ids"}


@dataclass(frozen=True, slots=True)
class EffectiveKnowledgeNodeView:
    generated_node: KnowledgeNode
    effective_node: KnowledgeNode
    field_provenance: dict[str, FieldProvenance]
    overrides: tuple[KnowledgeNodeFieldOverride, ...]


@dataclass(frozen=True, slots=True)
class FieldDiff:
    field_name: str
    before: object
    after: object
    unified_diff: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class KnowledgeNodeDiff:
    node_id: str
    from_version: int
    to_version: int
    fields: tuple[FieldDiff, ...]


class KnowledgeNodeReviewService:
    def __init__(
        self,
        *,
        knowledge_node_repository: KnowledgeNodeRepository,
        override_repository: KnowledgeNodeOverrideRepository,
    ) -> None:
        self.nodes = knowledge_node_repository
        self.overrides = override_repository

    def set_field_override(
        self,
        *,
        node_id: str,
        field_name: str,
        value: object,
        editor: str,
        edited_at: datetime,
        override_mode: OverrideMode = OverrideMode.REPLACE,
    ) -> KnowledgeNodeFieldOverride:
        if field_name not in EDITABLE_FIELDS:
            raise ValueError(f"Unsupported editable field: {field_name}")
        override = KnowledgeNodeFieldOverride(
            node_id=node_id,
            field_name=field_name,
            override_mode=override_mode,
            value=value,
            edited_at=edited_at,
            editor=editor,
        )
        return self.overrides.upsert(override)

    def effective_view(self, node_id: str) -> EffectiveKnowledgeNodeView:
        generated = self.nodes.get(node_id)
        if generated is None:
            raise KeyError(f"Unknown node: {node_id}")
        overrides = self.overrides.list_for_node(node_id)
        effective = generated
        provenance: dict[str, FieldProvenance] = {
            "title": FieldProvenance.GENERATED,
            "summary": FieldProvenance.GENERATED,
            "body": FieldProvenance.GENERATED,
            "related_node_ids": FieldProvenance.GENERATED,
        }

        for override in overrides:
            if override.field_name == "title":
                effective = self._replace_node(effective, title=str(override.value))
                provenance["title"] = FieldProvenance.HUMAN_EDITED
            elif override.field_name == "summary":
                effective = self._replace_node(effective, summary=str(override.value))
                provenance["summary"] = FieldProvenance.HUMAN_EDITED
            elif override.field_name == "body":
                effective = self._replace_node(effective, body=str(override.value))
                provenance["body"] = FieldProvenance.HUMAN_EDITED
            elif override.field_name == "related_node_ids":
                override_values = tuple(str(item) for item in override.value)
                if override.override_mode is OverrideMode.MERGE:
                    merged = tuple(sorted(set(effective.related_node_ids).union(override_values)))
                    effective = self._replace_node(effective, related_node_ids=merged)
                    provenance["related_node_ids"] = FieldProvenance.MIXED
                else:
                    effective = self._replace_node(effective, related_node_ids=override_values)
                    provenance["related_node_ids"] = FieldProvenance.HUMAN_EDITED

        return EffectiveKnowledgeNodeView(
            generated_node=generated,
            effective_node=effective,
            field_provenance=provenance,
            overrides=overrides,
        )

    def diff_latest(self, node_id: str) -> KnowledgeNodeDiff | None:
        revisions = self.nodes.list_revisions(node_id)
        if len(revisions) < 2:
            return None
        before, after = revisions[-2], revisions[-1]
        field_diffs: list[FieldDiff] = []
        for field_name in ("title", "summary", "body", "related_node_ids"):
            before_value = getattr(before, field_name)
            after_value = getattr(after, field_name)
            if before_value == after_value:
                continue
            field_diffs.append(
                FieldDiff(
                    field_name=field_name,
                    before=before_value,
                    after=after_value,
                    unified_diff=tuple(
                        difflib.unified_diff(
                            _lines_for_diff(before_value),
                            _lines_for_diff(after_value),
                            fromfile=f"v{before.version}",
                            tofile=f"v{after.version}",
                            lineterm="",
                        )
                    ),
                )
            )
        return KnowledgeNodeDiff(
            node_id=node_id,
            from_version=before.version,
            to_version=after.version,
            fields=tuple(field_diffs),
        )

    @staticmethod
    def serialize_effective_view(view: EffectiveKnowledgeNodeView) -> dict[str, object]:
        return {
            "generated_node": serialize_entity(view.generated_node),
            "effective_node": serialize_entity(view.effective_node),
            "field_provenance": {key: value.value for key, value in view.field_provenance.items()},
            "overrides": [
                {
                    "field_name": override.field_name,
                    "override_mode": override.override_mode.value,
                    "value": override.value,
                    "edited_at": override.edited_at.isoformat(),
                    "editor": override.editor,
                }
                for override in view.overrides
            ],
        }

    @staticmethod
    def _replace_node(node: KnowledgeNode, **changes: object) -> KnowledgeNode:
        data = serialize_entity(node)
        data.update(changes)
        return KnowledgeNode(
            id=data["id"],
            node_type=node.node_type,
            title=data["title"],
            summary=data["summary"],
            body=data["body"],
            source_ids=tuple(data["source_ids"]),
            related_node_ids=tuple(data["related_node_ids"]),
            updated_at=node.updated_at,
            workspace_id=node.workspace_id,
            version=node.version,
        )


def _lines_for_diff(value: object) -> list[str]:
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return str(value).splitlines()
