# Meeting Data Architecture -- Design Document

## Problem Statement

The current implementation depends on the `fathom-python` SDK (a Speakeasy-generated client) which provides no meaningful abstraction over the Fathom REST API. It returns Fathom-shaped models with every field optional, carries a heavy dependency tree (`svix`, `jsonpath-ng`, `pydantic`, `requests` alongside `httpx`), and couples the codebase to a single provider's vocabulary and data shape.

The system needs meeting data -- recordings, transcripts, people -- from external providers. Fathom is the first provider. Others (Zoom, Teams, manual upload) are anticipated. The architecture must support provider substitution without rewriting domain logic or presentation code.

## Scope

This design covers the internal layering of the `fathom_play` package: how meeting data flows from an external API into domain objects and out to the CLI. It does not cover persistence, event streaming, or multi-service deployment.

---

## Component Boundaries

Four layers, each with a single responsibility:

### Domain

Contains the system's vocabulary for meeting data. These are the concepts the rest of the system reasons about, independent of any provider.

**Components:**

- **Person** -- A named individual with an optional email. Represents anyone who appears in meeting data: a recorder, an invitee, a speaker. Value object: two Persons with the same name and email are equal.
- **Meeting** -- A recorded meeting event. Carries both `id` (string, canonical Fathom identifier) and `recording_id` (integer, used for transcript/summary lookups). Also carries title, timing information, the person who recorded it, and the list of invited participants.
- **Utterance** -- A single spoken segment within a meeting. Attributed to a Person, with the spoken text and a time offset (integer, milliseconds from recording start). Value object. Parsing provider-specific timestamp formats is a mapper responsibility.
- **Transcript** -- An ordered collection of Utterances associated with a specific meeting (by recording_id).
- **Summary** -- A text summary of a meeting, associated with a specific meeting (by recording_id).

**Constraints:**

- No I/O. No imports from infrastructure or presentation layers.
- Fields that are always present in a well-formed record are required, not optional. The "everything is Optional" pattern from the SDK is explicitly rejected -- if data is missing, the mapper handles that before constructing domain objects, or raises an error.
- Person is a value object. Two Persons with the same name and email are equal.
- Utterance is a value object. It carries a time offset (integer, milliseconds from recording start) rather than a formatted timestamp string.
- Transcript and Summary are separate from Meeting. A Meeting does not carry an optional transcript field. You fetch a Meeting; you separately fetch its Transcript. This reflects the actual API semantics (separate endpoints, separate lifecycle) and avoids the "bag of optionals" anti-pattern.

### HTTP Client

A thin, provider-specific HTTP layer. One client per provider. The Fathom client knows the Fathom base URL, authentication scheme, and endpoint paths. It knows nothing about domain objects.

**Interface:**

Every method returns `ApiResponse`, a raw response container carrying:
- HTTP status code (int)
- Response headers (`httpx.Headers` -- preserves case-insensitivity and multi-value support)
- Parsed JSON body (dict or list)

On non-2xx responses, the client raises `FathomApiError` carrying the status code, headers, and error body. `ApiResponse` is only returned for successful responses. The mapper never sees error responses.

`FathomApiError` is defined in the client module, not in the domain layer. It is infrastructure -- it carries HTTP status codes and response bodies. The domain layer does not know that HTTP exists.

**Methods correspond 1:1 to API endpoints:**

- List meetings (with filter parameters)
- Get transcript (by recording ID)
- Get summary (by recording ID)
- List teams
- List team members

**Constraints:**

- Synchronous. All callers block and wait. This is a CLI tool and an exploration playground. Async wrapping is trivial if needed later; forcing async on sync callers is not.
- Uses `httpx.Client` directly. No additional HTTP abstraction.
- Authentication is `x-api-key` header, loaded from environment.
- No automatic pagination. The client returns one page. The caller (mapper or CLI) decides whether to follow cursors. This keeps the HTTP layer honest -- it does HTTP, not business logic.
- No retry logic built in. The API rate limit is 60 req/min. If retry or throttle handling becomes necessary, it belongs in a decorator or middleware around the client, not inside it.

### Mapper

Translates provider-specific JSON responses into domain objects. One mapper per provider.

**Responsibilities:**

- Parse Fathom JSON field names into domain object fields.
- Convert Fathom's string timestamps into integer millisecond offsets.
- Handle missing or null fields: either substitute sensible defaults (e.g., "Unknown" for a missing speaker name) or raise a clear error if the data is too incomplete to represent.
- Assemble Transcript from a list of raw utterance dicts.

**Composable functions:**

Mapper functions are composable. Each operates on the `.data` field of an `ApiResponse` and returns a single domain object type:

- `to_meetings(data) -> list[Meeting]` -- always works, ignores inline transcript/summary data.
- `to_transcripts(data) -> list[Transcript]` -- extracts transcript data if present in meeting list responses or from the standalone transcript endpoint. Returns empty list if transcript data was not included.
- `to_summaries(data) -> list[Summary]` -- same pattern.
- `to_transcript(data) -> Transcript` -- for the standalone `/recordings/{id}/transcript` endpoint.
- `to_summary(data) -> Summary` -- for the standalone `/recordings/{id}/summary` endpoint.

When the Fathom API is called with `include_transcript=true` or `include_summary=true`, the response contains inline data. The CLI composes mapper functions as needed: call `to_meetings()` and `to_transcripts()` on the same response data, then pair results by `recording_id` if needed.

This avoids inventing a container type that only exists to bundle things together for one specific API call pattern. It keeps the mapper functions simple and composable.

**Constraints:**

- No I/O. Receives dictionaries, returns domain objects.
- No knowledge of HTTP, headers, or status codes. It operates on the `.data` field of the API response.
- Testable with fixture JSON -- no mocks, no HTTP stubs required.

### CLI (Presentation)

Typer commands that call the HTTP client, pass responses through the mapper, and format domain objects for display using Rich.

**Constraints:**

- No business logic. No JSON parsing. No direct HTTP calls.
- Receives domain objects from the mapper and formats them.
- Error handling: catches `FathomApiError` from the client and displays user-friendly messages.

---

## Data Flow

```
User Command
    |
    v
CLI (Typer)
    |
    v
FathomHttpClient.list_meetings(**params)
    |
    |-- non-2xx --> raises FathomApiError --> CLI catches and displays error
    |
    v
ApiResponse(status_code, headers, data)
    |
    v
CLI passes response.data to Mapper
    |
    v
fathom_mapper.to_meetings(data) -> list[Meeting]
    |
    v
CLI formats and displays with Rich
```

---

## File Structure

```
src/fathom_play/
    __init__.py
    domain.py              # Person, Meeting, Utterance, Transcript, Summary
    fathom_client.py       # FathomHttpClient, ApiResponse, FathomApiError
    fathom_mapper.py       # Fathom JSON -> domain objects (composable functions)
    cli.py                 # Typer CLI (presentation)
```

Files to delete:
- `fathom_connection.py` -- replaced entirely by the new layering
- `display_utils.py` -- dead code; the CLI uses Rich/Typer directly

---

## Dependency Changes

**Before:**

```
fathom-python        (pulls in: svix, jsonpath-ng, pydantic, requests, typing-inspection, httpx)
python-dotenv
httpx
requests
typer
rich
```

**After:**

```
httpx
python-dotenv
typer
rich
```

The `fathom-python` SDK and `requests` are dropped. `httpx` is the sole HTTP library. `pydantic` is not needed -- domain objects are plain dataclasses.

---

## Key Design Decisions

### Why separate HTTP client and mapper

The HTTP client returns raw responses (headers + JSON). The mapper converts JSON to domain objects. This separation exists for three reasons:

1. **Observability.** Rate limit headers, status codes, and raw JSON shape are visible to the caller. During API exploration, this matters. The caller can log, inspect, or react to HTTP-level concerns without the mapper obscuring them.

2. **Testability.** The mapper is a pure function: dict in, domain objects out. It can be tested with fixture JSON files. No HTTP mocking required.

3. **Provider substitution.** When a second provider (Zoom, Teams) is added, it gets its own HTTP client and its own mapper. The domain objects remain unchanged. The CLI does not need to know which provider is active beyond selecting the right client+mapper pair.

### Why synchronous

All current callers are synchronous (CLI commands that block and wait). Per the async interface design principle: sync is the safer default when callers are known to be sync. Async callers can wrap sync code trivially (`asyncio.to_thread`). The reverse is error-prone.

### Why no automatic pagination in the HTTP client

Pagination is a policy decision. Some callers want one page. Some want all pages. Some want pages until a date threshold. Embedding pagination logic in the HTTP client forces one policy on all callers. The client returns one page with its cursor; the caller decides what to do next.

### Why Utterance carries millisecond offset, not a formatted string

The Fathom API returns timestamps as formatted strings. Other providers may use seconds, milliseconds, or ISO timestamps. The domain object uses a single canonical representation (integer milliseconds from recording start). Each provider's mapper is responsible for parsing its own format into this canonical form. This prevents downstream code from having to handle format differences.

### Why Meeting does not contain Transcript or Summary

The Fathom API has separate endpoints for meetings, transcripts, and summaries. Transcripts and summaries are fetched by recording ID, not bundled into the meeting list response (unless explicitly requested via include flags). Modeling them as optional fields on Meeting would recreate the "bag of optionals" pattern we are explicitly eliminating. Instead, Meeting, Transcript, and Summary are independent domain objects linked by `recording_id`.

When the caller uses `include_transcript=true` on the meetings endpoint, the mapper's composable functions extract Meeting and Transcript objects from the same response data independently. The caller pairs them by `recording_id` if needed.

### Why raise on non-2xx rather than return a result type

For a CLI tool, every call site would need to check success/failure if we returned a result type. Raising `FathomApiError` on non-2xx keeps the happy path clean (the mapper only ever sees successful response data) and concentrates error handling in the CLI's exception handler. This is the simplest correct approach that keeps error paths out of the mapper entirely.

### Why Meeting carries both id and recording_id

Fathom uses `id` (string) as the canonical meeting identifier and `recording_id` (integer) as the key for transcript/summary lookups. They serve different purposes in the API. Both are carried on the domain Meeting. The `recording_id` is the identifier callers use to fetch transcripts and summaries.

### Why no retry or rate limit handling yet

The API rate limit is 60 requests per minute. For a CLI exploration tool, this is unlikely to be hit. If it becomes a concern, retry logic belongs in a decorator or middleware wrapping the HTTP client -- not inside the client itself. Adding it now would be YAGNI.

### Why Team and TeamMember are deferred

The Fathom team endpoints return minimal data (team name, member name/email/teams). There is no current use case that requires team domain objects. When needed, they follow the same pattern: add fields to `domain.py`, add mapper functions, add CLI commands. The architecture supports this without structural changes.

---

## Construction Order

0. Capture real API response for timestamp format confirmation and test fixtures
1. Domain objects (dataclasses, no I/O)
2. Domain tests (if any domain logic warrants it -- value equality on Person, etc.)
3. Fathom HTTP client (thin httpx wrapper, raises FathomApiError on non-2xx)
4. Fathom mapper (JSON to domain, testable with fixtures)
5. CLI rewrite (presentation only)
6. Delete old files, clean dependencies