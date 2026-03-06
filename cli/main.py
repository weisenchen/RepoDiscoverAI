#!/usr/bin/env python3
"""
RepoDiscoverAI CLI

Command-line interface for discovering GitHub repositories.

Usage:
    repodiscover search "machine learning" --language python --min-stars 1000
    repodiscover trending --period week --limit 10
    repodiscover paths
    repodiscover stats
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
import requests
import sys
from typing import Optional

app = typer.Typer(help="Discover awesome GitHub repositories")
console = Console()

# Default API URL
API_BASE = "http://localhost:8080/api"


def check_api_available():
    """Check if the API server is available."""
    try:
        response = requests.get(f"{API_BASE[:-4]}/health", timeout=5)
        if response.status_code == 200:
            return True
    except requests.RequestException:
        pass
    console.print("[red]❌ API server not available. Please start the server first:[/red]")
    console.print("   uvicorn app.main:app --host 0.0.0.0 --port 8080")
    sys.exit(1)


@app.command()
def version():
    """Show version information."""
    console.print("[bold blue]RepoDiscoverAI CLI[/bold blue] v2.0.0")
    console.print("Discover awesome GitHub repositories")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    language: Optional[str] = typer.Option(None, "-l", "--language", help="Filter by language"),
    min_stars: Optional[int] = typer.Option(None, "--min-stars", help="Minimum stars"),
    max_stars: Optional[int] = typer.Option(None, "--max-stars", help="Maximum stars"),
    sort_by: str = typer.Option("stars", "--sort", help="Sort by: stars, forks, updated, name"),
    limit: int = typer.Option(20, "-n", "--limit", help="Number of results"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Search for repositories."""
    check_api_available()
    
    params = {
        "q": query,
        "language": language,
        "min_stars": min_stars,
        "max_stars": max_stars,
        "sort_by": sort_by,
        "limit": limit,
    }
    
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    
    try:
        response = requests.get(f"{API_BASE}/search", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if json_output:
            console.print_json(data=data)
            return
        
        repos = data.get("repos", [])
        total = data.get("pagination", {}).get("total", 0)
        
        if not repos:
            console.print("[yellow]No repositories found.[/yellow]")
            return
        
        # Create table
        table = Table(title=f"🔍 Search Results: '{query}' ({total} total)")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Language", style="green")
        table.add_column("⭐ Stars", justify="right")
        table.add_column("🍴 Forks", justify="right")
        table.add_column("Description", style="dim")
        
        for repo in repos:
            name = f"[link={repo['url']}]{repo['full_name']}[/link]"
            table.add_row(
                name,
                repo.get("language", "") or "",
                f"{repo.get('stars', 0):,}",
                f"{repo.get('forks', 0):,}",
                (repo.get("description", "") or "")[:50] + ("..." if len(repo.get("description", "") or "") > 50 else ""),
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(repos)} of {total} results[/dim]")
        
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def trending(
    period: str = typer.Option("today", "-p", "--period", help="Period: today, week, month"),
    language: Optional[str] = typer.Option(None, "-l", "--language", help="Filter by language"),
    limit: int = typer.Option(25, "-n", "--limit", help="Number of results"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get trending repositories."""
    check_api_available()
    
    params = {
        "period": period,
        "language": language,
        "limit": limit,
    }
    params = {k: v for k, v in params.items() if v is not None}
    
    try:
        response = requests.get(f"{API_BASE}/trending", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if json_output:
            console.print_json(data=data)
            return
        
        repos = data.get("repos", [])
        
        if not repos:
            console.print("[yellow]No trending repositories found.[/yellow]")
            return
        
        table = Table(title=f"🔥 Trending ({data.get('period', 'today')}) - {data.get('language', 'all')}")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Language", style="green")
        table.add_column("⭐ Stars", justify="right")
        table.add_column("🍴 Forks", justify="right")
        
        for idx, repo in enumerate(repos, 1):
            name = f"[link={repo['url']}]{repo['full_name']}[/link]"
            table.add_row(
                str(idx),
                name,
                repo.get("language", "") or "",
                f"{repo.get('stars', 0):,}",
                f"{repo.get('forks', 0):,}",
            )
        
        console.print(table)
        
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def paths():
    """List learning paths."""
    check_api_available()
    
    try:
        response = requests.get(f"{API_BASE}/paths", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        paths = data.get("paths", [])
        
        if not paths:
            console.print("[yellow]No learning paths available.[/yellow]")
            return
        
        table = Table(title="📚 Learning Paths")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="bold")
        table.add_column("Description")
        table.add_column("Duration", style="green")
        table.add_column("Stages", justify="center")
        
        for path in paths:
            stages = len(path.get("stages", []))
            table.add_row(
                path.get("id", ""),
                path.get("title", ""),
                path.get("description", ""),
                path.get("duration", ""),
                str(stages),
            )
        
        console.print(table)
        
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def stats():
    """Show database statistics."""
    check_api_available()
    
    try:
        response = requests.get(f"{API_BASE}/search/stats", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        console.print(Panel(
            f"[bold]📊 Repository Statistics[/bold]\n\n"
            f"Total Repositories: [cyan]{data.get('total_repos', 0):,}[/cyan]\n"
            f"Languages: [green]{data.get('languages', 0)}[/green]\n"
            f"Max Stars: [yellow]{data.get('max_stars', 0):,}[/yellow]",
            title="RepoDiscoverAI",
            border_style="blue",
        ))
        
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def languages():
    """List available programming languages."""
    check_api_available()
    
    try:
        response = requests.get(f"{API_BASE}/search/languages", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        languages = data.get("languages", [])
        
        if not languages:
            console.print("[yellow]No languages found.[/yellow]")
            return
        
        table = Table(title="💻 Programming Languages")
        table.add_column("Language", style="green")
        table.add_column("Repositories", justify="right")
        
        for lang in languages:
            table.add_row(
                lang.get("language", ""),
                f"{lang.get('count', 0):,}",
            )
        
        console.print(table)
        
    except requests.RequestException as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
