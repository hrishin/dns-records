#!/usr/bin/env python3
"""
DNS Records Manager - Automated DNS record management for ib.bigbank.com zone

This script processes CSV files containing FQDN and IPv4 mappings to create,
update, and delete DNS records in an idempotent and safe manner.
"""

import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..providers.dns_client import DNSClient
from .record_manager import RecordManager

# Initialize rich console and logger
console = Console()
logger = logging.getLogger(__name__)


class DNSManager:
    """Main DNS management class that orchestrates the entire process."""

    def __init__(self, config: Dict):
        """Initialize the DNS manager with configuration."""
        self.config = config
        self.dns_client = DNSClient(self.config)
        self.record_manager = RecordManager(self.dns_client)

    def process_records(
        self,
        records: List[Dict[str, str]],
        zone: str,
        dry_run: bool = False,
        output_file: Optional[str] = None,
    ) -> bool:
        """Process DNS records."""
        try:
            if not records:
                console.print("[red]No valid records provided[/red]")
                return False

            console.print(f"[green]Fetching current DNS records...[/green]")
            current_records = self.dns_client.get_records(zone)
            console.print(
                f"[blue]Found {len(current_records)} existing DNS records[/blue]"
            )

            # Analyze changes
            changes = self.record_manager.analyze_changes(
                current_records, records, zone
            )

            # Display changes summary
            self._display_changes_summary(changes)

            if dry_run:
                console.print(
                    "[yellow]DRY RUN MODE - No changes will be applied[/yellow]"
                )

                if output_file:
                    self._save_dry_run_output(changes, output_file)
                    console.print(
                        f"[green]Dry run output saved to: {output_file}[/green]"
                    )

                return True

            if changes["total_changes"] > 0:
                success = self._apply_changes(changes, zone)
                if success:
                    console.print(
                        "[green]All DNS changes applied successfully![/green]"
                    )
                    return True
                else:
                    console.print("[red]Some DNS changes failed to apply[/red]")
                    return False
            else:
                console.print(
                    "[green]No changes required - DNS records are up to date[/green]"
                )
                return True

        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            console.print(f"[red]Error: {e}[/red]")
            return False

    def _display_changes_summary(self, changes: Dict) -> bool:
        """Ask user to confirm changes."""
        
        console.print(
            f"\n[bold]Changes summary:[/bold]"
        )
        console.print(
            f"\n[bold]Total {changes['total_changes']} DNS changes[/bold]"
        )

        # Show detailed changes
        if changes.get("creates", []):
            console.print(f"Total creates: {len(changes['creates'])}")
            console.print("\n[bold]Records to create:[/bold]")
            for record in changes["creates"]:
                console.print(f"  + {record['fqdn']} -> {record['ipv4']}")

        if changes.get("updates", []):
            console.print(f"Total updates: {len(changes['updates'])}")
            console.print("\n[yellow]Records to update:[/yellow]")
            for record in changes["updates"]:
                console.print(f"  ~ {record['fqdn']} -> {record['ipv4']}")

        if changes.get("deletes", []):
            console.print(f"Total deletes: {len(changes['deletes'])}")
            console.print("\n[red]Records to delete:[/red]")
            for record in changes["deletes"]:
                console.print(f"  - {record['fqdn']}")

        console.print("")

    def _apply_changes(self, changes: Dict, zone: str) -> bool:
        """Apply DNS changes."""
        success_count = 0
        total_changes = changes["total_changes"]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Applying DNS changes...", total=total_changes)

            # Apply creates
            for record in changes["creates"]:
                try:
                    self.dns_client.create_record(zone, record)
                    success_count += 1
                    progress.update(task, advance=1)
                    logger.info(f"Created record: {record['fqdn']} -> {record['ipv4']}")
                except Exception as e:
                    logger.error(f"Failed to create record {record['fqdn']}: {e}")
                    console.print(f"[red]Failed to create {record['fqdn']}: {e}[/red]")

            # Apply updates
            for record in changes["updates"]:
                try:
                    self.dns_client.update_record(zone, record)
                    success_count += 1
                    progress.update(task, advance=1)
                    logger.info(f"Updated record: {record['fqdn']} -> {record['ipv4']}")
                except Exception as e:
                    logger.error(f"Failed to update record {record['fqdn']}: {e}")
                    console.print(f"[red]Failed to update {record['fqdn']}: {e}[/red]")

            # Apply deletes
            for record in changes["deletes"]:
                try:
                    self.dns_client.delete_record(zone, record)
                    success_count += 1
                    progress.update(task, advance=1)
                    logger.info(f"Deleted record: {record['fqdn']}")
                except Exception as e:
                    logger.error(f"Failed to delete record {record['fqdn']}: {e}")
                    console.print(f"[red]Failed to delete {record['fqdn']}: {e}[/red]")

        console.print(
            f"[blue]Successfully applied {success_count}/{total_changes} changes[/blue]"
        )
        return success_count == total_changes

    def _save_dry_run_output(self, changes: Dict, output_file: str):
        """Save dry run output to a file."""
        try:
            with open(output_file, "w") as f:
                f.write("=" * 60 + "\n")
                f.write("DNS RECORDS MANAGER - DRY RUN SUMMARY\n")
                f.write("=" * 60 + "\n\n")

                f.write(f"Total Changes: {changes['total_changes']}\n")
                f.write(
                    f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                )

                if changes.get("creates", []):
                    f.write("RECORDS TO CREATE:\n")
                    f.write("-" * 20 + "\n")
                    for record in changes["creates"]:
                        f.write(f"  + {record['fqdn']:<30} -> {record['ipv4']}\n")
                    f.write("\n")

                if changes.get("updates", []):
                    f.write("RECORDS TO UPDATE:\n")
                    f.write("-" * 20 + "\n")
                    for record in changes["updates"]:
                        f.write(f"  ~ {record['fqdn']:<30} -> {record['ipv4']}\n")
                    f.write("\n")

                if changes.get("deletes", []):
                    f.write("RECORDS TO DELETE:\n")
                    f.write("-" * 20 + "\n")
                    for record in changes["deletes"]:
                        f.write(f"  - {record['fqdn']}\n")
                    f.write("\n")

                if changes.get("no_changes", []):
                    f.write("RECORDS WITH NO CHANGES:\n")
                    f.write("-" * 25 + "\n")
                    for record in changes["no_changes"]:
                        f.write(f"  = {record['fqdn']}\n")
                    f.write("\n")

                f.write("=" * 60 + "\n")
                f.write("END OF DRY RUN SUMMARY\n")
                f.write("=" * 60 + "\n")

            logger.info(f"Dry run output saved to: {output_file}")
        except Exception as e:
            logger.error(f"Failed to save dry run output to {output_file}: {e}")
            console.print(
                f"[red]Warning: Failed to save dry run output to {output_file}: {e}[/red]"
            )


if __name__ == "__main__":
    main()
