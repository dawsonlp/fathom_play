# Fathom Conversation Agent Technical Design

## Purpose

Define the technical design for implementing the approved local Fathom conversation agent architecture. This design specifies subsystem behavior, interfaces, local data handling, workflow execution expectations, and operational behavior while preserving the approved Conversation Knowledge Base architecture.

## Scope

This design covers the first local implementation of:

- Fathom transcript ingestion.
- Local source artifact storage.
- Local query-oriented conversation database.
- Separate ingestion and analysis workflows.
- Runtime user identity and optional context handling.
- Evidence-grounded transcript analysis.
- Configurable LLM access through LangChain-compatible providers.
- CLI adapter behavior for workflow triggering and basic result display.

This design does not include production code, final prompt wording, final JSON schemas, exhaustive database migrations, advanced search, embeddings, hosted deployment, or UI design.

## Inputs Consulted

- Approved requirements in `docs/conversation_agent_requirements.md`.
- Approved componentization in `docs/conversation_agent_componentization.md`.
- Approved architecture in `docs/conversation_agent_architecture.md`.
- Senior systems engineer architecture review in `docs/conversation_agent_architecture.md`.
- Existing Fathom client, mapper, domain model, CLI, and fixtures.
- CTO direction that LangGraph tools must be created explicitly, not through decorators.

## Governing Inputs

- Conversation Knowledge Base is the product center.
- Ingestion and analysis are separate workflows.
- CLI is an adapter over the Query/Automation Interface.
- User identity for coaching analysis is supplied at workflow runtime with optional context.
- All unprocessed conversations should be processed, with more recent conversations prioritized.
- Source artifacts must not be stored under the repository by default.
- Local data must use platform-appropriate application data locations.
- SQLite is acceptable but not mandatory if implementation discovers a better local database alternative.
- JSON may be the initial analysis output format, but outputs are not constrained to JSON only.
- Fathom summaries are not required workflow inputs.
- LangGraph tool creation must be explicit; do not use decorator-based tool definition.
- The first implementation supports only the locally installed Ollama model `gemma4:e2b`.
- Automatic retry is not part of the first implementation; failures should fail loudly while preserving local failure state.
- Local deletion of local conversation records and artifacts must be available through the CLI adapter.

## Supporting Context

The existing package already provides a synchronous Fathom HTTP client and mapper for meetings and transcripts. The first implementation should reuse those boundaries where practical, while adding local persistence, artifact management, workflow orchestration, and analysis.

## Technical Decomposition

### Conversation Knowledge Base

The Conversation Knowledge Base stores queryable local records and processing state. The baseline implementation should use SQLite because it is local, inspectable, widely available, and sufficient for the first query requirements. The design permits a different local database if the implementation engineer documents a clear advantage and preserves the same architectural responsibilities.

Minimum conceptual records:

| Record | Purpose |
| --- | --- |
| Conversation | Fathom meeting identity, recording ID, title, start/end time, duration, processing status, source provider. |
| Participant | Person identity observed from recorded-by, invitees, transcript speakers, or analysis ownership. |
| ConversationParticipant | Participant role within a conversation, such as recorded_by, invitee, speaker, action_owner. |
| ArtifactReference | Links local files to conversations or analysis runs. |
| AnalysisRun | One rerunnable analysis execution, including provider/model metadata, prompt or analysis version, runtime user identity/context, status, timestamps, and errors. |
| AnalysisFinding | Queryable structured output from analysis runs, such as conversation type, action item, coaching observation, or people-dynamics observation. |
| EvidenceReference | Transcript evidence associated with findings, including speaker, timestamp or offset, and excerpt when present. |

The knowledge base should expose operations for:

- Upserting conversation metadata.
- Checking whether a conversation has completed ingestion and processing.
- Finding conversations requiring ingestion or analysis.
- Recording artifact references.
- Creating and completing analysis runs.
- Recording structured findings and evidence references.
- Querying conversations, analysis runs, findings, and artifact locations for CLI display.

### Artifact Store

The Artifact Store owns local files and path resolution. It stores raw source payloads and human-readable files outside the repository.

Baseline data root should follow platform conventions:

- macOS: application support data location, such as `~/Library/Application Support/fathom-play/`.
- Linux: XDG data location, such as `${XDG_DATA_HOME:-~/.local/share}/fathom-play/`.
- Windows, if supported later: the standard per-user application data location.

The exact path-resolution mechanism is an implementation detail, but it must be centralized behind Artifact Store. Repository-local `data/` must not be the default.

Recommended artifact layout under the application data root:

```text
fathom-play/
  conversations.db
  artifacts/
    fathom/
      recordings/
        {recording_id}/
          meeting.json
          transcript.json
          transcript.md
          analyses/
            {analysis_run_id}/
              conversation_type.json
              action_items.json
              coaching.json
              people_dynamics.json
              analysis_context.json
```

The layout is recommended, not a hard-coded architectural constraint. Technical implementation may adjust names if the knowledge base consistently records artifact references.

### Source Importer

The Source Importer is a light abstraction over the existing Fathom API integration.

Responsibilities:

- List visible Fathom conversations.
- Page through available results so the ingestion workflow can process all unprocessed conversations.
- Prioritize more recent conversations before older conversations.
- Fetch transcript source by recording ID.
- Convert source payloads through existing mapper/domain boundaries where useful.
- Send source metadata and artifacts to the knowledge base and artifact store through their interfaces.

The Source Importer must not fetch or depend on Fathom summaries for this workflow.

### Analysis Enricher

The Analysis Enricher runs transcript-centered analyses and writes results back through the knowledge base and artifact store.

Required analysis perspectives:

- Conversation classification.
- Action item extraction for all participants where possible.
- Meeting coaching review using runtime user identity.
- People dynamics review with careful, evidence-grounded language.

Each analysis output should include:

- Analysis type.
- Analysis run ID.
- Recording ID.
- Model/provider metadata.
- Runtime user identity and optional context when relevant.
- Structured findings.
- Evidence references with speaker, timestamp/offset, and excerpt when available.
- Confidence or uncertainty where meaningful.

JSON is the recommended first output representation because it is easy to persist, inspect, and query. Markdown or other human-readable renderings may be added without changing the architecture.

### Model Adapter

The Model Adapter returns configured LLM connections and model metadata.

Initial provider expectation:

- Ollama with the locally installed `gemma4:e2b` model.

Deferred future provider path:

- AWS Bedrock or other non-local model providers.

The adapter should expose provider-agnostic behavior to Analysis Enricher. Provider-specific settings, credentials, regions, model IDs, and transport behavior must not leak into analysis prompt or workflow code.

### Workflow Runner

The Workflow Runner is the LangGraph execution boundary. It owns named workflows and workflow state transitions, not durable conversation records.

Required workflows:

- `ingest`: discover and import unprocessed conversations.
- `analyze`: run analysis for selected local conversations.
- `query`: read local records and produce displayable results through the Query/Automation Interface.
- `delete-local`: delete local conversation records and artifacts without affecting Fathom.

The workflow design should preserve resumability at the durable-state level: failed or interrupted work must leave enough status and artifact information for a later run to retry safely.

### Query/Automation Interface And CLI Adapter

The Query/Automation Interface exposes stable operations for local usage and future automation. The CLI is the initial concrete adapter over this interface, not the full interface surface. Future adapters, such as scheduled jobs or other local automation triggers, should use the same workflow and query operations rather than bypassing the interface.

Query/Automation Interface responsibilities:

- Trigger ingestion.
- Trigger analysis.
- Query local records.
- Trigger local deletion of conversation records and artifacts.
- Pass runtime metadata to workflows.

CLI adapter responsibilities:

- Collect username for analysis workflows.
- Collect optional analysis context.
- Call Query/Automation Interface operations.
- Print basic local results to standard output when requested.
- Provide an operator command path for local deletion.

CLI must not own source API calls, database operations, artifact path policy, LLM construction, or LangGraph internals.

## Interfaces And Dependencies

### Knowledge Base Interface

Expected operations:

- `upsert_conversation(metadata)`
- `get_conversation(recording_id)`
- `list_unprocessed_conversations(order=recent_first)`
- `mark_ingestion_started(recording_id)`
- `mark_ingestion_completed(recording_id)`
- `mark_ingestion_failed(recording_id, error)`
- `create_analysis_run(recording_id, runtime_context, model_metadata, analysis_version)`
- `record_analysis_outputs(analysis_run_id, findings, artifact_refs)`
- `mark_analysis_completed(analysis_run_id)`
- `mark_analysis_failed(analysis_run_id, error)`
- `query_conversations(filters)`
- `query_analysis_runs(recording_id)`

Names are illustrative and may change during implementation. The interface intent is required.

### Artifact Store Interface

Expected operations:

- Resolve application data root.
- Resolve conversation artifact directory.
- Write raw meeting metadata.
- Write raw transcript payload.
- Write rendered transcript.
- Write analysis artifact.
- Read transcript artifact.
- Return artifact references suitable for knowledge-base storage.

### Source Importer Interface

Expected operations:

- Discover conversations visible to Fathom credentials.
- Fetch transcript for recording ID.
- Normalize source metadata into the local conversation shape.

### Analysis Enricher Interface

Expected operations:

- Run conversation classification.
- Run action-item extraction.
- Run coaching review.
- Run people-dynamics review.
- Return structured findings plus artifact payloads.

### Model Adapter Interface

Expected operations:

- Resolve model provider configuration.
- Return a LangChain-compatible chat model.
- Return provider/model metadata for analysis-run records.

### Workflow Runner Interface

Expected operations:

- Run ingestion workflow.
- Run analysis workflow for a selection of conversations.
- Run query workflow or query command path.
- Report workflow outcomes.

## LangGraph Tool Design

LangGraph tools must be created explicitly. The implementation must avoid decorator-based tool creation for this system.

Rationale:

- Tool boundaries are architectural interfaces, not incidental function annotations.
- Explicit tool construction makes name, description, input contract, output contract, ownership, and dependency injection visible.
- Decorator-based registration can obscure responsibility boundaries and make ordinary helper functions appear to have workflow-level semantics.

Technical design expectations:

- Define tool contracts as explicit objects or factory-created tool instances.
- Keep tool ownership aligned to components: Source Importer tools, Knowledge Base tools, Artifact Store tools, and Analysis tools should be created from their owning component boundary.
- Do not decorate arbitrary functions to turn them into tools.
- Tool descriptions should identify side effects, especially database writes, artifact writes, and external Fathom API calls.
- Workflow nodes should depend on explicit tool sets or component interfaces, not global tool registration.

## Data Handling Design

### Processing State

Conversation processing should distinguish at least:

- Discovered.
- Ingestion started.
- Ingestion completed.
- Ingestion failed.
- Analysis pending.
- Analysis started.
- Analysis completed.
- Analysis failed.

The exact state model may be normalized differently, but it must support retrying incomplete work and identifying fully processed conversations.

### Analysis Runs

Each analysis run is immutable after completion except for explicitly supported repair or annotation operations. Reruns create new analysis runs rather than overwriting prior results.

Analysis run records should include:

- Recording ID.
- Run status.
- Runtime username.
- Optional runtime context.
- Provider and model metadata.
- Analysis/prompt version.
- Started and completed timestamps.
- Error information when failed.
- Artifact references.

### Evidence

Evidence references must retain enough information to verify findings against transcript artifacts:

- Speaker identity when available.
- Timestamp or offset when available.
- Excerpt when relevant.
- Linkage to analysis finding and analysis run.

Verbatim transcript excerpts are allowed in local artifacts and database records where useful.

### Transcript Rendering

The human-readable transcript should preserve speaker, timestamp, and text. It should be deterministic so analysis evidence can be audited by the operator.

## Workflow Behavior

### Ingestion Workflow

Input:

- Optional source discovery filters if supported.

Behavior:

- Discover visible Fathom conversations.
- Sort unprocessed conversations with newer conversations first.
- For each unprocessed conversation, record ingestion start.
- Fetch transcript source.
- Store raw metadata and transcript artifacts.
- Render human-readable transcript.
- Update knowledge-base records and artifact references.
- Mark ingestion complete or failed.

Failure behavior:

- Failed conversations retain enough error context to retry.
- A failed conversation is not treated as fully processed.
- Later runs continue processing other eligible conversations where possible.

### Analysis Workflow

Input:

- Conversation selection.
- Runtime username.
- Optional runtime context.
- Optional model/provider override only in future implementations that support providers beyond local `gemma4:e2b`.

Behavior:

- Select local conversations eligible for analysis.
- Create a distinct analysis run.
- Load transcript and metadata from local storage.
- Run required analysis perspectives.
- Persist structured outputs and optional human-readable artifacts.
- Record findings and evidence references in the knowledge base where practical.
- Mark analysis run complete or failed.

Failure behavior:

- Failed analysis runs remain visible.
- Rerun creates a new analysis run unless implementation explicitly supports repair.

### Query Workflow

Input:

- Query filters or request for recent/local status.

Behavior:

- Read from the knowledge base.
- Resolve artifact references only when display requires artifact content.
- Print basic results through CLI stdout when requested.

### Local Deletion Workflow

Input:

- Conversation selection.

Behavior:

- Delete local analysis artifacts, transcript artifacts, and source artifacts associated with the selected conversation.
- Delete or tombstone local knowledge-base records according to the implementation's consistency strategy.
- Do not call Fathom or attempt to delete remote source data.
- Report deleted local records and artifacts through CLI output.

Failure behavior:

- Fail loudly if any local deletion step cannot complete.
- Preserve enough error context for the operator to inspect or retry cleanup.

## Operational Considerations

### Local Data Location

Local database and artifacts must be stored in user application data locations. Configuration files, if any, should use platform configuration locations separately from data.

First-version data root precedence:

1. Explicit operator override, if the implementation provides one through CLI or environment configuration.
2. Platform-appropriate user application data directory.
3. Documented fallback under the user's home directory only if the platform directory cannot be resolved.

Repository-local storage must not be used as the default fallback.

### Idempotency

Ingestion must be safe to rerun. Completed conversations are skipped unless a refresh mode is introduced. Failed or incomplete conversations remain eligible.

### Rate Limits And Retries

The first implementation may use simple sequential processing. Automatic retry is not included initially. Source-import failures must fail loudly, be recorded clearly, and leave the affected conversation eligible for a later operator-initiated run.

### Observability

CLI output should report:

- Number of discovered conversations.
- Number skipped as already processed.
- Number ingested.
- Number failed.
- Analysis run IDs and statuses.

Detailed logs may be added during implementation without changing architecture.

### Privacy And Locality

Transcript artifacts and evidence excerpts are stored locally. The design assumes local operator control over the machine and does not include multi-user access controls.

### Provider Configuration

The first implementation uses Ollama with `gemma4:e2b`. The Model Adapter must report provider and model identity into analysis-run metadata. Additional provider selection is deferred.

## Traceability

| Requirement / Decision | Technical Design Coverage |
| --- | --- |
| FCR-001 discover conversations | Source Importer and ingestion workflow. |
| FCR-002 processing eligibility | Knowledge Base processing state and ingestion workflow. |
| FCR-003 download transcript | Source Importer and Artifact Store. |
| FCR-004 source artifacts | Artifact Store layout and references. |
| FCR-005 local records | Conversation Knowledge Base records. |
| FCR-006 conversation type | Analysis Enricher classification. |
| FCR-007 action items | Analysis Enricher all-participant action extraction. |
| FCR-008 coaching review | Analysis Enricher with runtime username/context. |
| FCR-009 people dynamics | Analysis Enricher evidence-grounded findings. |
| FCR-010 persist outputs | Artifact Store, Knowledge Base, AnalysisRun records. |
| FCR-011 rerunnable analysis | Immutable analysis runs and rerun behavior. |
| FCR-012 configurable LLM | Model Adapter. |
| FCR-013 query/review | Knowledge Base and Query/Automation Interface. |
| FCR-014 runtime context | CLI adapter, Workflow Runner, AnalysisRun records. |
| Explicit tool creation | LangGraph Tool Design section. |
| CTO decision: fail loudly rather than retry | Rate Limits And Retries and workflow failure behavior. |
| CTO decision: local deletion from CLI | Local Deletion Workflow and Query/Automation Interface. |
| CTO decision: `gemma4:e2b` only initially | Model Adapter and Provider Configuration. |

## Decisions Made

- Use SQLite as the baseline local database for the first design, while preserving implementation discretion to choose a better local database if justified.
- Store local data under platform-appropriate application data directories, not under the repository.
- Store artifacts separately from queryable records and record artifact references in the knowledge base.
- Keep ingestion and analysis as separate workflows.
- Process all unprocessed conversations with newer conversations first.
- Use JSON as the initial structured analysis artifact format, without constraining future output formats to JSON only.
- Treat each analysis rerun as a distinct analysis run.
- Create LangGraph tools explicitly rather than using decorators.
- Fail loudly rather than automatically retrying in the first implementation.
- Provide local deletion from the CLI adapter.
- Support only the locally installed Ollama `gemma4:e2b` model in the first implementation.

## Decisions Explicitly Deferred

- Exact database schema, indexes, and migrations.
- Exact app data path resolution library or helper.
- Exact artifact file names and final directory layout.
- Exact prompt text and prompt versioning scheme.
- Exact structured output schema for each analysis perspective.
- Exact throttling, pagination, and failure-reporting mechanics.
- Exact CLI command and option names.
- Exact provider configuration names.
- Future model providers beyond local Ollama `gemma4:e2b`.
- Exact local deletion consistency strategy: hard delete versus tombstone.

## Open Questions

No technical-design-level open questions remain.

## Questions For CTO

No technical-design-level CTO questions remain.

## Decisions Requested

No technical-design-level decisions remain requested.

## Recommended Next Step

Architect review using `review-technical-design-as-architect`, followed by senior implementation engineer review using `review-technical-design-as-implementation-engineer`.

## Approval Status

approved

## Architect Review

### Findings

No blocking findings.

- The technical design preserves the approved architecture and component model. Conversation Knowledge Base remains the local product center, Artifact Store remains separate, Source Importer owns Fathom access, Analysis Enricher owns analysis behavior, Model Adapter owns provider access, Workflow Runner owns LangGraph orchestration, and CLI remains an adapter.
- The design respects CTO decisions: separate ingestion and analysis workflows, platform-appropriate data locations, all unprocessed conversations processed newest-first, SQLite as acceptable but not mandatory, JSON as initial but not exclusive output, and explicit LangGraph tool creation rather than decorator-based tool definition.
- The design stays mostly at technical-design level. Conceptual records, interface operations, workflow behavior, and operational expectations are appropriate; exact schema, prompt text, graph topology, and CLI command names remain deferred.
- The Query/Automation Interface clarification has been made: it is now described as the stable boundary, with CLI as the first concrete adapter and future adapters expected to reuse the same workflow/query operations.

### Required Changes

No architect-level changes remain required.

### Questions

- No architect-level questions remain beyond the CTO decisions already listed in the technical design.

### Review Disposition

Accepted. The design is architecturally faithful and can proceed to implementation-engineer review.

## Senior Implementation Engineer Review

### Findings

No blocking findings.

- The design is buildable. It defines enough subsystem behavior, conceptual records, interfaces, workflow behavior, artifact handling, and operational expectations to support implementation planning without writing production code.
- The design leaves appropriate implementation discretion. Exact schema, migrations, path-resolution helper, prompt text, structured output schemas, graph topology, retry mechanics, and CLI names remain deferred.
- The explicit LangGraph tool guidance is implementable and helpful. It gives the implementation engineer a concrete boundary rule without prescribing code structure.
- The earlier implementation-readiness gap around local data path precedence has been resolved in the Local Data Location section.
- The CTO decisions that were open during review are now resolved: fail loudly rather than retry, include local deletion from CLI, and defer all models other than local `gemma4:e2b`.

### Required Changes

No implementation-engineering changes remain required.

### Questions

- No implementation-engineering questions remain.

### Review Disposition

Accepted. The design is complete enough for development checklist creation.

## CTO Review

### CTO Decisions

- Fail loudly for now rather than automatically retrying.
- Local deletion from the CLI should be available.
- No support yet for anything other than the locally installed Ollama `gemma4:e2b` model.

The CTO decisions have been incorporated into the technical design.

CTO approved this technical design as governing input for development checklist creation and implementation on 2026-05-01.

## Sign-Off

### Author

- Signer: Codex
- Signer Type: agent
- Role: Technical design author
- Review Perspective: systems engineering technical design
- Disposition: submitted-for-review
- Summary Notes: Initial technical design for the approved local Fathom conversation agent architecture.
- Date: 2026-05-01

### Review Entries

- Signer: Codex
- Signer Type: agent
- Role: Architect reviewer
- Review Perspective: architecture fidelity and boundary preservation
- Disposition: accepted
- Summary Notes: Technical design preserves approved architecture. Query/Automation Interface boundary clarification is incorporated.
- Date: 2026-05-01

- Signer: Codex
- Signer Type: agent
- Role: Senior Implementation Engineer reviewer
- Review Perspective: buildability, implementation completeness, and engineering discretion
- Disposition: accepted
- Summary Notes: Design is buildable and leaves healthy implementation discretion. Local data path precedence is clarified.
- Date: 2026-05-01

### CTO Sign-Off

- Signer: CTO (Human)
- Signer Type: human
- Status: approved
- Date: 2026-05-01

### Workflow Status

- Current Status: approved
