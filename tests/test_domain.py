from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from app.domain import (
    AccessMode,
    AuditLog,
    CapabilitySignal,
    CandidateStatus,
    CandidateType,
    CardType,
    DomainValidationError,
    EvidenceFragment,
    FocusCard,
    FocusStatus,
    KnowledgeNode,
    MistakePattern,
    MountSession,
    NodeType,
    Passport,
    PassportReadiness,
    PermissionLevel,
    Postcard,
    PrivacyLevel,
    ReviewCandidate,
    SessionStatus,
    Source,
    SourceType,
    VisaBundle,
    VisaStatus,
    Workspace,
    WorkspaceType,
    WritebackPolicy,
    deserialize_entity,
    serialize_entity,
)


NOW = datetime(2026, 4, 6, 10, 0, 0)


class DomainModelTests(unittest.TestCase):
    def test_core_entities_instantiate(self) -> None:
        workspace = Workspace(
            id="ws-1",
            workspace_type=WorkspaceType.PERSONAL,
            title="Personal",
            created_at=NOW,
            updated_at=NOW,
            passport_readiness=PassportReadiness.IN_PROGRESS,
        )
        source = Source(
            id="src-1",
            source_type=SourceType.MARKDOWN,
            title="Notes",
            origin="notes.md",
            imported_at=NOW,
            workspace_id=workspace.id,
            privacy_level=PrivacyLevel.PRIVATE,
            raw_blob_ref="data/workspaces/personal/raw/notes.md",
        )
        node = KnowledgeNode(
            id="node-1",
            node_type=NodeType.TOPIC,
            title="Python typing",
            summary="Typing basics",
            body="Body",
            source_ids=(source.id,),
            related_node_ids=(),
            updated_at=NOW,
            workspace_id=workspace.id,
        )
        evidence = EvidenceFragment(
            id="ev-1",
            source_id=source.id,
            locator="line:1-2",
            excerpt="Typed excerpt",
            confidence=0.8,
        )
        signal = CapabilitySignal(
            id="sig-1",
            topic="Python typing",
            evidence_ids=(evidence.id,),
            observed_practice="Uses dataclasses and enums",
            current_gaps=("Needs persistence layer",),
            confidence=0.7,
            workspace_id=workspace.id,
        )
        pattern = MistakePattern(
            id="mistake-1",
            topic="GitHub Projects",
            description="Retries omitted for long-running syncs",
            examples=("Transient API failures",),
            fix_suggestions=("Add retries",),
            recurrence_count=1,
            workspace_id=workspace.id,
        )
        focus = FocusCard(
            id="focus-1",
            title="Ship Milestone 1.2",
            goal="Define domain contracts",
            timeframe="2026-04-06 to 2026-04-10",
            priority=1,
            success_criteria=("Entities compile", "Tests pass"),
            related_topics=("domain", "storage"),
            status=FocusStatus.ACTIVE,
            workspace_id=workspace.id,
        )
        postcard = Postcard(
            id="card-1",
            card_type=CardType.KNOWLEDGE,
            title="Typing postcard",
            known_things=("Dataclasses",),
            done_things=("Bootstrapped repo",),
            common_gaps=("Storage schema",),
            active_questions=("How should migrations be versioned?",),
            suggested_next_step="Implement domain models",
            evidence_links=(evidence.id,),
            related_nodes=(node.id,),
            visibility=PrivacyLevel.PRIVATE,
            version=1,
            workspace_id=workspace.id,
        )
        passport = Passport(
            id="passport-1",
            owner_summary="Local-first learner",
            theme_map=("python", "knowledge systems"),
            capability_signal_ids=(signal.id,),
            focus_card_ids=(focus.id,),
            representative_postcard_ids=(postcard.id,),
            machine_manifest={"postcards": [postcard.id]},
            version=1,
            workspace_id=workspace.id,
        )
        visa = VisaBundle(
            id="visa-1",
            scope=("passport", "topic:python"),
            included_postcards=(postcard.id,),
            included_nodes=(node.id,),
            permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.TOPIC_READ),
            expiry_at=NOW + timedelta(days=1),
            access_mode=AccessMode.READ_ONLY,
            writeback_policy=WritebackPolicy.REVIEW_REQUIRED,
            redaction_rules=("hide_private_examples",),
            status=VisaStatus.ACTIVE,
            version=1,
            workspace_id=workspace.id,
        )
        session = MountSession(
            id="session-1",
            client_type="gpt",
            visa_id=visa.id,
            started_at=NOW,
            ended_at=NOW + timedelta(hours=1),
            actions=("passport_read", "postcard_read"),
            writeback_count=0,
            status=SessionStatus.ENDED,
        )
        candidate = ReviewCandidate(
            id="candidate-1",
            session_id=session.id,
            candidate_type=CandidateType.SUMMARY,
            content_ref="content://candidate-1",
            target_object=node.id,
            diff_ref="diff://candidate-1",
            status=CandidateStatus.PENDING,
            version=1,
            evidence_ids=(evidence.id,),
        )
        audit = AuditLog(
            id="audit-1",
            actor="user",
            action="accept_candidate",
            object_id=candidate.id,
            timestamp=NOW,
            result="success",
            meta={"session_id": session.id},
        )

        self.assertEqual(passport.representative_postcard_ids, (postcard.id,))
        self.assertEqual(audit.meta["session_id"], session.id)
        self.assertEqual(pattern.recurrence_count, 1)

    def test_visa_writeback_requires_review_required_and_explicit_permission(self) -> None:
        with self.assertRaises(DomainValidationError):
            VisaBundle(
                id="visa-2",
                scope=("passport",),
                included_postcards=(),
                included_nodes=(),
                permission_levels=(PermissionLevel.PASSPORT_READ, PermissionLevel.WRITEBACK_CANDIDATE),
                expiry_at=None,
                access_mode=AccessMode.READ_ONLY,
                writeback_policy=WritebackPolicy.REVIEW_REQUIRED,
                redaction_rules=(),
                status=VisaStatus.ACTIVE,
                version=1,
                workspace_id="ws-1",
            )

    def test_wildcard_access_is_rejected(self) -> None:
        with self.assertRaises(DomainValidationError):
            VisaBundle(
                id="visa-3",
                scope=("*",),
                included_postcards=(),
                included_nodes=(),
                permission_levels=(PermissionLevel.PASSPORT_READ,),
                expiry_at=None,
                access_mode=AccessMode.READ_ONLY,
                writeback_policy=WritebackPolicy.REVIEW_REQUIRED,
                redaction_rules=(),
                status=VisaStatus.ACTIVE,
                version=1,
                workspace_id="ws-1",
            )

    def test_versioned_entities_reject_zero_version(self) -> None:
        with self.assertRaises(DomainValidationError):
            Postcard(
                id="card-2",
                card_type=CardType.KNOWLEDGE,
                title="Bad postcard",
                known_things=("x",),
                done_things=("y",),
                common_gaps=("z",),
                active_questions=("q",),
                suggested_next_step="fix",
                evidence_links=("ev-1",),
                related_nodes=("node-1",),
                visibility=PrivacyLevel.PRIVATE,
                version=0,
                workspace_id="ws-1",
            )

    def test_serialization_round_trip_for_postcard(self) -> None:
        postcard = Postcard(
            id="card-3",
            card_type=CardType.CAPABILITY,
            title="Capability postcard",
            known_things=("Enums",),
            done_things=("Project setup",),
            common_gaps=("Persistence",),
            active_questions=("What is the first migration?",),
            suggested_next_step="Add schema migration",
            evidence_links=("ev-1",),
            related_nodes=("node-1",),
            visibility=PrivacyLevel.RESTRICTED,
            version=2,
            workspace_id="ws-1",
        )
        payload = serialize_entity(postcard)
        restored = deserialize_entity(Postcard, payload)
        self.assertEqual(restored, postcard)


if __name__ == "__main__":
    unittest.main()
