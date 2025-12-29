#!/usr/bin/env python3
"""
Command-line monitoring client for BearishVanish
Real-time display of simulation and analysis progress
"""

import sys
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.layout import Layout
from rich.text import Text


class MonitorCLI:
    """CLI monitoring client"""

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
        self.console = Console()

    async def get_status(self):
        """Get system status"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/status", timeout=5.0)
                return response.json()
            except Exception as e:
                return {"error": str(e)}

    async def get_processes(self, status: Optional[str] = None):
        """Get all processes"""
        async with httpx.AsyncClient() as client:
            try:
                params = {"status": status} if status else {}
                response = await client.get(f"{self.base_url}/processes", params=params, timeout=5.0)
                return response.json()
            except Exception as e:
                return {"error": str(e)}

    async def get_process(self, process_id: str):
        """Get specific process"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/process/{process_id}", timeout=5.0)
                return response.json()
            except Exception as e:
                return {"error": str(e)}

    def format_time(self, seconds: float) -> str:
        """Format seconds as human-readable time"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

    def create_status_table(self, processes: list) -> Table:
        """Create a rich table showing all processes"""
        table = Table(title="BearishVanish Process Monitor", show_header=True, header_style="bold magenta")

        table.add_column("Process ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Progress", style="blue")
        table.add_column("Elapsed", style="white")
        table.add_column("ETA", style="white")
        table.add_column("Message", style="white")

        for proc in processes:
            # Status indicator
            status = proc.get("status", "unknown")
            if status == "running":
                status_str = "🔄 Running"
                status_style = "bold yellow"
            elif status == "completed":
                status_str = "✅ Done"
                status_style = "bold green"
            elif status == "failed":
                status_str = "❌ Failed"
                status_style = "bold red"
            else:
                status_str = "⏸️  Idle"
                status_style = "dim"

            # Progress
            current = proc.get("current_progress", 0)
            total = proc.get("total_items", 0)
            if total > 0:
                pct = (current / total) * 100
                progress_str = f"{current}/{total} ({pct:.1f}%)"
            else:
                progress_str = f"{current}"

            # Time
            elapsed = proc.get("elapsed_time", 0)
            eta = proc.get("eta_seconds")
            eta_str = self.format_time(eta) if eta else "—"

            table.add_row(
                proc.get("process_id", "unknown")[:20],
                proc.get("process_type", "unknown"),
                Text(status_str, style=status_style),
                progress_str,
                self.format_time(elapsed),
                eta_str,
                proc.get("message", "")[:50]
            )

        return table

    async def show_status_once(self):
        """Show current status once and exit"""
        status = await self.get_status()

        if "error" in status:
            self.console.print(f"[red]Error connecting to API:[/red] {status['error']}")
            self.console.print("[yellow]Is the monitoring server running?[/yellow]")
            self.console.print(f"[dim]Try: python3 monitoring/api_server.py[/dim]")
            return

        # Show summary
        self.console.print(Panel.fit(
            f"[green]Total Processes:[/green] {status['total_processes']}\n"
            f"[yellow]Running:[/yellow] {status['running_processes']}\n"
            f"[blue]Completed:[/blue] {status['completed_processes']}\n"
            f"[red]Failed:[/red] {status['failed_processes']}",
            title="System Status",
            border_style="blue"
        ))

        # Show processes
        processes_data = await self.get_processes()
        if "processes" in processes_data:
            processes = processes_data["processes"]
            if processes:
                table = self.create_status_table(processes)
                self.console.print(table)
            else:
                self.console.print("[dim]No processes found[/dim]")

    async def watch_status(self, refresh_rate: float = 2.0):
        """Watch status with live updates"""
        with Live(console=self.console, refresh_per_second=1/refresh_rate) as live:
            while True:
                try:
                    status = await self.get_status()

                    if "error" in status:
                        live.update(Panel(
                            f"[red]Error:[/red] {status['error']}\n\n"
                            "[yellow]Is the monitoring server running?[/yellow]",
                            title="Connection Error",
                            border_style="red"
                        ))
                        await asyncio.sleep(refresh_rate)
                        continue

                    # Get processes
                    processes_data = await self.get_processes()
                    processes = processes_data.get("processes", [])

                    # Create layout
                    layout = Layout()

                    # Summary panel
                    summary = Panel(
                        f"[green]Total:[/green] {status['total_processes']}  "
                        f"[yellow]Running:[/yellow] {status['running_processes']}  "
                        f"[blue]Completed:[/blue] {status['completed_processes']}  "
                        f"[red]Failed:[/red] {status['failed_processes']}\n"
                        f"[dim]Last update: {datetime.now().strftime('%H:%M:%S')}[/dim]",
                        title="System Status",
                        border_style="blue"
                    )

                    # Process table
                    if processes:
                        table = self.create_status_table(processes)
                        layout.split_column(
                            Layout(summary, size=5),
                            Layout(table)
                        )
                    else:
                        layout.split_column(
                            Layout(summary, size=5),
                            Layout(Panel("[dim]No active processes[/dim]", border_style="dim"))
                        )

                    live.update(layout)
                    await asyncio.sleep(refresh_rate)

                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Monitoring stopped[/yellow]")
                    break
                except Exception as e:
                    live.update(Panel(f"[red]Error:[/red] {str(e)}", border_style="red"))
                    await asyncio.sleep(refresh_rate)

    async def watch_process(self, process_id: str, refresh_rate: float = 1.0):
        """Watch a specific process"""
        with Live(console=self.console, refresh_per_second=1/refresh_rate) as live:
            while True:
                try:
                    proc = await self.get_process(process_id)

                    if "error" in proc or "detail" in proc:
                        live.update(Panel(
                            f"[red]Process not found:[/red] {process_id}",
                            border_style="red"
                        ))
                        await asyncio.sleep(refresh_rate)
                        continue

                    # Create detailed view
                    status = proc.get("status", "unknown")
                    current = proc.get("current_progress", 0)
                    total = proc.get("total_items", 0)
                    elapsed = proc.get("elapsed_time", 0)
                    eta = proc.get("eta_seconds")

                    # Progress bar
                    if total > 0:
                        pct = (current / total) * 100
                        bar_width = 40
                        filled = int((current / total) * bar_width)
                        bar = "█" * filled + "░" * (bar_width - filled)
                        progress_str = f"{bar} {pct:.1f}%"
                    else:
                        progress_str = f"Items processed: {current}"

                    # Build panel content
                    content = (
                        f"[cyan]Process ID:[/cyan] {proc.get('process_id', 'unknown')}\n"
                        f"[green]Type:[/green] {proc.get('process_type', 'unknown')}\n"
                        f"[yellow]Status:[/yellow] {status}\n\n"
                        f"[blue]Progress:[/blue]\n{progress_str}\n"
                        f"{current} / {total} items\n\n"
                        f"[white]Elapsed:[/white] {self.format_time(elapsed)}\n"
                        f"[white]ETA:[/white] {self.format_time(eta) if eta else '—'}\n\n"
                        f"[dim]Message:[/dim] {proc.get('message', '')}\n"
                        f"[dim]Last update: {datetime.now().strftime('%H:%M:%S')}[/dim]"
                    )

                    if proc.get("error_message"):
                        content += f"\n\n[red]Error:[/red] {proc['error_message']}"

                    live.update(Panel(
                        content,
                        title=f"Monitoring: {process_id}",
                        border_style="blue" if status == "running" else "green" if status == "completed" else "red"
                    ))

                    # Stop watching if completed or failed
                    if status in ["completed", "failed"]:
                        await asyncio.sleep(2)
                        break

                    await asyncio.sleep(refresh_rate)

                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Monitoring stopped[/yellow]")
                    break
                except Exception as e:
                    live.update(Panel(f"[red]Error:[/red] {str(e)}", border_style="red"))
                    await asyncio.sleep(refresh_rate)


async def main():
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor BearishVanish simulation and analysis processes"
    )
    parser.add_argument(
        "--url", "-u",
        default="http://localhost:8765",
        help="Monitoring API base URL (default: http://localhost:8765)"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Watch mode with live updates"
    )
    parser.add_argument(
        "--process", "-p",
        help="Watch specific process ID"
    )
    parser.add_argument(
        "--refresh", "-r",
        type=float,
        default=2.0,
        help="Refresh rate in seconds (default: 2.0)"
    )

    args = parser.parse_args()

    cli = MonitorCLI(base_url=args.url)

    if args.process:
        await cli.watch_process(args.process, refresh_rate=args.refresh)
    elif args.watch:
        await cli.watch_status(refresh_rate=args.refresh)
    else:
        await cli.show_status_once()


if __name__ == "__main__":
    asyncio.run(main())
