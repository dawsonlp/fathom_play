# Fathom Conversation Agent Architecture

## Purpose

Define the architecture for the local Fathom conversation agent using the approved requirements and approved system componentization. This document establishes system boundaries, component responsibilities, high-level interfaces, and architectural constraints for downstream technical design.

## Scope

This architecture covers local ingestion of Fathom conversation transcripts, preservation of source artifacts, maintenance of a query-oriented local conversation database, rerunnable analysis, LangGraph workflow execution, configurable LLM access, and CLI-based operator access.

This architecture does not define concrete database schema, exact filesystem layout, prompt templates, graph node implementation, CLI command names, or implementation task sequencing.

## Inputs Consulted

- Approved requirements in `docs/conversation_agent_requirements.md`.
- Approved componentization in `docs/conversation_agent_componentization.md`.
- Senior systems engineer review recorded in `docs/conversation_agent_componentization.md`.
- Existing meeting-data design context in `docs/design_decisions.md`.
- Existing Fathom client, mapper, domain objects, CLI, and fixtures under `src/` and `tests/`.

## Governing Inputs

- Requirements are CTO-approved as governing input for architecture and downstream technical design.
- Componentization is CTO-approved as governing input for architecture and downstream technical design.
- The approved component model is Model 3: Local Knowledge Base Components.
- The local Conversation Knowledge Base is the product center.
- Ingestion and analysis are separate workflows.
- The initial automation interface is CLI-based, but CLI must remain an adapter rather than being embedded in the automation boundary.
- Source importing starts as a light abstraction over the Fathom API and may evolve when additional sources exist.
- Action extraction covers all participants and associates actions with participants where possible.
- Verbatim transcript evidence excerpts are allowed in local analysis artifacts.
- User identity for coaching analysis is supplied by the CLI at workflow runtime with optional context.
- Fathom summaries are not part of the required workflow.

## Supporting Context

The existing codebase already separates Fathom HTTP access, provider-specific mapping, provider-neutral domain objects, and CLI presentation. That structure is valid supporting context for the new architecture, but the new governing scope expands beyond API exploration into a local conversation knowledge base and reusable workflow automation.

`docs/design_decisions.md` mentions Fathom summaries as an existing API capability. That does not govern this workflow. The conversation agent architecture must not require Fathom summaries.

## Decisions Made

- The system architecture is organized around a local Conversation Knowledge Base.
- Source artifacts are owned by a separate Artifact Store rather than embedded directly into the knowledge base.
- Fathom access is isolated behind a Source Importer.
- Transcript analysis is isolated behind an Analysis Enricher.
- LLM provider selection is isolated behind a Model Adapter.
- LangGraph execution is isolated behind a Workflow Runner.
- Operator and automation entrypoints are isolated behind a Query/Automation Interface.
- The first operator adapter is CLI, and it can display basic local query results to standard output.
- Runtime workflow context includes the CLI-supplied user identity and optional contextual guidance.
- Advanced search, embeddings, and retrieval workflows are deferred.
- SQLite is acceptable but not required; the implementation engineer may choose a better local database alternative during technical design.
- Local data must use platform-appropriate application data locations rather than repository-local storage.
- All unprocessed conversations should be processed, with more recent conversations prioritized over older conversations.
- JSON may be the initial analysis output format, but the architecture does not constrain analysis outputs to JSON only.

## Approved Component Model

The approved model is Local Knowledge Base Components:

| Component | Architectural Responsibility | State/Data Ownership |
| --- | --- | --- |
| Conversation Knowledge Base | Authoritative local record for conversations, processing status, analysis runs, queryable metadata, and artifact references. | Owns local database records. |
| Source Importer | Imports conversation metadata and transcripts from Fathom into the local system. | Does not own durable records; writes through the knowledge base and artifact store. |
| Artifact Store | Stores raw source files, human-readable transcript files, analysis files, and other local artifacts. | Owns local file artifacts and path resolution. |
| Analysis Enricher | Produces evidence-grounded analysis findings from transcripts and runtime context. | Does not own source records; enriches knowledge-base records and writes analysis artifacts through system boundaries. |
| Model Adapter | Provides configured LLM connections and provider metadata. | Does not own conversation state. |
| Workflow Runner | Runs named LangGraph workflows and coordinates state transitions across components. | Owns workflow execution state only. |
| Query/Automation Interface | Exposes operator and future automation operations without owning business capabilities. | Does not own durable records. |

## Architecture Structure

The architecture is local-first and layered around durable local knowledge.

```text
Operator / Future Automation
    |
    v
Query/Automation Interface
    |
    v
Workflow Runner
    |
    +--> Source Importer ---------> Fathom API
    |
    +--> Analysis Enricher -------> Model Adapter -------> Configured LLM
    |
    +--> Conversation Knowledge Base
    |
    +--> Artifact Store
```

The Conversation Knowledge Base is the authoritative local record. It records conversation identity, processing state, analysis-run identity, queryable metadata, and references to artifacts. It should start simple, but it must not be shaped only around one ingestion workflow.

The Artifact Store preserves local files. Raw source payloads, rendered transcripts, and analysis artifacts remain inspectable outside the database. The knowledge base records references to these artifacts.

The Source Importer imports Fathom meeting metadata and transcripts. It does not consume Fathom summaries for this workflow. It is allowed to be Fathom-shaped initially, but the architecture keeps the boundary clear so future source providers can be introduced without moving source API concerns into the knowledge base or analysis components.

The Analysis Enricher reads transcript source through artifact and knowledge-base interfaces, receives runtime context from the workflow, obtains an LLM through the Model Adapter, and produces structured, evidence-grounded findings. Analysis runs are separate from ingestion and can be rerun without redownloading transcripts by default.

The Workflow Runner is the LangGraph boundary. It composes components into named workflows, records workflow outcomes, and coordinates success/failure transitions. It does not own provider API calls, database records, artifact layout, prompt behavior, or model-provider construction.

The Query/Automation Interface exposes operator and future automation operations. The initial concrete adapter is CLI. The CLI must pass runtime user identity and optional context into workflows and may print basic local query results to standard output.

## Boundary And Interface Definitions

### Conversation Knowledge Base

Offers:

- Record or update conversation metadata.
- Query conversation records by available local metadata.
- Record processing state for ingestion and analysis workflows.
- Record analysis-run metadata and status.
- Associate artifact references with conversations and analysis runs.
- Provide records to workflow and query consumers without requiring source re-fetch.

Consumes:

- Imported metadata from Source Importer through Workflow Runner.
- Artifact references from Artifact Store.
- Analysis-run outcomes from Analysis Enricher through Workflow Runner.

Boundary constraints:

- Does not call Fathom.
- Does not construct LLMs.
- Does not own filesystem artifact bytes.
- Does not embed workflow orchestration logic.

### Source Importer

Offers:

- Discover available source conversations within a workflow-selected scope.
- Import source conversation metadata.
- Import transcript source for a recording.

Consumes:

- Fathom API access through the existing client boundary or its architectural successor.
- Artifact Store for source artifact preservation.
- Conversation Knowledge Base for local record updates.

Boundary constraints:

- Does not perform LLM analysis.
- Does not decide long-term query schema.
- Does not consume or require Fathom summaries.

### Artifact Store

Offers:

- Store and retrieve source artifacts.
- Store and retrieve human-readable transcript artifacts.
- Store and retrieve analysis artifacts.
- Resolve artifact references for knowledge-base records and workflow consumers.

Consumes:

- Source payloads from Source Importer.
- Analysis outputs from Analysis Enricher through Workflow Runner.

Boundary constraints:

- Does not decide processing eligibility.
- Does not own queryable conversation metadata beyond artifact references.
- Does not call Fathom or LLM providers.

### Analysis Enricher

Offers:

- Classify conversation type.
- Extract action items for all participants where possible.
- Produce meeting coaching review using CLI-supplied user identity.
- Produce people-dynamics review using careful, evidence-grounded language.
- Produce analysis outputs tied to transcript evidence and analysis-run context.

Consumes:

- Transcript artifacts and conversation metadata.
- Runtime user identity and optional context.
- LLM connections from Model Adapter.
- Knowledge-base and artifact interfaces for recording outputs.

Boundary constraints:

- Does not decide source import policy.
- Does not own model-provider configuration.
- Does not write directly around knowledge-base or artifact-store boundaries.
- Does not present inferred people dynamics as definitive facts.

### Model Adapter

Offers:

- Provide configured LLM connection.
- Provide model/provider metadata for analysis-run records.

Consumes:

- Runtime or environment configuration selected by downstream technical design.

Boundary constraints:

- Does not know conversation storage details.
- Does not own prompts or analysis semantics.
- Does not expose provider-specific behavior to Query/Automation Interface.

### Workflow Runner

Offers:

- Run source ingestion workflow.
- Run analysis workflow for existing local conversations.
- Support rerunnable analysis runs.
- Coordinate workflow state transitions and failure reporting.

Consumes:

- Query/Automation Interface requests.
- Source Importer, Conversation Knowledge Base, Artifact Store, Analysis Enricher, and Model Adapter interfaces.

Boundary constraints:

- Does not own durable business records.
- Does not implement source API details.
- Does not implement analysis prompts.
- Does not implement CLI presentation.

### Query/Automation Interface

Offers:

- Trigger ingestion workflow.
- Trigger analysis workflow.
- Query local conversation and analysis records.
- Display basic local results through the CLI adapter.
- Pass runtime user identity and optional context into workflows.

Consumes:

- Workflow Runner operations.
- Conversation Knowledge Base query operations.
- Artifact Store retrieval operations when local output display requires artifact content.

Boundary constraints:

- CLI is an adapter, not the core automation boundary.
- Does not own workflow orchestration logic.
- Does not call Fathom directly.
- Does not construct LLMs.

## Architectural Workflows

### Source Ingestion Workflow

The ingestion workflow discovers visible Fathom conversations, checks local knowledge-base state, imports metadata and transcript source for eligible conversations, stores source artifacts, records artifact references, and updates processing state.

The workflow must treat incomplete or failed processing as retryable. A conversation is not fully processed until local download and processing records indicate completion.

### Analysis Workflow

The analysis workflow selects an existing local conversation, receives runtime user identity and optional context, creates a distinct analysis run, reads transcript artifacts and metadata, runs required analysis perspectives, persists analysis artifacts, records structured findings or artifact references, and marks the analysis run outcome.

Analysis is rerunnable. Reruns must not overwrite prior analysis runs by default.

### Query And Review Workflow

The query and review flow reads from the Conversation Knowledge Base and may resolve artifact references through the Artifact Store. The first version exposes basic local access and CLI stdout display. The architecture preserves future room for richer query and automation without requiring advanced search infrastructure now.

## Major Architectural Constraints

- Conversation Knowledge Base is authoritative for local conversation records and analysis-run records.
- Artifact Store is authoritative for local artifact bytes and artifact path resolution.
- Ingestion and analysis are separate workflows.
- CLI is an adapter over Query/Automation Interface.
- User identity and optional context are runtime workflow inputs, not inferred implicitly from Fathom metadata.
- Fathom summaries are excluded from required workflow contracts.
- Analysis outputs must preserve evidence references and confidence where meaningful.
- Verbatim transcript evidence excerpts may be stored in local analysis artifacts.
- LLM provider choice must be configuration-driven and isolated behind Model Adapter.
- Advanced search, embeddings, and retrieval augmentation are not part of the initial architecture.

## Fidelity To Approved Componentization

This architecture preserves the approved component model without replacement:

- Conversation Knowledge Base remains the architectural center.
- Artifact Store remains separate from the knowledge base.
- Source Importer remains a light source boundary over Fathom.
- Analysis Enricher remains separate from model access, workflow orchestration, and storage ownership.
- Model Adapter isolates provider configuration.
- Workflow Runner is the LangGraph composition boundary.
- Query/Automation Interface owns entrypoints while CLI remains an adapter.

No approved component responsibility has been merged into another component. No new component replaces the approved model.

## Decisions Explicitly Deferred

- Exact local database technology and schema.
- Exact artifact directory layout and file naming.
- Exact indexing and query strategy.
- Exact LangGraph graph topology, state object, node names, and edge logic.
- Exact source-import pagination, retry, and throttling behavior.
- Exact workflow command names and CLI option names.
- Exact prompt templates and prompt versioning.
- Exact structured analysis output schemas.
- Exact model-provider configuration mechanism.
- Exact transcript refresh detection strategy.
- Exact local deletion or retention policy.
- Exact platform-specific application data path.

## Open Questions

- Should failed transcript downloads be retried automatically, manually, or both?
- Should local deletion of conversation artifacts and knowledge-base records be supported in the first version?
- Should Bedrock/Sonnet be required as the first non-local model-provider implementation?

## Questions For CTO

No architecture-level CTO questions remain.

## Decisions Requested

No architecture-level decisions remain requested.

### CTO Decisions

- SQLite is approved by CTO but not required and the solution may be chosen by the Implementation Engineer if they have a better alternative
- the data should be stored in the best practice location for a given platform. Follow patterns set by other similar data based applications. The repository locally is not right for this, I would say something following a convention for data in the same way that ~/.config/application_name/* is used for configuration files on mac and linux.
- all conversations not processed should be processed, with more recent ones priortized above older ones
- JSON may be the output format initially for analysis output, but is not constrained to be the only one.
- CTO approves this architecture as governing input for technical design.

## Recommended Next Step

Senior systems engineer review using `review-architecture-as-systems-engineer`.

## Approval Status

approved

## Senior Systems Engineer Review

### Findings

No blocking findings.

- The architecture is coherent with the approved requirements and the approved Model 3 componentization. It preserves the Conversation Knowledge Base as the product center and keeps Source Importer, Artifact Store, Analysis Enricher, Model Adapter, Workflow Runner, and Query/Automation Interface as distinct architectural boundaries.
- The architecture respects CTO decisions recorded in the governing artifacts: ingestion and analysis are separate workflows, CLI is an adapter, runtime username and optional context are workflow inputs, action extraction covers all participants, verbatim evidence excerpts are allowed locally, and Fathom summaries are excluded from required workflow contracts.
- Boundary discipline is strong enough for technical design. Durable local records, file artifacts, source API access, LLM access, analysis behavior, orchestration, and operator interface concerns are separated at the right architectural level.
- Operational concerns are covered at the correct level for this stage: retryable incomplete processing, rerunnable analysis, provider isolation, local-first storage, and deferred advanced search are all visible without drifting into schema, prompt, or graph-node design.
- The CTO has resolved the architecture-level questions that were pending at review time. Remaining open questions are appropriate for technical design.

### Required Changes

No architecture changes are required before CTO review.

### Open Questions

- No architecture-level review questions remain.

### Review Disposition

Accepted. The architecture is complete enough to govern technical design.

## CTO Review

CTO answered the architecture questions inline under `CTO Decisions` and approved the architecture as governing input for technical design on 2026-05-01.

## Sign-Off

### Author

- Signer: Codex
- Signer Type: agent
- Role: Architecture author
- Review Perspective: architecture drafting
- Disposition: submitted-for-review
- Summary Notes: Initial architecture for the local Fathom conversation agent, preserving the approved Conversation Knowledge Base component model.
- Date: 2026-05-01

### Review Entries

- Signer: Codex
- Signer Type: agent
- Role: Senior Systems Engineer reviewer
- Review Perspective: architecture coherence, boundary discipline, and technical-design readiness
- Disposition: accepted
- Summary Notes: Architecture preserves the approved component model. CTO decisions are recorded, and the architecture is ready to govern technical design.
- Date: 2026-05-01

### CTO Sign-Off

- Signer: CTO (Human)
- Signer Type: human
- Status: approved
- Date: 2026-05-01

### Workflow Status

- Current Status: approved
