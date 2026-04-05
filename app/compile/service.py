"""Knowledge-node generation service for Milestone 3.1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from uuid import uuid4

from app.compile.parser import NodeDraft, parse_source_to_drafts
from app.domain import CompileJob, CompileJobStatus, EvidenceFragment, KnowledgeNode, NodeType, Source, serialize_entity
from app.ingest.service import RawSourceStore
from app.storage.compile_jobs import CompileJobRepository
from app.storage.evidence import EvidenceFragmentRepository
from app.storage.knowledge_nodes import KnowledgeNodeRepository
from app.storage.node_evidence_links import NodeEvidenceLinkRepository
from app.storage.sources import SourceRepository


@dataclass(frozen=True, slots=True)
class CompileResult:
    job: CompileJob
    nodes: tuple[KnowledgeNode, ...]


@dataclass(frozen=True, slots=True)
class NodeEvidenceView:
    node: KnowledgeNode
    evidence_fragments: tuple[EvidenceFragment, ...]


@dataclass(frozen=True, slots=True)
class SourceJumpTarget:
    node_id: str
    source_id: str
    raw_blob_ref: str
    locator: str
    excerpt: str


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:48] or "node"


class KnowledgeCompileService:
    def __init__(
        self,
        *,
        source_repository: SourceRepository,
        compile_job_repository: CompileJobRepository,
        knowledge_node_repository: KnowledgeNodeRepository,
        evidence_repository: EvidenceFragmentRepository,
        node_evidence_link_repository: NodeEvidenceLinkRepository,
        raw_store: RawSourceStore,
    ) -> None:
        self.sources = source_repository
        self.jobs = compile_job_repository
        self.nodes = knowledge_node_repository
        self.evidence = evidence_repository
        self.node_evidence_links = node_evidence_link_repository
        self.raw_store = raw_store

    def compile_source(self, source_id: str, *, requested_at: datetime) -> CompileResult:
        source = self._get_source(source_id)
        job = self._queue_job(source, requested_at=requested_at)
        self.jobs.update_status(job.id, status=CompileJobStatus.RUNNING, now=requested_at)
        try:
            raw_content = self.raw_store.read_raw_source(source.raw_blob_ref)
            drafts = parse_source_to_drafts(raw_content, fallback_title=source.title)
            nodes = self._persist_nodes(source, drafts, now=requested_at)
            completed = self.jobs.update_status(job.id, status=CompileJobStatus.SUCCEEDED, now=requested_at)
            return CompileResult(job=completed, nodes=nodes)
        except Exception as exc:
            failed = self.jobs.update_status(job.id, status=CompileJobStatus.FAILED, now=requested_at, last_error=str(exc))
            raise RuntimeError(f"compile failed for {source_id} via {failed.id}") from exc

    def _persist_nodes(self, source: Source, drafts: tuple[NodeDraft, ...], *, now: datetime) -> tuple[KnowledgeNode, ...]:
        draft_id_map = {
            (draft.node_type, draft.title.lower()): self._node_id(source, draft.node_type, draft.title)
            for draft in drafts
        }
        related_index: dict[str, set[str]] = {node_id: set() for node_id in draft_id_map.values()}

        for draft in drafts:
            current_id = draft_id_map[(draft.node_type, draft.title.lower())]
            for ref in draft.related_refs:
                target = self._resolve_related_ref(ref, draft_id_map)
                if target is None or target == current_id:
                    continue
                related_index[current_id].add(target)
                related_index[target].add(current_id)

        persisted: list[KnowledgeNode] = []
        for draft in drafts:
            node_id = draft_id_map[(draft.node_type, draft.title.lower())]
            current = self.nodes.get(node_id)
            node = KnowledgeNode(
                id=node_id,
                node_type=draft.node_type,
                title=draft.title,
                summary=draft.summary,
                body=draft.body,
                source_ids=(source.id,),
                related_node_ids=tuple(sorted(related_index[node_id])),
                updated_at=now,
                workspace_id=source.workspace_id,
                version=current.version if current is not None else 1,
            )
            persisted_node = self.nodes.upsert_generated(node, recorded_at=now)
            evidence = self._extract_evidence(source, persisted_node, draft)
            self.node_evidence_links.replace_links(persisted_node.id, (evidence.id,))
            persisted.append(persisted_node)
        return tuple(sorted(persisted, key=lambda item: item.id))

    def read_node_with_evidence(self, node_id: str) -> NodeEvidenceView:
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Unknown node: {node_id}")
        evidence_ids = self.node_evidence_links.list_evidence_ids(node_id)
        evidence = self.evidence.list_for_ids(evidence_ids)
        return NodeEvidenceView(node=node, evidence_fragments=evidence)

    def source_jump_target(self, node_id: str) -> SourceJumpTarget:
        view = self.read_node_with_evidence(node_id)
        if not view.evidence_fragments:
            raise KeyError(f"No evidence linked to node: {node_id}")
        evidence = view.evidence_fragments[0]
        source = self._get_source(evidence.source_id)
        return SourceJumpTarget(
            node_id=node_id,
            source_id=source.id,
            raw_blob_ref=source.raw_blob_ref,
            locator=evidence.locator,
            excerpt=evidence.excerpt,
        )

    @staticmethod
    def serialize_node_with_evidence(view: NodeEvidenceView) -> dict[str, object]:
        return {
            "node": serialize_entity(view.node),
            "evidence_fragments": [serialize_entity(fragment) for fragment in view.evidence_fragments],
        }

    def _resolve_related_ref(
        self,
        ref: str,
        draft_id_map: dict[tuple[NodeType, str], str],
    ) -> str | None:
        if ":" in ref:
            raw_type, raw_title = ref.split(":", 1)
            try:
                node_type = NodeType(raw_type.strip().lower())
            except ValueError:
                return None
            return draft_id_map.get((node_type, raw_title.strip().lower()))
        for (node_type, title), node_id in draft_id_map.items():
            if title == ref.strip().lower():
                return node_id
        return None

    def _queue_job(self, source: Source, *, requested_at: datetime) -> CompileJob:
        latest = self.jobs.latest_for_source(source.id)
        attempt_number = 1 if latest is None else latest.attempt_number + 1
        job = CompileJob(
            id=f"job-{uuid4().hex[:12]}",
            source_id=source.id,
            workspace_id=source.workspace_id,
            status=CompileJobStatus.QUEUED,
            requested_at=requested_at,
            attempt_number=attempt_number,
        )
        return self.jobs.create(job)

    def _get_source(self, source_id: str) -> Source:
        source = self.sources.get(source_id)
        if source is None:
            raise KeyError(f"Unknown source: {source_id}")
        return source

    @staticmethod
    def _node_id(source: Source, node_type: NodeType, title: str) -> str:
        return f"node-{source.id}-{node_type.value}-{_slug(title)}"

    def _extract_evidence(self, source: Source, node: KnowledgeNode, draft: NodeDraft) -> EvidenceFragment:
        fragment = EvidenceFragment(
            id=f"evidence-{node.id}",
            source_id=source.id,
            locator=f"line:{draft.line_start}-{draft.line_end}",
            excerpt=draft.summary,
            confidence=0.8,
        )
        return self.evidence.create_or_replace(fragment)
