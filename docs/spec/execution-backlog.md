# AI Knowledge Passport: Epics → Milestones → Tickets (Execution Backlog for Codex)

Status: Draft for Codex execution  
Last Updated: 2026-04-05

---

## 1. How to Use This Backlog

This document turns the PRD into an execution structure that Codex can work through step by step.

Working rules:
1. Work one milestone at a time.
2. Do not build adjacent features outside the active milestone.
3. Every milestone ends with passing typecheck/tests and an updated documentation note.
4. No external-AI writeback may bypass review.
5. No milestone may weaken evidence traceability or permission boundaries.
6. Prefer simple, testable implementations over broad but vague scaffolding.

## 2. Global Program Phases

### Phase 0 — Repo Recon and Architecture Baseline
Understand the real repository, stack, commands, constraints, and module boundaries before changing behavior.

### Phase 1 — Domain and Persistence Skeleton
Define entities, invariants, migrations, and storage contracts.

### Phase 2 — Source Intake and Compilation Core
Implement source import, compile jobs, knowledge nodes, and evidence extraction.

### Phase 3 — Knowledge Surfaces
Implement Focus, Postcards, and Passport generation.

### Phase 4 — Mounting and Access Control
Implement Passport-first mount flow, Visa Bundles, session tracking, and read boundaries.

### Phase 5 — Review and Governance
Implement review queue, diff/merge controls, audit logging, export, restore, and revocation.

### Phase 6 — Pilot Readiness
Implement the thin operator UI, benchmarks, release gating, and instrumentation needed for a real pilot.

---

## 3. Epic Breakdown

# Epic 1. Foundations and Domain Contracts

**Goal**  
Create a stable product vocabulary, repository baseline, domain model, and persistence layer so the rest of the system can be built without naming drift or architectural confusion.

**Related PRD**  
US-01 to US-04, US-11 to US-13, FR-01 to FR-07, FR-34 to FR-37

### Milestone 1.1 — Repository reconnaissance and architecture baseline
**Outcome**  
The team understands the real repo and freezes the initial execution plan.

**Tickets**

- **E1-M1-T01 — Inventory repository structure and commands**  
  Document the package manager, runtime, app/package layout, migration command, lint command, typecheck command, and test command.  
  **Acceptance:** `Documentation.md` contains verified commands that run in the real repo.

- **E1-M1-T02 — Freeze module boundaries**  
  Define the intended package/module boundaries for domain, compiler, passport, gateway, review, and UI layers.  
  **Acceptance:** one architecture section or ADR exists and names each module’s responsibility.

- **E1-M1-T03 — Establish branch and migration policy**  
  Define naming conventions for feature branches, migration files, and seed data.  
  **Acceptance:** branch/migration policy is written and referenced from the main planning docs.

- **E1-M1-T04 — Set up baseline CI tasks**  
  Ensure lint, typecheck, and test commands can run locally and in CI, even if some suites are placeholders at first.  
  **Acceptance:** CI or equivalent local script exists and fails on broken checks.

### Milestone 1.2 — Core domain entities and invariants
**Outcome**  
The canonical entity set and invariants are defined in code.

**Tickets**

- **E1-M2-T01 — Define entity schemas/types**  
  Create typed models for Workspace, Source, KnowledgeNode, EvidenceFragment, CapabilitySignal, MistakePattern, FocusCard, Postcard, Passport, VisaBundle, MountSession, ReviewCandidate, and AuditLog.  
  **Acceptance:** all core entities compile and expose required fields from the PRD.

- **E1-M2-T02 — Encode invariant rules**  
  Express key invariants such as read-only-first, no auto-merge writeback, versioned snapshots, and whitelist-only access.  
  **Acceptance:** invariants are represented in domain code and covered by tests.

- **E1-M2-T03 — Freeze enums and status vocabularies**  
  Define stable enums for workspace types, node types, card types, candidate status, session status, and Visa status.  
  **Acceptance:** enums are centralized and reused consistently.

- **E1-M2-T04 — Add domain-level serialization contracts**  
  Define how domain objects are serialized for storage and API response use.  
  **Acceptance:** a documented mapping exists between internal objects and transport shape.

### Milestone 1.3 — Persistence schema, migrations, and seed workspace
**Outcome**  
The data model exists in storage with initial seed data.

**Tickets**

- **E1-M3-T01 — Create initial database migration**  
  Add the first migration covering all MVP tables and indexes.  
  **Acceptance:** migration can be applied to an empty database and rolled back safely.

- **E1-M3-T02 — Seed one sample workspace**  
  Add sample data including one workspace, a few sources, nodes, evidence fragments, and one draft passport.  
  **Acceptance:** seed command produces a usable local dev state.

- **E1-M3-T03 — Add repository tests for relations**  
  Verify entity relationships such as source → evidence → node and passport → visa → session.  
  **Acceptance:** tests cover critical foreign-key or logical-link integrity.

- **E1-M3-T04 — Document the schema**  
  Add a schema overview to the docs so Codex and human reviewers share the same model.  
  **Acceptance:** docs include an entity relationship summary.

---

# Epic 2. Workspace, Inbox, and Source Intake

**Goal**  
Allow users to create workspaces, import raw materials, preserve source truth, and manage intake through an Inbox.

**Related PRD**  
US-01, US-02, FR-01 to FR-07

### Milestone 2.1 — Workspace lifecycle and onboarding
**Outcome**  
Users can create isolated workspaces and begin cold start.

**Tickets**

- **E2-M1-T01 — Create workspace service and API**  
  Implement create/list/read/update/archive operations for personal, work, and project workspaces.  
  **Acceptance:** workspace CRUD works and enforces type validation.

- **E2-M1-T02 — Build workspace switcher state**  
  Add UI/application state for selecting the active workspace without leaking data across workspaces.  
  **Acceptance:** switching workspace updates all visible data scopes correctly.

- **E2-M1-T03 — Add cold-start readiness placeholders**  
  Show a first-run onboarding state and a placeholder readiness indicator before Passport generation exists.  
  **Acceptance:** the dashboard can distinguish “not started,” “in progress,” and “ready for draft.”

### Milestone 2.2 — Source intake and raw preservation
**Outcome**  
Raw inputs are ingested, stored, and never overwritten.

**Tickets**

- **E2-M2-T01 — Implement source import pipeline**  
  Create import handlers for web page text, Markdown, PDF text extraction results, plain text, and project documents.  
  **Acceptance:** supported input types can be stored as Source objects.

- **E2-M2-T02 — Persist raw content and metadata**  
  Store raw content reference, origin, import timestamp, workspace id, and privacy level.  
  **Acceptance:** no imported source can exist without complete provenance metadata.

- **E2-M2-T03 — Add privacy-level defaults and validation**  
  Define allowed privacy levels and default assignment on import.  
  **Acceptance:** invalid privacy settings are rejected.

- **E2-M2-T04 — Prevent raw overwrite on recompilation**  
  Ensure compile runs never mutate the canonical raw source record.  
  **Acceptance:** recompilation changes derived objects only.

### Milestone 2.3 — Inbox operations and compile trigger
**Outcome**  
Imported items appear in Inbox and can be compiled or retried.

**Tickets**

- **E2-M3-T01 — Build Inbox list and status model**  
  Show source title, type, workspace, import time, compile status, and last error.  
  **Acceptance:** Inbox reflects the actual source/compile state.

- **E2-M3-T02 — Create compile job records**  
  Add job records with queued/running/succeeded/failed states.  
  **Acceptance:** compile jobs can be created, updated, retried, and inspected.

- **E2-M3-T03 — Add source preview and evidence preview panel**  
  Allow users to inspect the raw source and preview extracted evidence where available.  
  **Acceptance:** Inbox supports side-by-side source and compile preview.

- **E2-M3-T04 — Add recompile action**  
  Allow failed or stale imports to be recompiled manually.  
  **Acceptance:** a user can re-run compilation without duplicating the source.

---

# Epic 3. Compilation Core and Evidence Traceability

**Goal**  
Compile raw sources into reusable structured knowledge while preserving traceability.

**Related PRD**  
US-03, US-04, FR-08 to FR-11

### Milestone 3.1 — Knowledge node generation
**Outcome**  
The system can create foundational topic/project/method/question nodes.

**Tickets**

- **E3-M1-T01 — Implement node generation pipeline**  
  Create compiler logic that emits topic, project, method, and question nodes from imported content.  
  **Acceptance:** at least one fixture source can compile into all supported node classes.

- **E3-M1-T02 — Add reverse link support**  
  Support bidirectional or discoverable reverse relationships between nodes.  
  **Acceptance:** related nodes are visible from either linked side.

- **E3-M1-T03 — Version compiled node revisions**  
  Preserve meaningful node revisions instead of replacing every output blindly.  
  **Acceptance:** updates produce traceable revisions or version history.

### Milestone 3.2 — Evidence fragment extraction and linkage
**Outcome**  
Every high-level object can point back to source evidence.

**Tickets**

- **E3-M2-T01 — Implement evidence fragment extraction**  
  Extract citeable fragments with locator information from sources.  
  **Acceptance:** fragments contain source reference, locator, excerpt, and confidence.

- **E3-M2-T02 — Link nodes to evidence**  
  Associate nodes with one or more evidence fragments.  
  **Acceptance:** every generated node shows evidence links when viewed or serialized.

- **E3-M2-T03 — Build source-jump contract**  
  Add a reusable contract for “jump to source location” from higher-level objects.  
  **Acceptance:** UI/API can resolve a postcard or node to concrete source provenance.

### Milestone 3.3 — Human reviewability of compile output
**Outcome**  
Users can inspect and correct derived knowledge.

**Tickets**

- **E3-M3-T01 — Add manual edit support for key node fields**  
  Allow a user to edit title, summary, body, or relation data on generated nodes.  
  **Acceptance:** edited fields persist and remain marked as user-modified.

- **E3-M3-T02 — Distinguish generated vs user-edited content**  
  Preserve provenance of generated text versus human edits.  
  **Acceptance:** the system can tell whether a field is machine-generated, human-edited, or mixed.

- **E3-M3-T03 — Add compile diff visibility**  
  Show what changed between previous and current compile outputs for a node.  
  **Acceptance:** users can inspect meaningful before/after changes.

---

# Epic 4. Capability Signals, Mistake Patterns, and Focus Layer

**Goal**  
Represent demonstrated practice, recurring gaps, and the user’s active objective without collapsing them into oversimplified scores.

**Related PRD**  
US-05, US-06, US-07, FR-12 to FR-16

### Milestone 4.1 — Capability signal generation
**Outcome**  
The system emits evidence-backed capability signals.

**Tickets**

- **E4-M1-T01 — Define capability signal schema and rendering contract**  
  Represent topic, observed practice, current gaps, confidence, and evidence links.  
  **Acceptance:** signals serialize cleanly and are displayable in Knowledge and Passport views.

- **E4-M1-T02 — Generate initial capability signals from compiled nodes**  
  Derive signals from projects, methods, and topic evidence.  
  **Acceptance:** sample workspaces produce at least a small set of useful signals.

- **E4-M1-T03 — Explicitly prohibit numeric capability scores**  
  Prevent any single ranking score from appearing as the canonical interpretation.  
  **Acceptance:** API, UI, and domain model expose signals only, not scores.

### Milestone 4.2 — Mistake pattern generation and controls
**Outcome**  
The system can detect and manage recurring mistake patterns.

**Tickets**

- **E4-M2-T01 — Define mistake pattern schema**  
  Include topic, description, examples, recurrence count, and fix suggestions.  
  **Acceptance:** patterns can be stored, versioned, and displayed.

- **E4-M2-T02 — Generate mistake patterns from repeated evidence**  
  Produce patterns from repeated errors, repeated questions, or repeated corrections.  
  **Acceptance:** at least one benchmark fixture can produce a stable mistake pattern.

- **E4-M2-T03 — Add user confirm/hide/dismiss actions**  
  Let users control visibility and trust for each mistake pattern.  
  **Acceptance:** dismissed or hidden patterns are respected in Passport output.

### Milestone 4.3 — Focus Card lifecycle
**Outcome**  
The system can represent what the user is currently trying to solve.

**Tickets**

- **E4-M3-T01 — Implement Focus Card domain and CRUD**  
  Support creation, editing, switching, archiving, and status transitions.  
  **Acceptance:** exactly one active focus can be designated per workspace in MVP.

- **E4-M3-T02 — Add success criteria and timeframe fields**  
  Require structured goal, timeframe, priority, and success criteria fields.  
  **Acceptance:** invalid or incomplete Focus Cards are rejected by validation.

- **E4-M3-T03 — Prioritize active Focus in Passport reads**  
  Ensure the active Focus Card appears in Passport-first access.  
  **Acceptance:** the machine manifest includes active focus in the default payload.

---

# Epic 5. Postcards and Passport

**Goal**  
Compress the compiled knowledge base into concise, explainable objects that external AI can read quickly.

**Related PRD**  
US-08, US-09, FR-17 to FR-22

### Milestone 5.1 — Postcard generation
**Outcome**  
The system can generate versioned topic-level Postcards.

**Tickets**

- **E5-M1-T01 — Define postcard schema**  
  Include known things, done things, common gaps, active questions, next step, evidence links, visibility, and version.  
  **Acceptance:** all postcards conform to one stable schema.

- **E5-M1-T02 — Generate four postcard classes**  
  Support knowledge, capability, mistake, and exploration postcards.  
  **Acceptance:** postcard class is explicit and visible in storage and UI.

- **E5-M1-T03 — Generate 3–5 representative postcards for cold start**  
  Prioritize cold-start quality over broad graph coverage.  
  **Acceptance:** a new workspace can produce 3–5 strong initial postcards from minimal imports.

### Milestone 5.2 — Postcard updates and version review
**Outcome**  
Postcards evolve safely as the knowledge base changes.

**Tickets**

- **E5-M2-T01 — Regenerate postcard candidates on source changes**  
  Generate a new candidate version when relevant nodes or evidence change.  
  **Acceptance:** postcard history is preserved rather than overwritten.

- **E5-M2-T02 — Add postcard visibility controls**  
  Allow users to hide sensitive postcards or restrict exposure.  
  **Acceptance:** hidden postcards never appear in default Passport output.

- **E5-M2-T03 — Add postcard quality checks**  
  Reject postcard candidates that lack evidence links or required sections.  
  **Acceptance:** invalid postcard candidates cannot be promoted.

### Milestone 5.3 — Passport manifest generation
**Outcome**  
The system can generate a compact human-readable and machine-readable Passport.

**Tickets**

- **E5-M3-T01 — Define Passport manifest schema**  
  Include owner summary, theme map, capability signals, active focus, representative postcards, and version.  
  **Acceptance:** Passport manifests validate against a stable schema.

- **E5-M3-T02 — Generate human-readable and machine-readable variants**  
  Produce a human view and a machine manifest from the same underlying snapshot.  
  **Acceptance:** both views stay semantically aligned.

- **E5-M3-T03 — Add owner summary rewrite and redaction controls**  
  Allow the user to edit summary language and hide sensitive content.  
  **Acceptance:** hidden or rewritten content affects the generated Passport output immediately.

- **E5-M3-T04 — Compute Passport Readiness**  
  Define and surface a readiness heuristic for whether the workspace is ready to mount.  
  **Acceptance:** readiness changes predictably as required ingredients appear or disappear.

---

# Epic 6. Mounting, Visa Bundles, and Session Control

**Goal**  
Allow external AI to consume the Passport safely, request deeper scope deliberately, and leave an auditable trail.

**Related PRD**  
US-10, US-11, FR-23 to FR-28

### Milestone 6.1 — Passport-first mount flow
**Outcome**  
External AI can begin with Passport, representative Postcards, and active Focus only.

**Tickets**

- **E6-M1-T01 — Implement `GET /passport/{id}/manifest`**  
  Return the machine-readable Passport manifest.  
  **Acceptance:** response contains only allowed default objects.

- **E6-M1-T02 — Implement postcard read endpoint**  
  Expose read access for whitelisted postcards.  
  **Acceptance:** unauthorized postcard reads are rejected consistently.

- **E6-M1-T03 — Enforce read-only default access**  
  Ensure the initial mount flow cannot mutate workspace state.  
  **Acceptance:** no write path is available without explicit writeback-candidate permission.

### Milestone 6.2 — Visa Bundles and topic-level access
**Outcome**  
Deeper reads are permissioned through explicit scope packages.

**Tickets**

- **E6-M2-T01 — Implement Visa Bundle model and issuance flow**  
  Support scope, included objects, expiry, access mode, and writeback policy.  
  **Acceptance:** Visas can be created with explicit object inclusion and expiry.

- **E6-M2-T02 — Enforce three MVP permissions**  
  Implement `passport_read`, `topic_read`, and `writeback_candidate`.  
  **Acceptance:** permission checks are centralized and tested.

- **E6-M2-T03 — Block whole-workspace search**  
  Prevent any default “search everything” path for external AI.  
  **Acceptance:** all deeper reads require explicit object inclusion.

- **E6-M2-T04 — Add revocation and expiry processing**  
  Support manual revoke and automatic expiry.  
  **Acceptance:** revoked or expired Visas immediately fail authorization checks.

### Milestone 6.3 — Mount sessions and access logs
**Outcome**  
Every external AI interaction is captured and traceable.

**Tickets**

- **E6-M3-T01 — Implement mount session start/end records**  
  Record client type, visa, timestamps, and status.  
  **Acceptance:** every authorized mount creates a session record.

- **E6-M3-T02 — Record access actions within session**  
  Track which objects were read and which writeback candidates were submitted.  
  **Acceptance:** session logs can be queried for object-level access history.

- **E6-M3-T03 — Build Mount screen with session list and status**  
  Provide an operator view for Visa Bundles, sessions, and revoke actions.  
  **Acceptance:** a user can inspect active and historical sessions in one screen.

---

# Epic 7. Review Queue, Audit, Export, and Recovery

**Goal**  
Create the trust layer that prevents silent knowledge pollution and preserves user control.

**Related PRD**  
US-12, US-13, FR-29 to FR-37

### Milestone 7.1 — Review Queue ingestion and candidate model
**Outcome**  
External AI outputs become reviewable candidates instead of canonical writes.

**Tickets**

- **E7-M1-T01 — Implement `POST /writeback-candidates`**  
  Create review candidates linked to the originating mount session.  
  **Acceptance:** no candidate can exist without a valid source session.

- **E7-M1-T02 — Define candidate types and target contracts**  
  Support summary, outline, memo, teaching note, question set, and similar candidate classes.  
  **Acceptance:** candidate types are validated and mapped to permissible targets.

- **E7-M1-T03 — Enforce no auto-merge rule**  
  Prevent any candidate from writing into canonical knowledge automatically.  
  **Acceptance:** there is no code path from candidate creation to silent merge.

### Milestone 7.2 — Review actions and diff visibility
**Outcome**  
Users can review, edit, and decide whether a candidate becomes part of the knowledge base.

**Tickets**

- **E7-M2-T01 — Build candidate diff model**  
  Represent before/after deltas against a target node, postcard, or focus card.  
  **Acceptance:** each candidate exposes a renderable diff structure.

- **E7-M2-T02 — Implement accept / edit then accept / reject actions**  
  Add explicit review actions with resulting state transitions.  
  **Acceptance:** all actions are auditable and update candidate status correctly.

- **E7-M2-T03 — Build Review screen**  
  Show candidate content, target object, source session, diff, and actions in one workflow.  
  **Acceptance:** a user can complete the full review flow without leaving the screen.

### Milestone 7.3 — Audit, export, backup, and restore
**Outcome**  
Users can inspect history and retain data sovereignty.

**Tickets**

- **E7-M3-T01 — Add audit event pipeline**  
  Record mount, read, revoke, review, export, and restore events.  
  **Acceptance:** audit log entries are append-only and queryable.

- **E7-M3-T02 — Implement export package**  
  Export core structures, cards, Passport, candidates, and logs.  
  **Acceptance:** a single export contains enough data to restore an MVP workspace.

- **E7-M3-T03 — Implement restore flow**  
  Rebuild a workspace from a prior export or backup package.  
  **Acceptance:** restore reproduces a valid workspace with preserved relationships.

- **E7-M3-T04 — Add privacy-level enforcement across export paths**  
  Ensure privacy and visibility rules are respected during export and restore.  
  **Acceptance:** excluded or hidden objects remain excluded when required.

---

# Epic 8. Thin UI, Quality Gates, and Pilot Readiness

**Goal**  
Deliver the minimum interface and validation tooling needed to run a real pilot and learn whether the product promise is true.

**Related PRD**  
All screen sections, NFRs, success metrics, release gates

### Milestone 8.1 — Thin operator UI
**Outcome**  
Users can complete the end-to-end flow through a minimal but coherent interface.

**Tickets**

- **E8-M1-T01 — Build Dashboard screen**  
  Show active Focus, Passport Readiness, recent imports, pending review, and recent mount sessions.  
  **Acceptance:** Dashboard reflects live data for the selected workspace.

- **E8-M1-T02 — Build Knowledge screen**  
  Show nodes, evidence, signals, mistake patterns, linked focus, and postcards in one place.  
  **Acceptance:** users can inspect compiled knowledge without navigating a graph explorer.

- **E8-M1-T03 — Build Passport screen**  
  Show human view, machine view, regenerate, hide, edit, and create Visa actions.  
  **Acceptance:** Passport can be previewed and managed in one screen.

- **E8-M1-T04 — Build Settings screen**  
  Show workspace config, export, backup, privacy, and default policies.  
  **Acceptance:** operational controls are accessible without developer intervention.

### Milestone 8.2 — Benchmarks, traceability tests, and guardrails
**Outcome**  
The team can verify compile quality and trust boundaries repeatedly.

**Tickets**

- **E8-M2-T01 — Create benchmark fixtures for compiler quality**  
  Add fixed sample inputs and expected properties for nodes, evidence, postcards, and passport outputs.  
  **Acceptance:** benchmark fixtures run deterministically in CI or local eval mode.

- **E8-M2-T02 — Add evidence-trace coverage tests**  
  Ensure all high-level objects can resolve to source evidence.  
  **Acceptance:** tests fail if postcards or Passport outputs lose evidence traceability.

- **E8-M2-T03 — Add permission boundary tests**  
  Verify that unauthorized reads, revoked visas, expired visas, and whole-workspace search attempts fail.  
  **Acceptance:** access-control tests cover all three MVP permissions and core denial paths.

- **E8-M2-T04 — Add writeback pollution tests**  
  Verify that no external output bypasses Review Queue.  
  **Acceptance:** tests fail if a direct canonical merge path appears.

### Milestone 8.3 — Release gates and pilot instrumentation
**Outcome**  
The product is ready for real-user validation.

**Tickets**

- **E8-M3-T01 — Instrument north-star and leading metrics**  
  Track Passport Readiness, review acceptance, session usage, and first-response fit signals.  
  **Acceptance:** pilot telemetry or logging can measure the PRD metrics.

- **E8-M3-T02 — Add release gate checklist**  
  Encode the MVP release gates into a visible checklist for engineering and product review.  
  **Acceptance:** the team can inspect pass/fail status of all gates before pilot.

- **E8-M3-T03 — Run one end-to-end pilot script**  
  Document and test the full flow: import → compile → Passport → mount → writeback → review → export → restore.  
  **Acceptance:** the scripted path can be executed by a human tester without developer improvisation.

- **E8-M3-T04 — Prepare pilot feedback template**  
  Create a structured form or document for collecting “does the AI understand me better?” feedback.  
  **Acceptance:** pilot reviewers have one standard template for reporting fit, trust, and friction.

---

## 4. Suggested Milestone Order for Codex

Recommended execution order:
1. Epic 1 / Milestone 1.1
2. Epic 1 / Milestones 1.2–1.3
3. Epic 2 / Milestones 2.1–2.3
4. Epic 3 / Milestones 3.1–3.3
5. Epic 4 / Milestones 4.1–4.3
6. Epic 5 / Milestones 5.1–5.3
7. Epic 6 / Milestones 6.1–6.3
8. Epic 7 / Milestones 7.1–7.3
9. Epic 8 / Milestones 8.1–8.3

This order protects the product thesis:
- first define the model,
- then ingest and compile,
- then compress into Passport,
- then mount safely,
- then close the review loop,
- then harden for pilots.

## 5. Definition of Done

A milestone is done only when:
1. The scoped functionality exists in the real repo.
2. Tests for the changed behavior pass.
3. Typecheck and lint pass.
4. Documentation is updated.
5. No new permission or traceability regressions are introduced.
6. The milestone does not violate the product’s core principles: Passport-first, read-only-first, evidence-backed, and review-controlled writeback.

## 6. Explicit Anti-Goals for Codex

Codex should not do the following unless a later milestone explicitly asks for it:
1. Build a heavy graph explorer
2. Build a general-purpose search API over the full workspace
3. Introduce capability scoring
4. Add auto-merge writeback
5. Add enterprise-grade permission complexity
6. Add multi-agent autonomy as a core product feature
7. Bind the system to one AI provider
8. Replace human review with silent automation
