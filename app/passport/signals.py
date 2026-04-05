"""Capability signal and mistake pattern generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.compile.service import KnowledgeCompileService
from app.domain import CapabilitySignal, FocusCard, FocusStatus, MistakePattern, NodeType, PrivacyLevel, serialize_entity
from app.storage.capability_signals import CapabilitySignalRepository
from app.storage.focus_cards import FocusCardRepository
from app.storage.mistake_patterns import MistakePatternRepository
from app.utils.time import utc_now


@dataclass(frozen=True, slots=True)
class InsightBundle:
    capability_signals: tuple[CapabilitySignal, ...]
    mistake_patterns: tuple[MistakePattern, ...]


class CapabilitySignalService:
    def __init__(
        self,
        *,
        compiler: KnowledgeCompileService,
        capability_signal_repository: CapabilitySignalRepository,
        mistake_pattern_repository: MistakePatternRepository,
    ) -> None:
        self.compiler = compiler
        self.signals = capability_signal_repository
        self.patterns = mistake_pattern_repository

    def generate_for_workspace(self, workspace_id: str) -> InsightBundle:
        nodes = self.compiler.nodes.list_by_workspace(workspace_id)
        signal_results: list[CapabilitySignal] = []
        pattern_results: list[MistakePattern] = []

        for node in nodes:
            evidence_view = self.compiler.read_node_with_evidence(node.id)
            evidence_ids = tuple(fragment.id for fragment in evidence_view.evidence_fragments)
            if node.node_type in {NodeType.TOPIC, NodeType.PROJECT, NodeType.METHOD}:
                signal = CapabilitySignal(
                    id=f"signal-{node.id}",
                    topic=node.title,
                    evidence_ids=evidence_ids,
                    observed_practice=node.summary,
                    current_gaps=self._derive_gaps(node.body),
                    confidence=self._confidence_for_node(node.node_type),
                    workspace_id=workspace_id,
                    visibility=PrivacyLevel.PRIVATE,
                )
                signal_results.append(self.signals.upsert(signal))
            if node.node_type is NodeType.QUESTION:
                pattern = MistakePattern(
                    id=f"pattern-{node.id}",
                    topic=node.title,
                    description=f"Recurring uncertainty around {node.title}.",
                    evidence_ids=evidence_ids,
                    examples=tuple(fragment.excerpt for fragment in evidence_view.evidence_fragments) or (node.summary,),
                    fix_suggestions=(f"Review related guidance for {node.title}.",),
                    recurrence_count=max(1, len(evidence_ids)),
                    workspace_id=workspace_id,
                    visibility=PrivacyLevel.PRIVATE,
                )
                pattern_results.append(self.patterns.upsert(pattern))

        return InsightBundle(
            capability_signals=tuple(sorted(signal_results, key=lambda item: item.topic.lower())),
            mistake_patterns=tuple(sorted(pattern_results, key=lambda item: item.topic.lower())),
        )

    def hide_signal(self, signal_id: str) -> CapabilitySignal:
        return self.signals.set_controls(signal_id, visibility=PrivacyLevel.RESTRICTED)

    def dismiss_pattern(self, pattern_id: str) -> MistakePattern:
        from app.domain import InsightDisposition

        return self.patterns.set_controls(pattern_id, disposition=InsightDisposition.DISMISSED)

    def confirm_pattern(self, pattern_id: str) -> MistakePattern:
        from app.domain import InsightDisposition

        return self.patterns.set_controls(pattern_id, disposition=InsightDisposition.CONFIRMED)

    @staticmethod
    def _derive_gaps(body: str) -> tuple[str, ...]:
        sentences = [segment.strip() for segment in body.replace("\n", " ").split(".") if segment.strip()]
        if len(sentences) > 1:
            return (f"Needs deeper coverage on {sentences[-1].lower()}",)
        return ("Needs deeper examples and applied practice.",)

    @staticmethod
    def _confidence_for_node(node_type: NodeType) -> float:
        return {
            NodeType.PROJECT: 0.82,
            NodeType.METHOD: 0.78,
            NodeType.TOPIC: 0.72,
            NodeType.QUESTION: 0.55,
        }[node_type]


class FocusCardService:
    def __init__(self, repository: FocusCardRepository) -> None:
        self.repository = repository

    def create_focus_card(
        self,
        *,
        workspace_id: str,
        title: str,
        goal: str,
        timeframe: str,
        priority: int,
        success_criteria: tuple[str, ...],
        related_topics: tuple[str, ...] = (),
        status: FocusStatus = FocusStatus.ACTIVE,
    ) -> FocusCard:
        card = FocusCard(
            id=f"focus-{uuid4().hex[:12]}",
            title=title,
            goal=goal,
            timeframe=timeframe,
            priority=priority,
            success_criteria=success_criteria,
            related_topics=related_topics,
            status=status,
            workspace_id=workspace_id,
        )
        if card.status is FocusStatus.ACTIVE:
            self.repository.archive_other_active(workspace_id, keep_id=card.id, now=utc_now())
        return self.repository.create(card)

    def update_focus_card(
        self,
        focus_id: str,
        *,
        title: str | None = None,
        goal: str | None = None,
        timeframe: str | None = None,
        priority: int | None = None,
        success_criteria: tuple[str, ...] | None = None,
        related_topics: tuple[str, ...] | None = None,
        status: FocusStatus | None = None,
    ) -> FocusCard:
        current = self.repository.get(focus_id)
        if current is None:
            raise KeyError(f"Unknown focus card: {focus_id}")
        updated = FocusCard(
            id=current.id,
            title=title if title is not None else current.title,
            goal=goal if goal is not None else current.goal,
            timeframe=timeframe if timeframe is not None else current.timeframe,
            priority=priority if priority is not None else current.priority,
            success_criteria=success_criteria if success_criteria is not None else current.success_criteria,
            related_topics=related_topics if related_topics is not None else current.related_topics,
            status=status if status is not None else current.status,
            workspace_id=current.workspace_id,
        )
        if updated.status is FocusStatus.ACTIVE:
            self.repository.archive_other_active(updated.workspace_id, keep_id=updated.id, now=utc_now())
        return self.repository.update(updated)

    def active_focus(self, workspace_id: str) -> FocusCard | None:
        return self.repository.active_for_workspace(workspace_id)

    def list_focus_cards(self, workspace_id: str) -> tuple[FocusCard, ...]:
        return self.repository.list_by_workspace(workspace_id)

    @staticmethod
    def serialize_focus(card: FocusCard | None) -> dict[str, object] | None:
        return serialize_entity(card) if card is not None else None
