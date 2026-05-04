# Fathom Conversation Agent Development Checklist

## Purpose

Translate the approved technical design into an ordered implementation checklist with verification and completion criteria.

## Scope

This checklist covers the first local implementation of the Fathom conversation agent:

- Platform-appropriate local data root.
- SQLite baseline Conversation Knowledge Base.
- Artifact Store outside the repository.
- Fathom Source Importer.
- Separate ingestion, analysis, query, and local deletion workflows.
- Explicit LangGraph tool construction.
- Ollama `gemma4:e2b` model usage.
- CLI adapter for triggering workflows and displaying basic results.

This checklist does not expand scope to advanced search, embeddings, hosted deployment, non-local model providers, or production UI.

## Inputs Consulted

- Approved technical design in `docs/conversation_agent_technical_design.md`.
- Approved architecture in `docs/conversation_agent_architecture.md`.
- Approved componentization in `docs/conversation_agent_componentization.md`.
- Approved requirements in `docs/conversation_agent_requirements.md`.
- Existing source code under `src/fathom_play`.
- Existing tests and fixtures under `tests/`.

## Governing Inputs

- Technical design is CTO-approved as of 2026-05-01.
- Ingestion and analysis are separate workflows.
- All unprocessed conversations are processed, newer first.
- Fail loudly rather than automatic retry.
- Local deletion from CLI is required.
- Initial model support is only local Ollama `gemma4:e2b`.
- LangGraph tools must be created explicitly, not through decorators.
- Local data must use platform-appropriate application data locations and must not default to repository-local storage.

## Supporting Context

The existing Fathom client and mapper provide a working base for listing meetings and fetching transcripts. Existing CLI commands are exploratory and should remain subordinate to the new Query/Automation Interface and workflow boundaries.

## Implementation Phases

### Phase 1: Project Foundation

- [ ] Confirm runtime dependencies are present in `pyproject.toml`: `langchain`, `langchain-ollama`, `langgraph`, and existing CLI/runtime dependencies.
- [ ] Confirm no lockfile is required for early development mode unless the CTO later asks to lock dependencies.
- [ ] Define package/module organization for the approved components without collapsing boundaries.
- [ ] Add a shared error/result vocabulary for workflow-visible failures without replacing existing `FathomApiError`.
- [ ] Add test fixture strategy for local database, artifact paths, and Fathom transcript payloads.

Verification:

- [ ] Existing tests still pass.
- [ ] New component modules import without creating Fathom, Ollama, or filesystem side effects.
- [ ] No implementation writes local data under the repository by default.

### Phase 2: Local Data Root And Artifact Store

- [ ] Implement centralized application data root resolution.
- [ ] Support explicit operator override if selected during implementation.
- [ ] Resolve macOS application support path.
- [ ] Resolve Linux XDG data path.
- [ ] Add documented home-directory fallback only when platform data path cannot be resolved.
- [ ] Implement Artifact Store operations for conversation directories and artifact references.
- [ ] Implement writing raw meeting metadata.
- [ ] Implement writing raw transcript payloads.
- [ ] Implement deterministic human-readable transcript rendering.
- [ ] Implement writing analysis artifacts.
- [ ] Implement artifact lookup for CLI display and analysis input.

Verification:

- [ ] Unit tests prove repository-local `data/` is not the default.
- [ ] Unit tests cover platform path precedence with temporary paths.
- [ ] Artifact writes are deterministic and return stable artifact references.
- [ ] Transcript rendering preserves speaker, timestamp, and text.

### Phase 3: Conversation Knowledge Base

- [ ] Implement SQLite baseline database initialization.
- [ ] Add migrations or initialization strategy appropriate for local development.
- [ ] Implement conceptual records from the design: conversations, participants, conversation participants, artifact references, analysis runs, findings, and evidence references.
- [ ] Implement upsert of conversation metadata.
- [ ] Implement processing state transitions for ingestion and analysis.
- [ ] Implement query for unprocessed conversations ordered newest first.
- [ ] Implement analysis run creation and completion/failure recording.
- [ ] Implement finding and evidence recording.
- [ ] Implement basic query operations for CLI display.

Verification:

- [ ] Unit tests cover idempotent conversation upsert.
- [ ] Unit tests cover completed conversations being skipped.
- [ ] Unit tests cover failed or incomplete conversations remaining eligible.
- [ ] Unit tests cover multiple analysis runs for one recording.
- [ ] Unit tests cover artifact references linked to conversations and analysis runs.

### Phase 4: Source Importer

- [ ] Wrap existing Fathom client behind Source Importer.
- [ ] Implement discovery of visible Fathom conversations.
- [ ] Implement pagination handling so available conversations are not silently omitted.
- [ ] Prioritize unprocessed conversations newest first.
- [ ] Fetch transcript by recording ID.
- [ ] Normalize Fathom metadata into local conversation metadata.
- [ ] Preserve raw source payloads through Artifact Store.
- [ ] Avoid fetching or depending on Fathom summaries.
- [ ] Fail loudly on source errors while recording failure state.

Verification:

- [ ] Unit tests use fixtures to map Fathom meetings and transcripts into local records.
- [ ] Tests verify Fathom summaries are not required or fetched by the ingestion workflow.
- [ ] Tests cover pagination behavior or pagination handoff.
- [ ] Tests cover source failure state being recorded and later eligible for retry by rerun.

### Phase 5: Model Adapter

- [ ] Implement Model Adapter for Ollama.
- [ ] Configure initial model as `gemma4:e2b`.
- [ ] Record provider/model metadata for analysis runs.
- [ ] Ensure non-local providers are not exposed in the first implementation.
- [ ] Provide a clear failure when `gemma4:e2b` is unavailable.

Verification:

- [ ] Unit tests or integration checks verify model configuration resolves to `gemma4:e2b`.
- [ ] Analysis run metadata records provider and model.
- [ ] Missing model configuration fails clearly.

### Phase 6: Analysis Enricher

- [ ] Define structured output contracts for conversation classification.
- [ ] Define structured output contracts for all-participant action extraction.
- [ ] Define structured output contracts for meeting coaching review.
- [ ] Define structured output contracts for people dynamics review.
- [ ] Include evidence references with speaker, timestamp or offset, and excerpt where available.
- [ ] Include confidence or uncertainty where meaningful.
- [ ] Include runtime username and optional context in analysis run context.
- [ ] Persist JSON analysis artifacts initially.
- [ ] Record queryable findings and evidence in the knowledge base where practical.
- [ ] Ensure reruns create distinct analysis runs.

Verification:

- [ ] Unit tests cover output parsing/validation from representative model-shaped responses.
- [ ] Tests cover evidence references linked to findings.
- [ ] Tests cover no-action-item outcomes.
- [ ] Tests cover multiple analysis runs without overwrite.
- [ ] Tests verify people-dynamics findings require careful, qualified language fields.

### Phase 7: Explicit LangGraph Tools And Workflow Runner

- [ ] Define explicit tool instances or factories for component-owned capabilities.
- [ ] Ensure no decorator-based LangGraph tool definitions are used.
- [ ] Implement `ingest` workflow.
- [ ] Implement `analyze` workflow.
- [ ] Implement `query` workflow or query command path.
- [ ] Implement `delete-local` workflow.
- [ ] Keep workflow state separate from durable knowledge-base state.
- [ ] Ensure workflow nodes use component interfaces or explicit tools, not global registration.
- [ ] Ensure side-effecting tools describe database writes, artifact writes, or Fathom calls.

Verification:

- [ ] Static search confirms decorator-based tool creation is not used.
- [ ] Workflow tests cover successful ingestion.
- [ ] Workflow tests cover source failure and loud failure behavior.
- [ ] Workflow tests cover successful analysis run creation.
- [ ] Workflow tests cover local deletion behavior.
- [ ] Workflow tests confirm Fathom is not called during analysis of existing local transcripts.

### Phase 8: Query/Automation Interface And CLI Adapter

- [ ] Implement Query/Automation Interface operations for ingestion, analysis, query, and local deletion.
- [ ] Keep CLI as an adapter over the interface.
- [ ] Add CLI command path for ingestion.
- [ ] Add CLI command path for analysis with required username.
- [ ] Add CLI option or argument for optional analysis context.
- [ ] Add CLI command path for local query/status display.
- [ ] Add CLI command path for local deletion.
- [ ] Ensure CLI prints basic results to standard output when requested.
- [ ] Ensure CLI does not call Fathom, database, artifact store, LangGraph, or LLM provider internals directly except through approved interface boundaries.

Verification:

- [ ] CLI tests cover username required for analysis.
- [ ] CLI tests cover optional context passed to workflow.
- [ ] CLI tests cover query/status output.
- [ ] CLI tests cover local deletion command path.
- [ ] CLI failure output is clear for source, model, and local storage errors.

### Phase 9: End-To-End Verification

- [ ] Run full test suite.
- [ ] Run ingestion against fixture-backed or mocked Fathom source.
- [ ] Run analysis against a local transcript using `gemma4:e2b` when Ollama is available.
- [ ] Verify local artifacts are written under application data root.
- [ ] Verify query output can show conversation records and analysis runs.
- [ ] Verify delete-local removes or tombstones local records and artifacts according to the implemented strategy.
- [ ] Verify rerunning ingestion skips completed conversations and leaves failed/incomplete conversations eligible.
- [ ] Verify rerunning analysis creates a new analysis run.

Verification:

- [ ] Tests pass without requiring network or a running Ollama service unless explicitly marked integration.
- [ ] Integration checks are documented separately from unit tests.
- [ ] Manual smoke command sequence is documented.

## Cross-Phase Verification Checklist

- [ ] No Fathom summaries are required by ingestion, analysis, or query workflows.
- [ ] No repository-local data root is used by default.
- [ ] No decorator-based LangGraph tool creation is used.
- [ ] `gemma4:e2b` is the only supported first implementation model.
- [ ] Automatic retry is not implemented initially.
- [ ] Failures fail loudly and preserve useful error state.
- [ ] Local deletion is available through the CLI.
- [ ] Analysis outputs preserve evidence references.
- [ ] Analysis reruns do not overwrite prior analysis runs.
- [ ] CLI remains an adapter over Query/Automation Interface.

## Completion Criteria

- [ ] All implementation phases are complete.
- [ ] All verification tasks pass.
- [ ] Existing tests still pass.
- [ ] New tests cover knowledge base, artifact store, source importer, model adapter, analysis enricher, workflows, and CLI adapter.
- [ ] Manual smoke test demonstrates ingestion, query, analysis, rerun analysis, and local deletion.
- [ ] Documentation reflects actual first implementation behavior where it differs from recommended layout details.

## Decisions Made

- Build storage foundation before Source Importer and workflows.
- Build ingestion before analysis so analysis can operate on local transcript artifacts.
- Build explicit tool creation before final workflow tests.
- Build CLI last so it remains an adapter over already-tested interfaces.
- Treat local deletion as part of the first implementation, after storage and query paths exist.

## Decisions Explicitly Deferred

- Advanced search, embeddings, and retrieval.
- Hosted or multi-user operation.
- Non-local model providers.
- Automatic retry.
- Final prompt wording.
- Production UI.

## Open Questions

No checklist-level open questions remain.

## Questions For CTO

No checklist-level CTO questions remain.

## Decisions Requested

No checklist-level decisions requested.

## Recommended Next Step

Begin implementation from Phase 1, preserving the approved component boundaries and verifying each phase before moving to the next.

## Approval Status

approved

## CTO Review

CTO approved this development checklist as governing input for implementation on 2026-05-01.

## Sign-Off

### Author

- Signer: Codex
- Signer Type: agent
- Role: Development checklist author
- Review Perspective: implementation planning
- Disposition: submitted-for-review
- Summary Notes: Development checklist for the approved Fathom conversation agent technical design.
- Date: 2026-05-01

### Review Entries

No review entries yet.

### CTO Sign-Off

- Signer: CTO (Human)
- Signer Type: human
- Status: approved
- Date: 2026-05-01

### Workflow Status

- Current Status: approved
