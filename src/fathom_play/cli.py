"""Fathom Play CLI -- explore meeting data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from fathom_play import fathom_mapper
from fathom_play.automation import ConversationAutomation
from fathom_play.fathom_client import FathomApiError, FathomHttpClient
from fathom_play.model_adapter import DEFAULT_MODEL

app = typer.Typer(help="Fathom.ai meeting tools")
console = Console()
DataRootOption = Annotated[Path | None, typer.Option(help="Override application data directory")]
UsernameOption = Annotated[str, typer.Option("--username", "-u", help="User identity for coaching analysis")]
ContextOption = Annotated[str, typer.Option("--context", "-c", help="Optional analysis context")]
ModelOption = Annotated[str, typer.Option("--model", "-m", help="Model for analysis (e.g. claude-sonnet-4-6, claude-opus-4-7, gemma4:e2b)")]
RecordingIdAnalyzeArgument = Annotated[int, typer.Argument(help="Recording ID to analyze")]
RecordingIdDeleteArgument = Annotated[int, typer.Argument(help="Recording ID to delete locally")]


def _get_client() -> FathomHttpClient:
    try:
        return FathomHttpClient()
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None


def _print_raw(resp):
    """Print raw API response headers and body as formatted JSON."""
    console.print("[bold cyan]Headers[/bold cyan]")
    headers_dict = dict(resp.headers)
    console.print(Syntax(json.dumps(headers_dict, indent=2), "json"))
    console.print("\n[bold cyan]Body[/bold cyan]")
    console.print(Syntax(json.dumps(resp.data, indent=2, default=str), "json"))


def _automation(
    data_root: Path | None = None,
    with_source: bool = True,
    with_model: bool = True,
    model: str = DEFAULT_MODEL,
) -> ConversationAutomation:
    try:
        return ConversationAutomation(data_root=data_root, with_source=with_source, with_model=with_model, model=model)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def meetings(
    days: int = typer.Option(30, help="Show meetings from the last N days"),
    limit: int = typer.Option(20, help="Max meetings to display"),
    raw: bool = typer.Option(False, "--raw", help="Show raw API headers and JSON body"),
):
    """List recent meetings."""
    from datetime import UTC, datetime, timedelta

    created_after = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    with _get_client() as client:
        try:
            resp = client.list_meetings(created_after=created_after)
        except FathomApiError as e:
            console.print(f"[red]API error ({e.status_code}): {e.body[:200]}[/red]")
            raise typer.Exit(1) from None

    if raw:
        _print_raw(resp)
        raise typer.Exit(0)

    items = fathom_mapper.to_meetings(resp.data)

    if not items:
        console.print(f"No meetings found in the last {days} days.")
        raise typer.Exit(0)

    table = Table(title=f"Meetings (last {days} days)")
    table.add_column("Recording ID", style="dim")
    table.add_column("Date", style="cyan")
    table.add_column("Duration", justify="right")
    table.add_column("Title")
    table.add_column("Recorded By", style="green")
    table.add_column("Invitees", justify="right")

    for m in items[:limit]:
        date_str = m.start_time.strftime("%Y-%m-%d %H:%M")
        mins, secs = divmod(m.duration_seconds, 60)
        duration_str = f"{mins}m {secs}s"
        invitee_count = str(len(m.invitees))
        table.add_row(
            str(m.recording_id),
            date_str,
            duration_str,
            m.title,
            m.recorded_by.name,
            invitee_count,
        )

    console.print(table)
    console.print(f"\n[dim]{len(items)} meeting(s) returned, showing up to {limit}.[/dim]")

    cursor = fathom_mapper.next_cursor(resp.data)
    if cursor:
        console.print("[dim]More results available (pagination cursor present).[/dim]")


@app.command()
def transcript(
    recording_id: int = typer.Argument(help="Recording ID of the meeting"),
    raw: bool = typer.Option(False, "--raw", help="Show raw API headers and JSON body"),
):
    """Show the transcript for a meeting."""
    with _get_client() as client:
        try:
            resp = client.get_transcript(recording_id)
        except FathomApiError as e:
            console.print(f"[red]API error ({e.status_code}): {e.body[:200]}[/red]")
            raise typer.Exit(1) from None

    if raw:
        _print_raw(resp)
        raise typer.Exit(0)

    t = fathom_mapper.to_transcript(resp.data, recording_id)

    if not t.utterances:
        console.print("[yellow]No transcript available for this recording.[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold cyan]Transcript ({len(t.utterances)} utterances)[/bold cyan]\n")

    for u in t.utterances:
        total_seconds = u.offset_ms // 1000
        mins, secs = divmod(total_seconds, 60)
        console.print(f"[dim]{mins:02d}:{secs:02d}[/dim] [bold]{u.speaker.name}:[/bold] {u.text}")

    console.print(f"\n[dim]{len(t.utterances)} utterance(s).[/dim]")


@app.command()
def summary(
    recording_id: int = typer.Argument(help="Recording ID of the meeting"),
):
    """Show the summary for a meeting."""
    with _get_client() as client:
        try:
            resp = client.get_summary(recording_id)
        except FathomApiError as e:
            console.print(f"[red]API error ({e.status_code}): {e.body[:200]}[/red]")
            raise typer.Exit(1) from None

    s = fathom_mapper.to_summary(resp.data, recording_id)

    if not s.markdown_text:
        console.print("[yellow]No summary available for this recording.[/yellow]")
        raise typer.Exit(0)

    from rich.markdown import Markdown

    console.print(Markdown(s.markdown_text))


@app.command("ingest-local")
def ingest_local(
    data_root: DataRootOption = None,
):
    """Ingest unprocessed Fathom conversations into local storage."""
    automation = _automation(data_root=data_root, with_source=True, with_model=False)
    try:
        result = automation.ingest()
    except FathomApiError as e:
        console.print(f"[red]API error ({e.status_code}): {e.body[:200]}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Ingestion failed: {e}[/red]")
        raise typer.Exit(1) from None

    console.print(
        f"Discovered {result.discovered}; skipped {result.skipped}; "
        f"ingested {result.completed}; failed {result.failed}."
    )


@app.command("analyze-local")
def analyze_local(
    recording_id: RecordingIdAnalyzeArgument,
    username: UsernameOption,
    context: ContextOption = "",
    data_root: DataRootOption = None,
    model: ModelOption = DEFAULT_MODEL,
):
    """Analyze a locally ingested conversation."""
    automation = _automation(data_root=data_root, with_source=False, with_model=True, model=model)
    try:
        analysis_run_id = automation.analyze(recording_id, username=username, context=context)
    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")
        raise typer.Exit(1) from None

    console.print(f"Analysis run {analysis_run_id} completed for recording {recording_id}.")


@app.command("query-local")
def query_local(
    data_root: DataRootOption = None,
):
    """Show locally stored conversations."""
    automation = _automation(data_root=data_root, with_source=False, with_model=False)
    rows = automation.query()
    table = Table(title="Local conversations")
    table.add_column("Recording ID", style="dim")
    table.add_column("Status")
    table.add_column("Start")
    table.add_column("Title")
    for row in rows:
        table.add_row(str(row.recording_id), row.status, row.start_time, row.title)
    console.print(table)


@app.command("delete-local")
def delete_local(
    recording_id: RecordingIdDeleteArgument,
    data_root: DataRootOption = None,
):
    """Delete local records and artifacts for a conversation."""
    automation = _automation(data_root=data_root, with_source=False, with_model=False)
    try:
        automation.delete_local(recording_id)
    except Exception as e:
        console.print(f"[red]Local deletion failed: {e}[/red]")
        raise typer.Exit(1) from None
    console.print(f"Deleted local data for recording {recording_id}.")


if __name__ == "__main__":
    app()
