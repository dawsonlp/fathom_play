"""Fathom Play CLI -- explore meeting data."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from fathom_play import fathom_mapper
from fathom_play.fathom_client import FathomApiError, FathomHttpClient

app = typer.Typer(help="Fathom.ai meeting tools")
console = Console()


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


if __name__ == "__main__":
    app()
