# Fathom Conversation Agent Requirements

## Purpose

Define the product requirements for a local, LangGraph-based agent that ingests Fathom conversation transcripts, stores them locally, and produces rerunnable conversation analyses grounded in transcript evidence.

This document captures what the system must accomplish and the constraints it must respect. It does not define the final architecture, module layout, database schema, graph topology, prompt text, or implementation plan.

## Scope

The system must discover Fathom conversations visible through the existing Fathom API integration, identify conversations that have not already completed local processing, download their transcripts, store source artifacts in a careful local filesystem structure, maintain local records that can grow into a usable queryable conversation database, and run transcript-based analyses through a configurable LLM provider.

The initial user is the repository owner operating locally from the CLI or local developer environment. The system is not required to support hosted multi-user operation, remote synchronization, team permissions, or a web UI in the initial scope.

## Inputs Consulted

- User direction in the current requirements discussion.
- Existing Fathom API client and mapper implementation in `src/fathom_play`.
- Existing domain model for meetings, transcripts, utterances, summaries, and people.
- Existing Fathom test fixtures for meetings and transcripts.
- Existing design decisions in `docs/design_decisions.md`.

## Governing Inputs

- The agent must be based on LangGraph.
- LangChain may be used primarily as the model-provider abstraction for returning an LLM connection.
- The default LLM expectation is a local Ollama model.
- The LLM provider must be configurable so that a provider such as Anthropic Claude Sonnet through AWS Bedrock can be used later without changing product behavior.
- Fathom summaries are out of scope for this workflow and must not be required input.
- A conversation is considered previously processed only when it has been downloaded and processed locally.
- Analysis must be rerunnable.
- The local database must start simple, but the product direction is a usable queryable conversation database rather than processing state alone.
- Analytical claims about people, conflict, and meeting conduct must use careful language while still making accurate assessments supported by transcript evidence.
- The user identity for coaching analysis is supplied on the command line when the workflow is run and passed into the workflow with other metadata and optional context.

## Supporting Context

The existing Fathom client can list meetings and fetch transcripts by recording ID. The existing mapper converts Fathom JSON into provider-neutral domain objects. Current fixtures show available meeting metadata including meeting ID, recording ID, title, start/end time, duration, recorded-by person, calendar invitees, speakers, transcript text, and transcript timestamps.

## Product Goals

- Create a reliable local record of Fathom conversations and transcripts.
- Avoid reprocessing conversations that already completed local ingestion and analysis.
- Preserve enough source data to support future remapping or reanalysis.
- Produce useful analysis from several perspectives: action items, meeting coaching, conversation type, and people dynamics.
- Keep results auditable by tying important conclusions back to transcript evidence.
- Keep early development flexible while preserving a path toward practical local query, review, and automation over conversation records.

## Out Of Scope

- Hosted service deployment.
- Multi-user authorization or shared team data access.
- Web UI.
- Vector search, embeddings, semantic search, or retrieval augmentation beyond the current transcript in the first implementation.
- Automated calendar updates, task creation, CRM writes, or outbound notifications.
- Use of Fathom-provided summaries as source material.
- Final architecture, database schema, graph node design, or exact prompts.

## Functional Requirements

### FCR-001: Discover Available Conversations

The system must discover conversations available from Fathom through the existing local API integration.

Acceptance criteria:

- The system can retrieve a list of visible Fathom meetings.
- Each discovered meeting is identified at minimum by recording ID.
- Available meeting metadata is captured for later local persistence.
- Pagination behavior must not silently omit available meetings within the selected discovery scope.

### FCR-002: Determine Processing Eligibility

The system must determine whether a discovered conversation requires local processing.

Acceptance criteria:

- A conversation is eligible when there is no local record showing completed download and completed processing for its recording ID.
- A conversation that failed or stopped partway through processing remains eligible for retry.
- A conversation that was downloaded but not successfully analyzed is not treated as fully processed.
- Rerunnable analysis does not require redownloading the transcript unless the operator explicitly requests refreshed source artifacts.

### FCR-003: Download Transcript Source

The system must download the transcript for each eligible conversation.

Acceptance criteria:

- The transcript is fetched from Fathom by recording ID.
- The raw transcript response is preserved locally.
- A human-readable transcript file is produced locally.
- Transcript entries preserve speaker, timestamp, and text where available.
- Missing or empty transcripts are recorded as processing outcomes rather than causing silent success.

### FCR-004: Store Local Source Artifacts

The system must store source artifacts in a careful, predictable local filesystem structure.

Acceptance criteria:

- Each conversation has a dedicated local location keyed by stable Fathom identity, preferably recording ID.
- Stored source artifacts include meeting metadata and transcript data.
- Filesystem paths are recorded in the local database.
- File names and layout support manual inspection during development.
- The system does not rely on Fathom summaries for source artifact completeness.

### FCR-005: Maintain Local Conversation Records

The system must maintain local conversation records in a local database that starts simple but is oriented toward future query and automation use.

Acceptance criteria:

- The database records discovered/processed conversations by recording ID.
- The database records enough metadata to inspect local processing status.
- The database records paths to local transcript and analysis artifacts.
- The database distinguishes at least pending, in-progress, completed, and failed processing outcomes.
- The database supports recording multiple analysis runs for the same conversation.
- The database preserves enough structured metadata to support later querying by meeting identity, time, participants, status, and available analysis runs.

### FCR-006: Classify Conversation Type

The system must classify each processed conversation by type.

Acceptance criteria:

- The classification includes a primary conversation type.
- The classification includes confidence.
- The classification includes transcript evidence or rationale sufficient to understand why the type was chosen.
- The classification supports an unknown or uncertain outcome when evidence is insufficient.

### FCR-007: Extract Action Items

The system must extract action items from each transcript.

Acceptance criteria:

- Each action item includes the task.
- Each action item includes the owner when identifiable.
- Each action item includes due date or timing when identifiable.
- Each action item distinguishes explicit commitments from inferred follow-ups.
- Each action item includes transcript evidence with speaker and timestamp where available.
- The system can represent that no action items were found.

### FCR-008: Produce Meeting Coaching Review

The system must analyze how the user conducted the meeting from a coaching perspective.

Acceptance criteria:

- The review identifies useful behaviors demonstrated by the user.
- The review identifies opportunities to improve meeting conduct.
- The review considers clarity, listening, question quality, agenda control, decision hygiene, and follow-up quality when evidence exists.
- Claims are grounded in transcript evidence.
- The review avoids overstating conclusions when the transcript does not provide enough evidence.

### FCR-009: Produce People Dynamics Review

The system must identify relevant problems, conflicts, information gaps, working styles, and personality or approach signals present in the transcript.

Acceptance criteria:

- Observations include careful language and confidence.
- Observations are tied to transcript evidence.
- The system distinguishes direct evidence from inference.
- The system can represent absence of evidence rather than inventing dynamics.
- The analysis is framed as meeting-specific observations, not clinical or definitive personality judgments.

### FCR-010: Persist Analysis Outputs

The system must persist analysis outputs locally.

Acceptance criteria:

- Analysis outputs are written to local files.
- Each output is associated with the relevant recording ID.
- Each output is associated with a specific analysis run.
- The local database records analysis run status and artifact paths.
- Failed analyses preserve error information sufficient for retry or debugging.

### FCR-011: Support Rerunnable Analysis

The system must allow analysis to be rerun for a previously ingested conversation.

Acceptance criteria:

- Reruns do not overwrite prior analysis runs by default.
- Each analysis run records model/provider identity where available.
- Each analysis run records prompt or analysis version where available.
- The operator can compare multiple runs for the same recording through stored artifacts and database records.

### FCR-012: Configurable LLM Provider

The system must support configurable model-provider selection.

Acceptance criteria:

- Ollama is supported as the initial local default provider.
- The product requirements allow a future Bedrock-backed Sonnet configuration.
- Provider choice is configuration-driven rather than hard-coded into analysis behavior.
- Analysis output expectations are provider-independent.

### FCR-013: Support Local Query And Review

The system must preserve conversation and analysis information in a way that can support local query and review workflows as the product evolves.

Acceptance criteria:

- The system records structured conversation metadata separately from raw transcript files.
- The system records analysis outputs in association with conversation and analysis-run identity.
- The system can support basic local queries without requiring transcript reprocessing.
- The initial query surface may be limited, but the stored records must not be shaped only for one ingestion workflow.
- Future workflow automations can use local conversation records as inputs without calling Fathom again unless source refresh is explicitly needed.

### FCR-014: Accept Workflow Runtime Context

The system must accept operator-provided runtime context for workflows.

Acceptance criteria:

- The CLI can accept the user identity used for coaching analysis.
- The CLI can pass user identity into the workflow with other runtime metadata.
- The workflow can receive optional context that may guide analysis without changing stored source artifacts.
- Analysis outputs can record the runtime context relevant to interpreting the run.

## Evidence Requirements

Analytical outputs must retain evidence for meaningful claims. Evidence should include speaker, timestamp, and excerpt when available.

For uncertain or inferential claims, the output must identify the uncertainty. Acceptable confidence levels are low, medium, and high unless a later design selects a more precise scale.

The system must not present inferred working styles, conflict, intent, or personality-related observations as facts without evidence and qualification.

## Non-Functional Requirements

### NFR-001: Local First

The system must run locally and store its database and artifacts locally.

### NFR-002: Inspectability

Local files and database records must be understandable during early development without specialized tooling beyond common developer tools.

### NFR-003: Idempotent Processing

Repeated runs must avoid duplicating completed ingestion and must safely retry incomplete or failed processing.

### NFR-004: Provider Flexibility

The product behavior must not depend on a single hosted LLM provider.

### NFR-005: Source Preservation

Raw source data needed to explain or rerun analysis must be preserved locally.

### NFR-006: Conservative Data Scope

The system must avoid collecting or deriving data not needed for the stated analysis goals during early development.

### NFR-007: Query-Oriented Evolution

The local database must be allowed to evolve from simple processing state into a practical local conversation database while avoiding premature search or embedding infrastructure.

## Data Requirements

The system should preserve, when available:

- Fathom meeting ID.
- Fathom recording ID.
- Meeting title.
- Recording start time.
- Recording end time.
- Duration.
- Recorded-by person.
- Calendar invitees.
- Transcript speakers.
- Transcript timestamps.
- Transcript text.
- Local artifact paths.
- Processing status.
- Analysis run status.
- LLM provider and model used for analysis.
- Prompt or analysis version used for analysis.
- Structured analysis findings suitable for later query and review where practical.

## Decisions Made

- Fathom summaries will not be used in this workflow.
- The transcript is the primary source artifact for analysis.
- Previously processed means both downloaded and processed locally.
- Analysis must support reruns.
- The local database should start simple, but its product role is a queryable local conversation database over time.
- People-dynamics and coaching analysis must be careful, evidence-grounded, and explicit about confidence.
- User identity for coaching analysis is provided at workflow runtime through the CLI, with optional contextual metadata.

## Decisions Explicitly Deferred

- Exact local database technology and schema.
- Exact filesystem layout.
- Exact LangGraph graph topology.
- Exact tool interfaces.
- Exact prompt templates.
- Exact analysis output schemas.
- CLI command names and user interaction model.
- Whether analysis should run automatically after ingestion or be a separate operator action.
- Whether transcript refresh detection should use hashes or manual operator control.
- Whether future search should use plain SQL, full-text search, embeddings, or another mechanism.
- The exact boundary between source artifact storage and queryable database records.

## Open Questions

- What time range should default discovery use?
- Should discovery include all historical Fathom meetings on first run, or require an explicit backfill command?
- Should failed transcript downloads be retried automatically, manually, or both?
- Should the system support deleting local artifacts for a recording?

## Questions For CTO

- Confirm whether SQLite is acceptable as the initial local conversation database if selected during design.
- Confirm whether filesystem artifacts under a repository-local `data/` directory are acceptable for early development.
- Confirm whether model outputs should be JSON-first for structured analysis, with optional Markdown renderings for human review.
- Confirm whether future provider support must include AWS Bedrock Sonnet as the first non-local provider.

## Decisions Requested

- Decide the default discovery/backfill behavior.

## Later CTO Decisions

- The requirements are approved as governing input for architecture and downstream technical design.
- Action-item extraction covers all participants and associates actions with a participant where possible.
- Verbatim transcript evidence excerpts are allowed in local analysis artifacts.
- User identity for coaching analysis is supplied on the command line at workflow runtime, with optional context.

## Recommended Next Step

Review and approve the requirements, then create a system componentization or lightweight architecture document that defines the local storage boundary, LangGraph orchestration boundary, Fathom ingestion boundary, and LLM-provider boundary.

## Approval Status

approved

## Architect Review

Not yet reviewed.

## CTO Review

Approved by CTO on 2026-04-30 for componentization. Reconfirmed by CTO on 2026-05-01 as governing input for architecture and downstream technical design.

## Sign-Off

### Author

- Signer: Codex
- Signer Type: agent
- Role: Requirements author
- Review Perspective: requirements drafting
- Disposition: submitted-for-review
- Summary Notes: Initial requirements specification for the local Fathom conversation agent.
- Date: 2026-04-30

### Review Entries

No review entries yet.

### CTO Sign-Off

- Signer: CTO (Human)
- Signer Type: human
- Status: approved
- Date: 2026-05-01

### Workflow Status

- Current Status: approved
