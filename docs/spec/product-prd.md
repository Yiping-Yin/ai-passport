# AI Knowledge Passport: Complete User Story + PRD (v1.0)

Status: Draft for Codex / MVP Definition  
Last Updated: 2026-04-05

---

# Part I. Complete User Story

## 1. Core User Story

As a long-horizon learner and a frequent collaborator with AI systems, I want to compile my scattered materials, projects, experience, recurring mistakes, and current goals into a permissioned knowledge passport that external AIs can understand quickly. That way, when I work with GPT, Claude, or any other AI, I do not need to re-explain my background from scratch every time. Instead, the AI can begin with knowledge postcards, capability signals, mistake patterns, and my active focus, understand my baseline and gaps, read deeper only within authorized scope, and return useful outputs as review candidates instead of silently writing into my core knowledge base.

## 2. Target Users

### 2.1 P0 Core Users
- People who work with multiple AIs frequently
- People with long-term material and project accumulation
- People who repeatedly re-explain their background in AI conversations
- People who need help tailored to their real level, context, and current goals
- People who want AI outputs to compound into a durable knowledge asset

### 2.2 Representative Personas
1. **Students and self-learners** with lecture notes, papers, exercises, mistakes, and project reports
2. **Researchers and analysts** with literature notes, experiment logs, hypotheses, drafts, and findings
3. **Developers** with code, design docs, architecture notes, postmortems, and error histories
4. **Creators and consultants** with source libraries, drafts, client context, frameworks, and case studies

## 3. Core Jobs-to-be-Done

### JTBD-01: Start an AI session with context already loaded
When I begin a new AI session, I want the AI to immediately know my baseline, goals, and weak spots, so it does not start from a blank assumption about who I am.

### JTBD-02: Turn long-term accumulation into reusable structure
When I keep accumulating notes, projects, documents, and reflections over time, I want them to be compiled into reusable knowledge structures instead of staying as disconnected files.

### JTBD-03: Let AI outputs compound over time
When an AI produces new summaries, plans, explanations, or research results, I want those outputs to come back into the system through a review flow, so my knowledge and progress can actually compound.

## 4. Layered User Stories

### US-01 Workspace and cold start
As a user, I want to create personal, work, or project workspaces quickly and generate an initial passport entry after importing a small number of materials, so the system becomes useful on day one.

**Acceptance criteria**
1. The system supports personal, work, and project workspaces.
2. After first import, the onboarding flow can generate 3–5 representative postcard candidates.
3. The system generates one initial Passport Draft.
4. The user can see what is already mountable by external AI and what is still missing.

### US-02 Unified intake for multi-source materials
As a user, I want to import lectures, notes, web pages, papers, project artifacts, work documents, and reflections into one system, so my knowledge does not remain scattered across many tools.

**Acceptance criteria**
1. The system supports web pages, Markdown, PDF, plain text, and project document imports.
2. Each source retains original content, provenance, import time, workspace assignment, and privacy level.
3. Imported items land in Inbox with visible status.
4. The raw source is never overwritten by the compile process.

### US-03 Automatic compilation into foundational knowledge structure
As a user, I want the system to automatically organize raw materials into topic pages, project pages, method pages, and question pages, so my knowledge becomes understandable structure instead of a pile of files.

**Acceptance criteria**
1. The system generates at least four node types: topic, project, method, and question.
2. It creates basic links and reverse links between nodes.
3. Every high-level result can trace back to raw sources.
4. Key generated results are manually editable.

### US-04 Traceable evidence fragments
As a user, I want generated judgments, summaries, and cards to trace back to concrete evidence fragments, so I can trust the system and verify it quickly.

**Acceptance criteria**
1. The system extracts evidence fragments from sources.
2. Every high-level object can reference one or more evidence fragments.
3. Knowledge nodes, capability signals, mistake patterns, and postcards all expose source links.
4. The user can jump from a card back to a source location or source description.

### US-05 Capability signals instead of hard capability labels
As a user, I want the system to extract capability signals and current gaps from my materials and projects instead of assigning me rigid labels or scores, so the AI’s interpretation of me stays cautious and explainable.

**Acceptance criteria**
1. The system can express observed knowledge, observed practice, and current gaps on a topic.
2. The system does not output a single capability score.
3. Each capability signal references evidence.
4. The user can correct or hide capability signals.

### US-06 Mistake pattern detection
As a user, I want the system to identify recurring errors, confusions, and biases in specific topics, so external AI understands where I need targeted help.

**Acceptance criteria**
1. The system records recurring errors and misunderstanding patterns.
2. Each mistake pattern can attach examples and suggested corrections.
3. Mistake patterns are readable by external AI, with sensitive items hideable.
4. The user can edit, confirm, or dismiss a mistake pattern.

### US-07 Active focus tracking
As a user, I want to express what I am currently trying to solve in addition to my long-term knowledge base, so AI help is grounded not only in my history but also in my present goal.

**Acceptance criteria**
1. The user can create, switch, and close Focus Cards.
2. A Focus Card includes goal, time range, priority, and success criteria.
3. External AI can read the active Focus Card first.
4. Inactive Focus Cards are not exposed as default context.

### US-08 Knowledge postcard generation
As a user, I want the system to turn important topics into knowledge postcards, so external AI can understand my state on a topic without reading the full knowledge base first.

**Acceptance criteria**
1. Each postcard contains at least: topic, what I know, what I have done, common gaps, active questions, and suggested next steps.
2. Postcards link to knowledge nodes and evidence.
3. The system supports four postcard classes: knowledge, capability, mistake, and exploration.
4. Postcards can be regenerated into new candidate versions as the knowledge base changes.

### US-09 Knowledge passport generation
As a user, I want the system to assemble multiple postcards into a high-level knowledge passport, so external AI can understand my topic landscape and growth state at a glance.

**Acceptance criteria**
1. The passport includes owner summary, theme map, capability signals, active focus, and representative postcards.
2. It provides both a human-readable and a machine-readable version.
3. The user can hide or edit selected content.
4. The Passport can act as the default entry point for external AI.

### US-10 Mount external AI instead of exporting the whole knowledge base
As a user, I want GPT or any other external AI to mount my passport rather than requiring me to repeatedly export and upload my entire knowledge base, so cross-model usage is lighter, faster, and safer.

**Acceptance criteria**
1. On first access, external AI can read only the Passport and representative Postcards.
2. Default access mode is read-only.
3. Deeper access requires a Visa Bundle.
4. Every mount action is logged.

### US-11 Use visa-based control for deeper access
As a user, I want specific scenarios to open specific topics or nodes to external AI only when needed, so permissions stay simple, visible, and revocable.

**Acceptance criteria**
1. The MVP supports exactly three permission levels: `passport_read`, `topic_read`, and `writeback_candidate`.
2. A Visa Bundle can limit topic scope, visible objects, expiration, and writeback policy.
3. The user can revoke a Visa manually.
4. Expired Visas become invalid automatically.

### US-12 Route AI-generated outputs into a review queue
As a user, I want new summaries, lecture notes, outlines, memos, and questions generated by external AI to come back into the system without polluting the main knowledge base, so my knowledge asset grows in a controlled way.

**Acceptance criteria**
1. New AI outputs enter a Review Queue.
2. The user can accept, edit then accept, or reject.
3. Accepted outputs can update a knowledge node, postcard, or focus card.
4. Every writeback records the source session.

### US-13 Auditing, revocation, and recovery
As a user, I want my passport to be usable by different AI systems while still remaining controllable, revocable, and recoverable, so I am not locked into a platform or worried about losing control of my data.

**Acceptance criteria**
1. The system logs mounts, reads, writebacks, revocations, and review actions.
2. It supports Visa expiration and manual revocation.
3. It supports export of core structures, cards, and session logs.
4. It supports local backup and restore.

### US-14 Cross-model reuse instead of platform lock-in
As a user, I want the same passport to be reused by multiple AI systems, so I do not have to rebuild context separately for every platform.

**Acceptance criteria**
1. The Passport exposes a machine-readable manifest.
2. Core objects do not depend on a single model’s naming or proprietary format.
3. The mount layer can be consumed by different AI clients.
4. Switching AI providers does not require re-uploading all raw material.

---

# Part II. Product Requirements Document

## 1. Document Overview

### 1.1 Product Name
**AI Knowledge Passport**

### 1.2 Subtitle
**A personal knowledge base that external AIs can mount and read under permission**

### 1.3 One-line Positioning
Help any AI understand your knowledge base, current goals, and recurring mistakes quickly and safely.

### 1.4 Product Summary
AI Knowledge Passport is a local-first, permissioned knowledge compilation and AI interface system. It continuously compiles a user’s raw materials, project history, reflections, mistakes, and current goals into structured knowledge, then compresses that structure into Postcards, a Passport, and scenario-specific Visas. External AI no longer requires the user to repeatedly upload an entire archive or explain themselves from scratch. Instead, the AI begins with the Passport and representative Postcards, understands the user’s baseline and focus, requests deeper access only when authorized, and returns useful outputs as review candidates rather than silently altering the canonical knowledge store.

## 2. Background and Opportunity

Today’s main limitation in personal AI assistance is not model capability alone. It is missing personal context:
- The AI does not know what the user already knows.
- The AI does not know where the user repeatedly gets stuck.
- The AI does not know what the user is working on right now.
- The AI does not know how deep or shallow to go for this particular person.
- Every model switch forces the user to explain themselves again.

At the same time, users’ own knowledge accumulates across notes, folders, web pages, project documents, and AI conversations. That accumulation rarely becomes a reusable, cross-model context asset.

The opportunity is therefore not “yet another note-taking tool.” It is a new layer of infrastructure:

**A personal knowledge base plus an AI understanding interface.**

## 3. Strategic Focus

### 3.1 Core Promise
Version one does not try to become an all-purpose personal cognition OS. It does one thing:

**Help AI understand you faster and more accurately.**

### 3.2 Explicit Non-Goals
1. Not a general-purpose cloud note app
2. Not a full social knowledge network
3. Not enterprise team knowledge management
4. Not foundation model training or fine-tuning
5. Not an autonomous auto-write system
6. Not a product that assigns users a single capability score
7. Not a heavy agent runtime platform
8. Not a protocol-first moat in v1

### 3.3 Lessons Borrowed, But Not Copied
1. Borrow the idea of a compiled middle knowledge layer, but do not make the product feel like “a wiki product.”
2. Borrow the idea of an experiment loop, but do not build infinite autonomy.
3. Borrow controlled runtime ideas, but do not build an oversized agent OS.
4. Borrow skill-like internal workflows, but do not surface system complexity to end users.

## 4. Product Goals

### 4.1 Core Goal
Enable external AI to understand a user faster and more accurately after reading the Passport than in a blank conversation.

### 4.2 User Goals
1. Stop re-explaining themselves in every AI session
2. Get help that matches their actual level and context
3. Let knowledge and exploration results compound over time
4. Reuse the same context across AI systems without platform lock-in

### 4.3 Business Goals
1. Validate whether “AI context infrastructure” is a real product category
2. Validate whether users will maintain a passport over time
3. Validate whether a Passport-first interaction improves first-response relevance

## 5. Target Users

### 5.1 P0 Core Users
Frequent AI users with long-horizon accumulation:
- Students
- Researchers
- Developers
- Creators
- Consultants
- Knowledge workers
- Freelancers

### 5.2 Shared User Traits
- They have substantial documents, notes, or projects
- They collaborate with multiple AIs
- They dislike repeating background context
- They need personalized help
- They want outputs to flow back into a durable system

## 6. Product Principles

1. **Postcards first.** External AI starts with concise high-level cards, not the whole knowledge base.
2. **Read-only first.** Default mode is read-only; any writeback goes to review.
3. **Traceable evidence.** All high-level descriptions must trace back to nodes and sources.
4. **Capability signals, not capability verdicts.** Avoid false precision and overreach.
5. **Goal aware.** The system must express what the user is currently trying to solve.
6. **Workspace isolation.** Personal, work, and project contexts must stay separable.
7. **Local core plus controlled gateway.** Not purely local, not purely cloud.
8. **Model agnostic.** The data model should not depend on one AI provider.
9. **Cold-start first.** Generate 3–5 strong representative postcards before attempting a full graph.
10. **Governance before automation.** Reviewability, revocability, and traceability come before stronger autonomy.

## 7. Brand Language and Internal Product Language

### 7.1 External Brand Language
- Postcard
- Passport
- Visa

### 7.2 Internal Product Language
- Card
- Manifest / Record
- Visa Bundle
- Session
- Review Candidate

**Note:** brand language helps product comprehension and positioning; internal naming should minimize metaphor stacking and implementation confusion.

## 8. Core Concepts and Data Model

### 8.1 Workspace
A container that separates personal, work, and project knowledge domains.

### 8.2 Source
A raw imported artifact. Suggested fields:  
`id, type, title, origin, imported_at, workspace_id, tags, privacy_level, raw_blob_ref`

### 8.3 Knowledge Node
A structured knowledge object. Suggested fields:  
`id, node_type, title, summary, body, source_ids, related_node_ids, updated_at`

### 8.4 Evidence Fragment
A traceable excerpt or locator from a raw source. Suggested fields:  
`id, source_id, locator, excerpt, confidence`

### 8.5 Capability Signal
An evidence-backed observation about demonstrated practice and current gaps. Suggested fields:  
`id, topic, evidence_ids, observed_practice, current_gaps, confidence`

### 8.6 Mistake Pattern
A recurring error, confusion, or bias pattern. Suggested fields:  
`id, topic, description, examples, fix_suggestions, recurrence_count`

### 8.7 Focus Card
An expression of what the user is currently trying to accomplish. Suggested fields:  
`id, title, goal, timeframe, priority, success_criteria, related_topics, status`

### 8.8 Knowledge Postcard
A concise, topic-level AI-readable summary. Suggested fields:  
`id, card_type, title, known_things, done_things, common_gaps, active_questions, suggested_next_step, evidence_links, related_nodes, visibility, version`

### 8.9 Passport Manifest
The high-level packaged representation of the user’s knowledge state. Suggested fields:  
`id, owner_summary, theme_map, capability_signals, focus_cards, representative_postcards, machine_manifest, version`

### 8.10 Visa Bundle
A scope-limited access package for deeper reads. Suggested fields:  
`id, scope, included_postcards, included_nodes, expiry_at, access_mode, writeback_policy, redaction_rules, status`

### 8.11 Mount Session
A record of an external AI interaction under a Visa. Suggested fields:  
`id, client_type, visa_id, started_at, ended_at, actions, writeback_count, status`

### 8.12 Review Candidate
A candidate object generated by an external AI and awaiting review. Suggested fields:  
`id, session_id, candidate_type, content_ref, target_object, diff_ref, status`

### 8.13 Audit Log
An append-only governance record. Suggested fields:  
`id, actor, action, object_id, timestamp, result, meta`

## 9. Product Architecture

### Layer 1: Source Layer
Receives and preserves raw source material.

### Layer 2: Compile Layer
Compiles sources into knowledge nodes, evidence fragments, capability signals, and mistake patterns.

### Layer 3: Passport Layer
Compresses high-value knowledge into Postcards and the Passport.

### Layer 4: Mount Layer
Provides controlled external AI access to Passports and selected nodes.

### Layer 5: Review and Governance Layer
Owns permissions, visas, session logs, revocation, and writeback review.

## 10. Core Flows

### 10.1 Cold-start flow
Create workspace  
→ import 1–5 core materials  
→ compile initial nodes and evidence  
→ generate 3–5 representative postcards  
→ generate initial passport  
→ user reviews and enables mountability

### 10.2 Ingestion and compilation flow
Import source  
→ land in Inbox  
→ trigger compile job  
→ generate topic / project / method / question nodes  
→ extract evidence fragments  
→ generate capability signals and mistake patterns  
→ generate or update postcards  
→ update passport

### 10.3 Mount flow
External AI initiates connection  
→ reads Passport Manifest  
→ reads representative Postcards  
→ reads active Focus Card  
→ requests Visa if deeper access is required  
→ reads authorized knowledge nodes  
→ produces a helpful output

### 10.4 Writeback flow
AI generates new summary / outline / question set / lecture note  
→ output enters Review Queue  
→ user reviews  
→ accept / edit then accept / reject  
→ approved result merges into node / postcard / focus card target  
→ audit log records the action

### 10.5 Governance flow
Create Visa  
→ use mount session  
→ expiry or manual revocation  
→ inspect audit trail  
→ export and backup

## 11. Information Architecture and Screens

### 11.1 Top-Level Navigation
1. Dashboard
2. Inbox
3. Knowledge
4. Passport
5. Mount
6. Review
7. Settings

### 11.2 Navigation Notes
- Signals do not become a top-level page; they live inside Knowledge.
- Postcards do not become a top-level page; they live inside Knowledge and Passport.
- This reduces metaphor overload and lowers cognitive load.

### 11.3 Screen Responsibilities

#### Dashboard
Shows current Focus, Passport Readiness, recent imports, pending review items, and recent mount sessions.

#### Inbox
Manages raw materials and compile queue items, with source details, status, evidence preview, and recompile action.

#### Knowledge
Browses topic / project / method / question nodes and shows capability signals, mistake patterns, linked Focus Cards, and postcards in context.

#### Passport
Manages human-readable and machine-readable passport views, with preview, edit, hide, regenerate, and Visa creation actions.

#### Mount
Manages Visa Bundles, mount sessions, access logs, expiration, and revocation.

#### Review
Shows candidate diffs, source sessions, target objects, and user actions: accept, edit then accept, reject.

#### Settings
Manages workspaces, privacy rules, export, backup, logging, and default policies.

## 12. Functional Requirements

### A. Workspace and cold start

**FR-01 Create workspace**  
Support personal, work, and project workspace types.

**FR-02 Cold-start onboarding**  
After initial imports, generate 3–5 representative postcard candidates and one draft Passport.

**FR-03 Readiness indicator**  
Display Passport Readiness so the user knows whether the workspace is ready to mount.

### B. Ingestion and source management

**FR-04 Multi-source import**  
Support import from web pages, Markdown, PDF, plain text, and project documents.

**FR-05 Preserve raw source**  
Raw material must be retained and never replaced by summaries only.

**FR-06 Source metadata**  
Each source stores origin, imported_at, workspace, and privacy_level.

**FR-07 Inbox management**  
Imported sources land in Inbox and show compile status, error state, and retry controls.

### C. Knowledge compilation

**FR-08 Generate knowledge nodes**  
Generate at least topic, project, method, and question nodes.

**FR-09 Extract evidence fragments**  
Support source extraction into citeable evidence fragments.

**FR-10 Relationship links**  
Support basic relation links and reverse links between nodes.

**FR-11 Reviewable compile output**  
Allow key compile outputs to be edited or corrected by a user.

### D. Capability signals, mistake patterns, and the goal layer

**FR-12 Generate capability signals**  
Generate evidence-backed capability signals from projects and knowledge nodes.

**FR-13 Generate mistake patterns**  
Generate mistake patterns from error logs, repeated questions, or learning traces.

**FR-14 Review and hide signals**  
Allow users to edit, hide, or dismiss capability signals and mistake patterns.

**FR-15 Active Focus Card**  
Allow users to create, switch, and archive Focus Cards.

**FR-16 AI reads active focus first**  
Allow external AI to read the active Focus Card before deeper context.

### E. Postcards and Passport

**FR-17 Generate postcards**  
Generate knowledge, capability, mistake, and exploration postcards.

**FR-18 Version postcard updates**  
When knowledge changes, generate new postcard candidates with versioning.

**FR-19 Generate Passport**  
Organize postcards, capability signals, and Focus Cards into a Passport Manifest.

**FR-20 Dual-format output**  
Provide both a human-readable and a machine-readable passport.

**FR-21 Representative compression**  
Passport defaults to representative postcards, not a full knowledge graph dump.

**FR-22 Hide and rewrite content**  
Allow users to hide sensitive objects or rewrite the owner summary.

### F. Mounting and access

**FR-23 Read-only first mount**  
On first mount, external AI can read only the Passport, representative Postcards, and active Focus.

**FR-24 Visa-gated deeper access**  
Deeper node access requires authorization through a Visa Bundle.

**FR-25 Three permission levels**  
The MVP supports `passport_read`, `topic_read`, and `writeback_candidate`.

**FR-26 Session record**  
Record external AI reads, Visa requests, and writeback actions.

**FR-27 Expiration and revocation**  
Support expiration, manual revocation, and visible Visa status.

**FR-28 Whitelist-only object access**  
External AI may read only objects explicitly included in a Visa. No default search across the whole workspace.

### G. Writeback and review

**FR-29 Writeback candidates**  
New summaries, outlines, questions, and teaching artifacts created by external AI must enter Review Queue.

**FR-30 No auto-merge**  
No external AI output may write directly into the canonical knowledge store.

**FR-31 Diff view**  
Review Queue must show target object, diff, source session, and evidence links where applicable.

**FR-32 Review merge actions**  
Users can accept, edit then accept, or reject.

**FR-33 Source session traceability**  
Every review candidate must trace back to a concrete mount session.

### H. Governance and recovery

**FR-34 Audit log**  
All mount, read, revoke, and review actions must be recorded in an audit log.

**FR-35 Export and local backup**  
Support export of core structures, cards, Passport, review candidates, and logs.

**FR-36 Restore**  
Support restore from local backup.

**FR-37 Privacy controls**  
Each source and object can define visibility or privacy level.

## 13. Minimum Mounting API

The MVP should expose only the minimum necessary interface:
- `GET /passport/{id}/manifest`
- `GET /postcards/{id}`
- `POST /visas`
- `POST /mount-sessions`
- `POST /writeback-candidates`

**Principles**
1. External AI reads snapshots first instead of scanning the entire workspace.
2. P0 does not expose a heavy general-purpose query API.
3. The product must first prove that Passport-first interaction is valuable.

## 14. MVP Scope

### 14.1 In Scope
1. Multi-source import
2. Foundational knowledge compilation
3. Initial extraction of capability signals and mistake patterns
4. Active Focus Card
5. Knowledge Postcards
6. Passport
7. Read-only mounting
8. Simple Visa control
9. Review Queue for writeback candidates
10. Audit logging
11. Local export and restore

### 14.2 Out of Scope
1. Multi-agent autonomous research loops
2. Cross-person knowledge networks
3. Autonomous external actions
4. Enterprise-grade complex permission models
5. Model fine-tuning or training
6. Full graph-database browsing experience
7. Large plugin ecosystems
8. Auto-merge writeback

## 15. Non-Functional Requirements

### 15.1 Explainability
- Every high-level object must expose evidence trace.
- Every writeback must expose session trace.

### 15.2 Safety and permissions
- Read-only by default
- Whitelist-only object access
- Expiration and revocation must take effect reliably

### 15.3 Data sovereignty
- Core data must be exportable and restorable locally
- The system must not require lock-in to one cloud provider

### 15.4 Maintainability
- Postcards, Passports, Visas, and Review Candidates must be versionable
- Compile failures and review failures must be visible states

### 15.5 MVP Performance Goals
- Initial Passport generation should complete within a single user session after first import
- Passport Manifest should remain lightweight enough to act as a first-read context packet
- Review actions should be completable on one screen without navigation sprawl

## 16. Success Metrics

### 16.1 North Star Metric
**The number of times an external AI gives directly useful help that matches the user’s actual level after reading the Passport.**

### 16.2 Leading Indicators
1. Fewer times the user repeats background in AI conversations
2. Higher user-rated relevance of the AI’s first helpful response
3. Passport Readiness attainment rate
4. Representative postcard generation success rate
5. Topic-level Visa usage rate
6. Review Candidate acceptance rate
7. User perception: “The AI understands me better”
8. User perception: “The AI teaches or guides me more appropriately”

### 16.3 Guardrail Metrics
1. Incorrect writeback merged into canonical store = 0
2. Unauthorized access to protected objects = 0
3. Percentage of high-level objects without evidence trace should trend down
4. Mount abandonment due to permission complexity should not trend upward materially

### 16.4 Vanity Metrics to Avoid
1. Number of imported files
2. Number of generated wiki-like pages
3. Number of cards
4. Number of protocol objects

## 17. Risks and Mitigations

### Risk 1: Capability misclassification
Mitigation: use evidence-backed capability signals rather than a single score, and allow human correction.

### Risk 2: Compile distortion
Mitigation: keep high-level cards reviewable and every important statement traceable.

### Risk 3: Knowledge pollution from external AI
Mitigation: external AI can only submit candidates; it cannot auto-merge into the canonical store.

### Risk 4: User distrust caused by permission complexity
Mitigation: keep the MVP permission model limited to three levels.

### Risk 5: Overweight cold start
Mitigation: generate 3–5 strong representative postcards first instead of chasing a full graph.

### Risk 6: Weak product sharpness
Mitigation: communicate one promise externally: help AI understand you faster and more accurately.

### Risk 7: Protocol before value
Mitigation: treat the protocol as an output layer, not the moat; the moat is compile quality, personalization, and governance.

### Risk 8: Tension between local-first and cross-model access
Mitigation: use a local core plus controlled gateway instead of choosing purely local or purely cloud.

### Risk 9: Metaphor overload
Mitigation: reduce the number of top-level objects and keep internal implementation language simpler than brand language.

### Risk 10: Premature expansion into an agent OS
Mitigation: keep the MVP focused on the knowledge base plus controlled mount loop, not a heavy autonomous runtime.

## 18. Roadmap

### MVP
Prove that an AI Knowledge Passport can reduce repeated context explanation and improve the relevance of AI help.

### V1
Strengthen capability signals, mistake patterns, the goal layer, and finer-grained Visa control.

### V2
Add knowledge health checks, compiler benchmarks, candidate quality scoring, and stronger writeback workflows.

### V3
Only after single-user value is proven, explore person-to-person passport exchange and a more open protocol layer.

## 19. Release Gates

The MVP may enter real-user testing only when all conditions below are true:
1. A user can complete the end-to-end flow from import to initial Passport
2. External AI can read Passport + Postcards + Focus Card
3. Topic-level Visa can be granted and revoked
4. External AI writeback always enters Review Queue
5. All high-level objects expose source evidence
6. All writeback candidates expose source session trace
7. Core data can be exported and restored
8. At least one real user cohort validates less background repetition and better first-response fit

## 20. Implementation Notes for Codex

1. Build the main path first: Source → Compile → Passport → Mount → Review
2. Do not start with heavy graph features or advanced visualization
3. Do not start with complex protocol design or large multi-platform plugin work
4. Do not allow external AI to search the whole workspace by default
5. Do not allow writeback to enter the canonical knowledge store directly
6. Build the smallest loop that is explainable, revocable, and reviewable

---

## Final Product Definition

**AI Knowledge Passport is not about storing more knowledge.**  
**It is not about training a private model.**  
**It is about turning your knowledge, goals, and recurring mistakes into a passport that any AI can quickly understand.**


---

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
