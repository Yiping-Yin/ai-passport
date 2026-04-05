"""Postcard and Passport generation services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.compile.service import KnowledgeCompileService
from app.domain import CardType, Passport, PassportReadiness, Postcard, PrivacyLevel, serialize_entity
from app.passport.signals import CapabilitySignalService, FocusCardService
from app.storage.capability_signals import CapabilitySignalRepository
from app.storage.mistake_patterns import MistakePatternRepository
from app.storage.passports import PassportRepository
from app.storage.postcards import PostcardRepository
from app.storage.workspaces import WorkspaceRepository


@dataclass(frozen=True, slots=True)
class PassportView:
    human_markdown: str
    machine_manifest: dict[str, object]
    passport: Passport


class PostcardService:
    def __init__(
        self,
        *,
        compiler: KnowledgeCompileService,
        capability_signals: CapabilitySignalRepository,
        mistake_patterns: MistakePatternRepository,
        postcard_repository: PostcardRepository,
    ) -> None:
        self.compiler = compiler
        self.capability_signals = capability_signals
        self.mistake_patterns = mistake_patterns
        self.postcards = postcard_repository

    def generate_for_workspace(self, workspace_id: str, *, recorded_at: datetime) -> tuple[Postcard, ...]:
        generated: list[Postcard] = []
        for node in self.compiler.nodes.list_by_workspace(workspace_id):
            if node.node_type.value in {"topic", "project", "method"}:
                view = self.compiler.read_node_with_evidence(node.id)
                postcard = Postcard(
                    id=f"postcard-knowledge-{node.id}",
                    card_type=CardType.KNOWLEDGE,
                    title=node.title,
                    known_things=(node.summary,),
                    done_things=(node.body.splitlines()[0],),
                    common_gaps=("Needs more source coverage.",),
                    active_questions=(),
                    suggested_next_step=f"Add stronger evidence and related methods for {node.title}.",
                    evidence_links=tuple(fragment.id for fragment in view.evidence_fragments),
                    related_nodes=(node.id, *node.related_node_ids),
                    visibility=PrivacyLevel.PRIVATE,
                    version=1,
                    workspace_id=workspace_id,
                )
                generated.append(self.postcards.upsert(postcard, recorded_at=recorded_at))
            if node.node_type.value == "question":
                view = self.compiler.read_node_with_evidence(node.id)
                postcard = Postcard(
                    id=f"postcard-exploration-{node.id}",
                    card_type=CardType.EXPLORATION,
                    title=node.title,
                    known_things=(),
                    done_things=(),
                    common_gaps=(node.summary,),
                    active_questions=(node.title,),
                    suggested_next_step=f"Resolve the open question: {node.title}.",
                    evidence_links=tuple(fragment.id for fragment in view.evidence_fragments),
                    related_nodes=(node.id, *node.related_node_ids),
                    visibility=PrivacyLevel.PRIVATE,
                    version=1,
                    workspace_id=workspace_id,
                )
                generated.append(self.postcards.upsert(postcard, recorded_at=recorded_at))

        for signal in self.capability_signals.list_by_workspace(workspace_id):
            postcard = Postcard(
                id=f"postcard-capability-{signal.id}",
                card_type=CardType.CAPABILITY,
                title=signal.topic,
                known_things=(signal.observed_practice,),
                done_things=(),
                common_gaps=signal.current_gaps,
                active_questions=(),
                suggested_next_step=f"Strengthen practice around {signal.topic}.",
                evidence_links=signal.evidence_ids,
                related_nodes=(),
                visibility=signal.visibility,
                version=1,
                workspace_id=workspace_id,
            )
            generated.append(self.postcards.upsert(postcard, recorded_at=recorded_at))

        for pattern in self.mistake_patterns.list_by_workspace(workspace_id):
            if pattern.disposition.value == "dismissed":
                continue
            postcard = Postcard(
                id=f"postcard-mistake-{pattern.id}",
                card_type=CardType.MISTAKE,
                title=pattern.topic,
                known_things=(),
                done_things=(),
                common_gaps=(pattern.description,),
                active_questions=(),
                suggested_next_step=pattern.fix_suggestions[0] if pattern.fix_suggestions else "Review the related material.",
                evidence_links=pattern.evidence_ids,
                related_nodes=(),
                visibility=pattern.visibility,
                version=1,
                workspace_id=workspace_id,
            )
            if self._quality_check(postcard):
                generated.append(self.postcards.upsert(postcard, recorded_at=recorded_at))

        return tuple(sorted(generated, key=lambda item: (item.card_type.value, item.title.lower())))

    def representative_postcards(self, workspace_id: str) -> tuple[Postcard, ...]:
        visible = [card for card in self.postcards.list_by_workspace(workspace_id) if card.visibility is PrivacyLevel.PRIVATE]
        by_type = {card_type: [] for card_type in CardType}
        for card in visible:
            by_type[card.card_type].append(card)
        selected: list[Postcard] = []
        for card_type in (CardType.KNOWLEDGE, CardType.CAPABILITY, CardType.MISTAKE, CardType.EXPLORATION):
            if by_type[card_type]:
                selected.append(by_type[card_type][0])
        if len(selected) < 3:
            remaining = [card for card in visible if card not in selected]
            selected.extend(remaining[: 3 - len(selected)])
        if len(selected) < 5:
            remaining = [card for card in visible if card not in selected]
            selected.extend(remaining[: 5 - len(selected)])
        return tuple(selected[:5])

    def set_visibility(self, postcard_id: str, visibility: PrivacyLevel) -> Postcard:
        return self.postcards.set_visibility(postcard_id, visibility)

    @staticmethod
    def _quality_check(postcard: Postcard, *, allow_empty_evidence: bool = False) -> bool:
        has_sections = bool(postcard.title and postcard.suggested_next_step)
        has_evidence = bool(postcard.evidence_links) or allow_empty_evidence
        return has_sections and has_evidence


class PassportService:
    def __init__(
        self,
        *,
        workspace_repository: WorkspaceRepository,
        compiler: KnowledgeCompileService,
        capability_signal_service: CapabilitySignalService,
        capability_signal_repository: CapabilitySignalRepository,
        mistake_pattern_repository: MistakePatternRepository,
        focus_service: FocusCardService,
        postcard_service: PostcardService,
        postcard_repository: PostcardRepository,
        passport_repository: PassportRepository,
    ) -> None:
        self.workspaces = workspace_repository
        self.compiler = compiler
        self.signal_service = capability_signal_service
        self.signals = capability_signal_repository
        self.mistake_patterns = mistake_pattern_repository
        self.focus = focus_service
        self.postcard_service = postcard_service
        self.postcards = postcard_repository
        self.passports = passport_repository

    def generate_for_workspace(self, workspace_id: str, *, recorded_at: datetime) -> PassportView:
        self.signal_service.generate_for_workspace(workspace_id)
        self.postcard_service.generate_for_workspace(workspace_id, recorded_at=recorded_at)
        representative = self.postcard_service.representative_postcards(workspace_id)
        signals = [
            signal
            for signal in self.signals.list_by_workspace(workspace_id)
            if signal.disposition.value != "dismissed" and signal.visibility is PrivacyLevel.PRIVATE
        ]
        active_focus = self.focus.active_focus(workspace_id)
        nodes = self.compiler.nodes.list_by_workspace(workspace_id)
        workspace = self.workspaces.get(workspace_id)
        if workspace is None:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        owner_summary = self._owner_summary(workspace.title, nodes, signals)
        machine_manifest = {
            "version": 1,
            "workspace_id": workspace_id,
            "owner_summary": owner_summary,
            "theme_map": tuple(node.title for node in nodes[:5]),
            "capability_signals": [serialize_entity(signal) for signal in signals],
            "active_focus": self.focus.serialize_focus(active_focus),
            "representative_postcards": [serialize_entity(card) for card in representative],
        }
        passport = Passport(
            id=f"passport-{workspace_id}",
            owner_summary=owner_summary,
            theme_map=tuple(node.title for node in nodes[:5]),
            capability_signal_ids=tuple(signal.id for signal in signals),
            focus_card_ids=(active_focus.id,) if active_focus else (),
            representative_postcard_ids=tuple(card.id for card in representative),
            machine_manifest=machine_manifest,
            version=1,
            workspace_id=workspace_id,
        )
        stored = self.passports.upsert(passport)
        self._update_readiness(workspace_id, representative_count=len(representative), signal_count=len(signals), node_count=len(nodes))
        return PassportView(
            human_markdown=self._human_view(stored, representative),
            machine_manifest=machine_manifest,
            passport=stored,
        )

    def read_machine_manifest(self, passport_id: str) -> dict[str, object]:
        passport = self.passports.get(passport_id)
        if passport is None:
            raise KeyError(f"Unknown passport: {passport_id}")
        return passport.machine_manifest

    def read_human_view(self, passport_id: str) -> str:
        passport = self.passports.get(passport_id)
        if passport is None:
            raise KeyError(f"Unknown passport: {passport_id}")
        representative = tuple(
            card
            for card in self.postcards.list_by_workspace(passport.workspace_id)
            if card.id in passport.representative_postcard_ids
        )
        return self._human_view(passport, representative)

    def rewrite_owner_summary(self, passport_id: str, owner_summary: str) -> Passport:
        return self.passports.set_owner_summary(passport_id, owner_summary)

    def compute_readiness(self, workspace_id: str) -> PassportReadiness:
        workspace = self.workspaces.get(workspace_id)
        if workspace is None:
            raise KeyError(f"Unknown workspace: {workspace_id}")
        sources_exist = bool(self.compiler.sources.list_by_workspace(workspace_id))
        nodes_exist = bool(self.compiler.nodes.list_by_workspace(workspace_id))
        postcards = self.postcard_service.representative_postcards(workspace_id)
        if not sources_exist:
            return PassportReadiness.NOT_STARTED
        if nodes_exist and len(postcards) >= 3:
            return PassportReadiness.READY
        return PassportReadiness.IN_PROGRESS

    def _update_readiness(self, workspace_id: str, *, representative_count: int, signal_count: int, node_count: int) -> None:
        workspace = self.workspaces.get(workspace_id)
        if workspace is None:
            return
        if node_count == 0:
            readiness = PassportReadiness.NOT_STARTED
        elif representative_count >= 3 and signal_count >= 1:
            readiness = PassportReadiness.READY
        else:
            readiness = PassportReadiness.IN_PROGRESS
        if workspace.passport_readiness is readiness:
            return
        updated = type(workspace)(
            id=workspace.id,
            workspace_type=workspace.workspace_type,
            title=workspace.title,
            created_at=workspace.created_at,
            updated_at=datetime.utcnow(),
            description=workspace.description,
            tags=workspace.tags,
            privacy_default=workspace.privacy_default,
            passport_readiness=readiness,
            archived_at=workspace.archived_at,
        )
        self.workspaces.update(updated)

    @staticmethod
    def _owner_summary(workspace_title: str, nodes: list[object], signals: list[object]) -> str:
        return f"{workspace_title} has {len(nodes)} compiled knowledge nodes and {len(signals)} evidence-backed capability signals."

    @staticmethod
    def _human_view(passport: Passport, representative: tuple[Postcard, ...]) -> str:
        lines = [
            f"# Passport for {passport.workspace_id}",
            "",
            passport.owner_summary,
            "",
            "## Themes",
        ]
        lines.extend(f"- {theme}" for theme in passport.theme_map)
        lines.extend(["", "## Representative Postcards"])
        for postcard in representative:
            lines.append(f"### {postcard.card_type.value.title()}: {postcard.title}")
            lines.append(f"- Next step: {postcard.suggested_next_step}")
            if postcard.common_gaps:
                lines.append(f"- Common gaps: {', '.join(postcard.common_gaps)}")
        return "\n".join(lines).strip()
