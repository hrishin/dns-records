#!/usr/bin/env python3
"""
DNS Records Manager - Demo Script

This script demonstrates the functionality of the DNS Records Manager
using the mock provider for safe testing and demonstration.
"""

import os
import tempfile
import csv
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from dns_manager import DNSManager

# Initialize rich console
console = Console()


def create_demo_config():
    """Create a demo configuration file."""
    config = {
        "dns_providers": {"mock": {}},  # Use mock provider for demo
        "default_provider": "mock",
        "logging": {"level": "INFO", "file": "demo.log"},
    }

    # Create config file
    config_file = "demo_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return config_file


def create_demo_csv():
    """Create a demo CSV file with sample records."""
    csv_file = "demo_records.csv"

    # Sample records for demonstration
    records = [
        ["FQDN", "IPv4"],
        ["web1.ib.bigbank.com", "10.33.1.10"],
        ["web2.ib.bigbank.com", "10.33.1.11"],
        ["db1.ib.bigbank.com", "10.33.2.10"],
        ["db2.ib.bigbank.com", "10.33.2.11"],
        ["monitoring.ib.bigbank.com", "10.33.3.10"],
        ["logging.ib.bigbank.com", "10.33.3.11"],
    ]

    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(records)

    return csv_file


def display_demo_header():
    """Display the demo header."""
    console.print(
        Panel.fit(
            "[bold blue]DNS Records Manager - Demo[/bold blue]\n"
            "[cyan]Automated DNS Record Management for ib.bigbank.com[/cyan]",
            border_style="blue",
        )
    )
    console.print()


def display_current_state(dns_manager, zone):
    """Display the current DNS zone state."""
    console.print("[bold]Current DNS Zone State:[/bold]")

    try:
        current_records = dns_manager.dns_client.get_records(zone)

        if not current_records:
            console.print("[yellow]No DNS records found in zone[/yellow]")
            return

        table = Table(title=f"DNS Records in {zone}")
        table.add_column("FQDN", style="cyan")
        table.add_column("IPv4", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("TTL", style="yellow")

        for record in current_records:
            table.add_row(
                record["fqdn"],
                record["ipv4"],
                record.get("type", "A"),
                str(record.get("ttl", "300")),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error retrieving current state: {e}[/red]")

    console.print()


def display_csv_content(csv_file):
    """Display the CSV file content."""
    console.print("[bold]CSV Input File:[/bold]")

    try:
        with open(csv_file, "r") as f:
            content = f.read()

        console.print(Panel(content, title="CSV Content", border_style="green"))

    except Exception as e:
        console.print(f"[red]Error reading CSV file: {e}[/red]")

    console.print()


def run_dry_run_demo(dns_manager, csv_file, zone):
    """Run a dry-run demo to show what changes would be made."""
    console.print("[bold]Running Dry-Run Demo...[/bold]")
    console.print(
        "[yellow]This will show what changes would be made without applying them[/yellow]"
    )
    console.print()

    try:
        console.print("[green]Processing CSV file...[/green]")
        result = dns_manager.process_csv(csv_file, zone, dry_run=True)
        if result:
            console.print("[green]✓ Dry-run completed successfully![/green]")
        else:
            console.print("[red]✗ Dry-run failed![/red]")

    except Exception as e:
        console.print(f"[red]Error during dry-run: {e}[/red]")

    console.print()


def run_live_demo(dns_manager, csv_file, zone):
    """Run a live demo to actually apply the changes."""
    console.print("[bold]Running Live Demo...[/bold]")
    console.print("[green]This will actually apply the DNS changes[/green]")
    console.print()

    try:
        # Process CSV with actual changes

        console.print("[green]Applying DNS changes..[/green]")
        result = dns_manager.process_csv(csv_file, zone, dry_run=False)

        if result:
            console.print("[green]✓ Live demo completed successfully![/green]")
        else:
            console.print("[red]✗ Live demo failed![/red]")

    except Exception as e:
        console.print(f"[red]Error during live demo: {e}[/red]")

    console.print()


def display_final_state(dns_manager, zone):
    """Display the final DNS zone state after changes."""
    console.print("[bold]Final DNS Zone State:[/bold]")

    try:
        current_records = dns_manager.dns_client.get_records(zone)

        if not current_records:
            console.print("[yellow]No DNS records found in zone[/yellow]")
            return

        table = Table(title=f"DNS Records in {zone} (After Changes)")
        table.add_column("FQDN", style="cyan")
        table.add_column("IPv4", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("TTL", style="yellow")

        for record in current_records:
            table.add_row(
                record["fqdn"],
                record["ipv4"],
                record.get("type", "A"),
                str(record.get("ttl", "300")),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error retrieving final state: {e}[/red]")

    console.print()


def cleanup_demo_files(config_file, csv_file):
    """Clean up demo files."""
    try:
        if os.path.exists(config_file):
            os.remove(config_file)
        if os.path.exists(csv_file):
            os.remove(csv_file)
        console.print("[blue]Demo files cleaned up[/blue]")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not clean up demo files: {e}[/yellow]")


def main():
    """Main demo function."""
    display_demo_header()

    # Create demo files
    config_file = create_demo_config()
    csv_file = create_demo_csv()

    try:
        # Initialize DNS manager
        console.print("[blue]Initializing DNS Manager...[/blue]")
        dns_manager = DNSManager(config_file)
        console.print("[green]✓ DNS Manager initialized successfully[/green]")
        console.print()

        # Set zone
        zone = "ib.bigbank.com"

        # Display initial state
        display_current_state(dns_manager, zone)

        # Display CSV content
        display_csv_content(csv_file)

        # Run dry-run demo
        run_dry_run_demo(dns_manager, csv_file, zone)

        # Ask user if they want to proceed with live demo
        console.print("[bold]Would you like to proceed with the live demo?[/bold]")
        console.print("[yellow]This will actually create/update DNS records[/yellow]")
        response = input("Proceed? (yes/no): ").lower().strip()

        if response in ["yes", "y"]:
            # Run live demo
            run_live_demo(dns_manager, csv_file, zone)

            # Display final state
            display_final_state(dns_manager, zone)
        else:
            console.print("[yellow]Live demo skipped[/yellow]")

        # Show demo summary
        console.print(
            Panel.fit(
                "[bold green]Demo Summary[/bold green]\n"
                "✓ DNS Manager initialized\n"
                "✓ CSV file processed\n"
                "✓ Changes analyzed\n"
                "✓ Mock provider used (no real DNS changes)\n"
                "✓ All operations logged",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]Demo failed with error: {e}[/red]")
        console.print("[yellow]Check the logs for more details[/yellow]")

    finally:
        # Clean up demo files
        cleanup_demo_files(config_file, csv_file)

        console.print()
        console.print("[bold blue]Demo completed![/bold blue]")
        console.print(
            "[cyan]Check the generated log files for detailed information[/cyan]"
        )


if __name__ == "__main__":
    main()
