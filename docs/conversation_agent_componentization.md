# Fathom Conversation Agent System Componentization

## Purpose

Define and compare viable software component models for the local Fathom conversation agent before architecture is written. The goal is to choose component boundaries that satisfy the approved requirements and remain useful when adding new workflow automations beyond the initial transcript analysis flow.

## Scope

This document covers the componentization of the local conversation ingestion, artifact storage, queryable conversation database, LangGraph orchestration, model-provider access, and transcript analysis capabilities. It does not define implementation modules, database schema, prompt templates, CLI command names, or production deployment architecture.

## Inputs Consulted

- Approved requirements in `docs/conversation_agent_requirements.md`.
- Existing Fathom client, domain model, and mapper in `src/fathom_play`.
- Existing design decisions in `docs/design_decisions.md`.
- CTO direction to make the componentization useful for new workflow automations.

## Governing Inputs

- Requirements are approved by CTO as of 2026-04-30.
- The agent must be based on LangGraph.
- LangChain may be used primarily for configurable LLM access.
- Ollama is the initial local default LLM provider.
- Future Bedrock/Sonnet support must be possible through configuration.
- Fathom summaries are out of scope.
- Conversations are previously processed only after local download and processing complete.
- Analysis must be rerunnable.
- The local database must start simple, but the product direction is a usable queryable conversation database rather than processing state alone.
- Analysis must use careful language and tie meaningful claims to transcript evidence.
- Component boundaries should support future workflow automations.
- User identity for coaching analysis is supplied by the CLI at workflow runtime and passed into the workflow with other metadata and optional context.

## Supporting Context

The current codebase already separates Fathom HTTP access, provider-to-domain mapping, and CLI presentation. That separation should be preserved where useful. The new system expands the current tool from API exploration into local workflow automation over conversation artifacts.

## Expected Change Profile

| Change Type | Expected Frequency Or Importance | Notes |
| --- | --- | --- |
| New workflow automations | High | CTO explicitly wants componentization useful for new automations. |
| New analysis perspectives | High | Current requirements already include classification, action items, coaching, and people dynamics; more perspectives are likely. |
| LLM provider/model changes | High | Ollama default plus future Bedrock/Sonnet support is a governing input. |
| Prompt and output schema revisions | High | Early analysis behavior will likely iterate quickly. |
| Local storage layout changes | Medium | Requirements call for careful filesystem structure but defer exact layout. |
| Conversation database evolution | High | The database starts simple, but long-term value comes from queryable conversation records and analysis outputs. |
| Fathom API changes or new meeting providers | Medium | Existing design anticipates provider substitution; current requirement is Fathom only. |
| User interaction changes | Medium | CLI is likely first, but command shape is deferred. |
| Hosted or multi-user operation | Low | Explicitly out of scope. |
| Search or embeddings | Low | Explicitly out of scope for initial scope. |

## Componentization Models Considered

### Model 1: Workflow Pipeline Components

This model divides the system by the major stages of the initial workflow: discover, ingest, analyze, and persist.

#### Components

| Component | Area Of Responsibility | Owns State/Data? | Notes |
| --- | --- | --- | --- |
| Discovery Component | Finds available Fathom conversations and filters them by processing state. | No | Focused on discovery scope and eligibility. |
| Ingestion Component | Downloads transcripts and meeting metadata for eligible conversations. | Partial | Produces source artifacts but does not own persistence policy. |
| Analysis Component | Runs required LLM analysis perspectives over transcript content. | No | Encapsulates classification, action-item, coaching, and people-dynamics analysis as workflow stages. |
| Persistence Component | Writes local files and database records. | Yes | Owns artifact and database state. |
| LLM Access Component | Returns configured model connection. | No | Supports Ollama and future provider switching. |
| Orchestration Component | Coordinates the pipeline using LangGraph. | Partial | Owns workflow execution state, not durable conversation records. |

#### Boundaries

- Discovery does not download transcripts.
- Ingestion does not decide final processed status.
- Analysis does not directly decide filesystem or database layout.
- Persistence owns local durable state.
- Orchestration coordinates components but does not own provider-specific Fathom logic.
- LLM access hides provider-specific model construction from analysis stages.

#### Interfaces Offered

| Component | Interface Offered | Consumers | Notes |
| --- | --- | --- | --- |
| Discovery Component | Discover eligible conversations for a scope. | Orchestration | Returns conversation identifiers and available metadata. |
| Ingestion Component | Fetch transcript source for a recording. | Orchestration | Uses Fathom access underneath. |
| Analysis Component | Analyze transcript for required perspectives. | Orchestration | Produces structured analysis outputs. |
| Persistence Component | Store artifacts, record status, read processing state. | Discovery, Ingestion, Analysis, Orchestration | Central state boundary. |
| LLM Access Component | Provide configured chat model. | Analysis | Keeps provider choice outside analysis behavior. |
| Orchestration Component | Run the end-to-end processing workflow. | CLI or future automation triggers | Uses LangGraph. |

#### Interfaces Consumed

| Component | Interface Consumed | Provider | Notes |
| --- | --- | --- | --- |
| Discovery Component | Processing-state lookup. | Persistence Component | Determines eligibility. |
| Ingestion Component | Fathom meeting and transcript access. | Existing Fathom integration | Fathom summaries are not consumed. |
| Analysis Component | Transcript artifact access and LLM connection. | Persistence Component, LLM Access Component | Reads transcript source; writes outputs through persistence. |
| Orchestration Component | Discovery, ingestion, analysis, persistence, LLM access. | All other components | Coordinates flow. |

#### Collaborations

- Orchestration asks Discovery for eligible recordings.
- Orchestration asks Ingestion to fetch transcript source for each eligible recording.
- Ingestion asks Persistence to store raw and human-readable transcript artifacts.
- Orchestration asks Analysis to run required perspectives.
- Analysis asks LLM Access for the configured model and asks Persistence to write outputs.
- Orchestration asks Persistence to mark processing complete or failed.

#### Change-Locality Assessment

| Expected Change Type | Locality Rating | Components Affected | Evidence Notes |
| --- | --- | --- | --- |
| New workflow automations | Medium | Orchestration plus stage components | Pipeline stages are reusable, but component boundaries are still shaped around the initial workflow. |
| New analysis perspectives | High | Analysis Component | Most perspective changes stay local to analysis. |
| LLM provider/model changes | High | LLM Access Component | Provider selection is isolated. |
| Prompt and output schema revisions | High | Analysis Component | Analysis owns prompts and result expectations at this level. |
| Local storage layout changes | High | Persistence Component | Durable layout ownership is centralized. |
| Processing state changes | High | Persistence Component | State ownership is centralized. |
| Fathom API changes or new providers | Medium | Ingestion and Discovery | Provider access may leak into multiple stage components. |

#### Risks

- The model is easy to understand but tends to hard-code the first workflow as the organizing concept.
- Future automations may either overload the pipeline stages or require parallel orchestration paths.
- Discovery and ingestion boundaries may blur when future automations need provider-specific metadata without transcript download.

### Model 2: Capability Components With Workflow Orchestration

This model divides the system into reusable capabilities that can be composed by multiple LangGraph workflows. It treats ingestion, local records, artifacts, analysis perspectives, and model access as independent capabilities.

#### Components

| Component | Area Of Responsibility | Owns State/Data? | Notes |
| --- | --- | --- | --- |
| Conversation Source Connector | Provides provider-specific access to conversations and transcripts. | No | Initial implementation is Fathom; future sources can be added behind the same capability. |
| Conversation Registry | Owns local conversation identity, processing status, and analysis-run records. | Yes | Local record boundary, but not a full query-centered knowledge base. |
| Artifact Repository | Owns local filesystem artifacts and artifact path resolution. | Yes | Stores raw transcript, rendered transcript, metadata, and analysis files. |
| Workflow Orchestrator | Defines and runs LangGraph workflows by composing capabilities. | Partial | Owns workflow execution state, routing, and error transitions. |
| Analysis Capability Set | Provides transcript analysis capabilities such as classification, action items, coaching, and people dynamics. | No | Each perspective is a capability with evidence-grounded output requirements. |
| LLM Provider Gateway | Provides configured LLM connections to analysis capabilities. | No | Ollama default; future Bedrock/Sonnet through configuration. |
| Automation Interface | Exposes user- or automation-facing operations. | No | Initial interface may be CLI; future triggers can reuse the same capabilities. |

#### Boundaries

- Conversation Source Connector is the only component that knows provider API details.
- Conversation Registry owns durable processing state but not file bytes.
- Artifact Repository owns file layout but not workflow eligibility policy.
- Workflow Orchestrator composes capabilities but does not own local durable records.
- Analysis Capability Set owns analytical behavior and evidence requirements but not model-provider construction.
- LLM Provider Gateway owns provider selection and model connection.
- Automation Interface triggers workflows or capability operations but does not implement workflow logic.

#### Interfaces Offered

| Component | Interface Offered | Consumers | Notes |
| --- | --- | --- | --- |
| Conversation Source Connector | List conversations, fetch transcript, return source metadata. | Workflow Orchestrator, future automations | Fathom summaries are intentionally absent. |
| Conversation Registry | Query processing status, record conversation metadata, record analysis runs, mark outcomes. | Workflow Orchestrator, Automation Interface | Keeps processing records authoritative but under-emphasizes long-term query. |
| Artifact Repository | Write/read source artifacts, write/read analysis artifacts, resolve artifact locations. | Workflow Orchestrator, Analysis Capability Set, Automation Interface | Keeps filesystem layout behind one boundary. |
| Workflow Orchestrator | Run named workflows such as ingest-and-analyze or rerun-analysis. | Automation Interface | LangGraph-centered composition boundary. |
| Analysis Capability Set | Run specific analysis perspectives against transcript input. | Workflow Orchestrator, future automations | Perspective capabilities can be reused independently. |
| LLM Provider Gateway | Return configured LLM connection and provider metadata. | Analysis Capability Set | Provider-independent analysis behavior. |
| Automation Interface | Operator-facing commands or future automation triggers. | User or external scheduler | Does not own business capabilities. |

#### Interfaces Consumed

| Component | Interface Consumed | Provider | Notes |
| --- | --- | --- | --- |
| Workflow Orchestrator | Source access, registry, artifacts, analysis capabilities. | Conversation Source Connector, Conversation Registry, Artifact Repository, Analysis Capability Set | Composes workflows. |
| Analysis Capability Set | LLM connection and transcript artifact access. | LLM Provider Gateway, Artifact Repository | Analysis reads transcript and produces structured outputs. |
| Conversation Registry | Artifact paths and workflow outcomes. | Artifact Repository, Workflow Orchestrator | Records references and status. |
| Automation Interface | Workflow execution and status query interfaces. | Workflow Orchestrator, Conversation Registry, Artifact Repository | Provides user and automation entrypoints. |

#### Collaborations

- Automation Interface requests a workflow run from Workflow Orchestrator.
- Workflow Orchestrator asks Conversation Source Connector for available conversations.
- Workflow Orchestrator asks Conversation Registry whether a recording has completed processing.
- Workflow Orchestrator asks Conversation Source Connector to fetch transcript source for eligible recordings.
- Workflow Orchestrator asks Artifact Repository to persist meeting metadata and transcript artifacts.
- Workflow Orchestrator asks Analysis Capability Set to run selected analyses.
- Analysis Capability Set asks LLM Provider Gateway for the configured model connection.
- Analysis Capability Set returns evidence-grounded results to Workflow Orchestrator.
- Workflow Orchestrator asks Artifact Repository and Conversation Registry to persist analysis outputs and final status.
- Future automations can reuse Conversation Registry, Artifact Repository, Source Connector, and selected Analysis capabilities without duplicating the main workflow.

#### Change-Locality Assessment

| Expected Change Type | Locality Rating | Components Affected | Evidence Notes |
| --- | --- | --- | --- |
| New workflow automations | High | Workflow Orchestrator, Automation Interface | Existing capabilities are reusable building blocks. |
| New analysis perspectives | High | Analysis Capability Set | New perspectives can be added without changing source, registry, or artifact ownership. |
| LLM provider/model changes | High | LLM Provider Gateway | Provider details are isolated. |
| Prompt and output schema revisions | High | Analysis Capability Set | Analysis behavior owns these revisions. |
| Local storage layout changes | High | Artifact Repository | File layout changes stay behind artifact interface. |
| Processing state changes | High | Conversation Registry | Database changes stay behind registry interface. |
| Fathom API changes or new providers | High | Conversation Source Connector | Provider detail is isolated to one capability. |
| User interaction changes | High | Automation Interface | CLI or scheduler changes do not alter capabilities. |

#### Risks

- More components than the initial workflow strictly requires.
- Requires discipline to keep orchestration from absorbing component responsibilities.
- Requires clear definitions for what belongs in Registry versus Artifact Repository.

### Model 3: Local Knowledge Base Components

This model organizes the system around the local database as the primary product center. Workflows and analysis operate mainly as ways to enrich a local conversation knowledge base.

#### Components

| Component | Area Of Responsibility | Owns State/Data? | Notes |
| --- | --- | --- | --- |
| Conversation Knowledge Base | Owns local records, artifact references, analysis results, and queryable metadata. | Yes | Central database-oriented component. |
| Source Importer | Imports Fathom conversations and transcripts into the knowledge base. | Partial | Writes source-derived records. |
| Artifact Store | Stores transcript and analysis files. | Yes | Files are subordinate to knowledge-base records. |
| Analysis Enricher | Adds analysis-derived metadata and findings. | Partial | Enriches knowledge-base records. |
| Model Adapter | Provides configured LLM access. | No | Provider switching boundary. |
| Workflow Runner | Runs import and enrichment workflows. | Partial | Coordinates state transitions around the knowledge base. |
| Query/Automation Interface | Lets operator or automations inspect and act on the knowledge base. | No | Stronger emphasis on query workflows. |

#### Boundaries

- Conversation Knowledge Base is the primary owner of local state.
- Source Importer and Analysis Enricher mutate knowledge-base records through controlled interfaces.
- Artifact Store owns file bytes but is secondary to knowledge-base indexing.
- Workflow Runner sequences import and enrichment operations.
- Query/Automation Interface reads from the knowledge base and triggers workflows.

#### Interfaces Offered

| Component | Interface Offered | Consumers | Notes |
| --- | --- | --- | --- |
| Conversation Knowledge Base | Conversation, processing, analysis-run, and metadata queries. | Source Importer, Analysis Enricher, Workflow Runner, Query/Automation Interface | Central interface. |
| Source Importer | Import visible source conversations. | Workflow Runner | Provider-specific import behavior. |
| Artifact Store | Store and retrieve artifact files. | Source Importer, Analysis Enricher, Knowledge Base | File storage boundary. |
| Analysis Enricher | Enrich conversation records with analysis findings. | Workflow Runner | Analysis is framed as metadata enrichment. |
| Model Adapter | Provide configured LLM access. | Analysis Enricher | Provider boundary. |
| Workflow Runner | Run import, enrich, and rerun workflows. | Query/Automation Interface | Composes importer and enricher. |

#### Interfaces Consumed

| Component | Interface Consumed | Provider | Notes |
| --- | --- | --- | --- |
| Source Importer | Fathom access and knowledge-base writes. | Existing Fathom integration, Conversation Knowledge Base | Imports source data. |
| Analysis Enricher | Knowledge-base reads, artifacts, LLM access. | Conversation Knowledge Base, Artifact Store, Model Adapter | Enriches records. |
| Query/Automation Interface | Knowledge-base queries and workflow execution. | Conversation Knowledge Base, Workflow Runner | User-facing access. |

#### Collaborations

- Workflow Runner asks Source Importer to import conversations.
- Source Importer writes local state through Conversation Knowledge Base and Artifact Store.
- Workflow Runner asks Analysis Enricher to enrich selected conversations.
- Analysis Enricher reads transcript artifacts and writes findings back to Conversation Knowledge Base.
- Query/Automation Interface uses the knowledge base for status and future automation.

#### Change-Locality Assessment

| Expected Change Type | Locality Rating | Components Affected | Evidence Notes |
| --- | --- | --- | --- |
| New workflow automations | Medium | Query/Automation Interface, Workflow Runner, Knowledge Base | Automations depend heavily on the central knowledge-base model. |
| New analysis perspectives | Medium | Analysis Enricher, Knowledge Base | New analyses may require knowledge-base shape changes. |
| LLM provider/model changes | High | Model Adapter | Provider switching is isolated. |
| Prompt and output schema revisions | Medium | Analysis Enricher, Knowledge Base | Schema coupling may increase. |
| Local storage layout changes | Medium | Artifact Store, Knowledge Base | Artifact references are indexed centrally. |
| Processing state changes | Medium | Knowledge Base, Workflow Runner | State model is central. |
| Fathom API changes or new providers | Medium | Source Importer, Knowledge Base | Importer changes may influence central record shape. |

#### Risks

- The simple local database requirement may be stretched too early.
- Analysis changes could force database changes before usage patterns are clear.
- The model biases the system toward query/search use cases that are explicitly deferred.

## Comparative Assessment

| Model | Responsibility Clarity | Boundary Clarity | Interface Simplicity | Change Locality | Main Tradeoff |
| --- | --- | --- | --- | --- | --- |
| Workflow Pipeline Components | High | Medium | High | Medium | Simple for the first workflow, less flexible for future automations. |
| Capability Components With Workflow Orchestration | High | High | Medium | High | Slightly more structure upfront, best reuse for new automations. |
| Local Knowledge Base Components | High | Medium | Medium | High | Best long-term fit if guarded against premature search and schema complexity. |

## Recommended Component Model

Recommend Model 3: Local Knowledge Base Components, revised with explicit guardrails to keep the first implementation simple.

This model best fits the revised governing inputs because the long-term product value is a usable local database of conversations, analyses, evidence, and workflow-relevant metadata. Ingestion is necessary, but it is not the center of the product. The system should be organized around a Conversation Knowledge Base that future automations can query and enrich.

The recommendation should not be read as approval for premature search infrastructure. The Conversation Knowledge Base should start with simple local records and queryable metadata, while Artifact Store preserves source and analysis files. Search, embeddings, full-text indexing, and retrieval workflows remain deferred. Workflow Runner, Source Importer, Analysis Enricher, Model Adapter, and Query/Automation Interface remain separate so the knowledge base does not become a monolith.

## Rejected Alternatives

- Single script or monolithic agent: rejected because it would mix provider access, file layout, database state, orchestration, prompts, and model access, making reruns and future automations costly.
- Pipeline-only decomposition: rejected as the primary model because it treats ingestion and analysis as the product center rather than as ways to build and enrich the local conversation database.
- Pure capability orchestration without a knowledge-base center: rejected as the primary model because it keeps future automations reusable but under-specifies the database as a product surface for query and review.
- Database-centered knowledge base with early search/vector infrastructure: rejected because search, embeddings, and retrieval augmentation are still out of scope for the first implementation.

## Decisions Made

- Use a local Conversation Knowledge Base as the governing center of the component model.
- Treat ingestion and analysis as workflows that build or enrich the knowledge base.
- Preserve a separate Artifact Store for raw and human-readable transcript and analysis files.
- Preserve a separate Source Importer for Fathom access and future source-provider changes.
- Preserve a separate Analysis Enricher for evidence-grounded transcript analysis.
- Preserve a separate Model Adapter for configurable LLM access.
- Preserve a separate Workflow Runner as the LangGraph composition boundary.
- Preserve a Query/Automation Interface as the entrypoint for local review and future workflow automations.

## Architecture Constraints Implied

- The architecture must make the Conversation Knowledge Base the authoritative local record for conversations, processing status, analysis runs, and queryable metadata.
- The architecture must preserve a clear boundary between queryable local records and filesystem artifact ownership.
- The architecture must keep provider-specific Fathom behavior out of the knowledge base, analysis enrichment, and workflow entrypoints.
- The architecture must keep LLM provider selection out of analysis enrichment behavior.
- The architecture must let analysis runs be recorded independently from source transcript ingestion.
- The architecture must let future workflows query and enrich the knowledge base without duplicating source, artifact, or model-provider logic.
- The architecture must not make Fathom summaries part of any required component contract.
- The architecture must maintain evidence-grounded analysis as a component-level requirement of the Analysis Enricher.
- The architecture must defer advanced search, embeddings, and retrieval infrastructure until product usage justifies them.

## Decisions Explicitly Deferred

- Exact database technology and schema.
- Exact artifact directory layout and file naming.
- Exact LangGraph graph topology and state object.
- Exact workflow names and trigger mechanisms.
- Exact analysis output schemas.
- Exact prompt templates and prompt versioning mechanism.
- Exact configuration mechanism for model providers.
- Exact CLI commands or future automation trigger interfaces.
- Whether transcript refresh detection uses hashes, timestamps, or manual operator control.
- Exact query model and indexing strategy for the Conversation Knowledge Base.

## Open Questions

No componentization-level open questions remain.

## Questions For CTO

All componentization-level CTO questions are answered below.

### CTO Answers

- Yes, confirm model 3
- Yes, confirm the initial Automation Interface should be CLI, but the CLI must be an adapter, not engrained in the Automation Interface.
- The source importer can be a light abstraction over the Fathom api, and may evolve once additional sources are included
- Confirmed - ingestion and analysis should be separate workflows.
- The first version should allow basic access, and the CLI should show the results if requested to it's standard output
- The username should for now be entered on the command line and passed to the workflow along with other metadata, and with optional context.
- CTO confirms this componentization document is approved as governing input for architecture and downstream technical design.

## Decisions Requested

No componentization-level decisions remain requested.

### CTO decisions

- CTO approves the revised recommended component model.
- CTO decides to split ingestion and analysis into separate workflows
- CTO decides that all actions are extracted and associated where possible with a participant
- CTO decides verbatim transcript evidence excerpts are allowed in local analysis artifacts
- CTO approves this componentization as governing input for architecture and downstream technical design.

## Recommended Next Step

Senior systems engineer review using `review-system-componentization-as-systems-engineer`.

## Approval Status

approved

## Senior Systems Engineer Review

### Findings

No blocking findings.

- The revised recommendation is coherent with the approved requirements and the later CTO clarification that the long-term product center is a usable local conversation database. Model 3 now fits the expected change profile better than the earlier capability-only recommendation.
- The component boundaries are sufficient for architecture: Conversation Knowledge Base owns queryable local records, Artifact Store owns file artifacts, Source Importer owns Fathom access, Analysis Enricher owns evidence-grounded analysis, Model Adapter owns LLM provider selection, Workflow Runner owns LangGraph orchestration, and Query/Automation Interface owns operator and automation entrypoints.
- CTO feedback is complete for the componentization decisions requested. It confirms Model 3, CLI-as-adapter, light Fathom importer abstraction, separate ingestion and analysis workflows, basic first-version query access, all-participant action extraction, and verbatim evidence excerpts in local artifacts.
- The prior open issue about user/operator identity is resolved by CTO decision: the CLI supplies username and optional context at workflow runtime.

### Required Changes

No componentization changes required before architecture.

### Open Questions

No componentization-level open questions remain.

### Review Disposition

Accepted. The componentization is ready to govern architecture.

## CTO Review

CTO approved the revised Model 3 recommendation and answered the componentization decisions inline under `Questions For CTO` and `Decisions Requested`. CTO reconfirmed the document as approved governing input for architecture and downstream technical design on 2026-05-01.

## Sign-Off

### Author

- Signer: Codex
- Signer Type: agent
- Role: System componentization author
- Review Perspective: component model comparison and recommendation
- Disposition: submitted-for-review
- Summary Notes: Revised recommendation centers the local Conversation Knowledge Base while preserving separate workflow, source, artifact, analysis, model, and automation boundaries.
- Date: 2026-04-30

### Review Entries

- Signer: Codex
- Signer Type: agent
- Role: Senior Systems Engineer reviewer
- Review Perspective: componentization coherence, boundaries, and architecture readiness
- Disposition: accepted
- Summary Notes: CTO feedback is complete for componentization. User identity for coaching analysis is now resolved as CLI-supplied workflow runtime context.
- Date: 2026-05-01

### CTO Sign-Off

- Signer: CTO (Human)
- Signer Type: human
- Status: approved
- Date: 2026-05-01

### Workflow Status

- Current Status: approved
