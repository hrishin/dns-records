#!/usr/bin/env python3
"""
DNS Records Manager - Automated DNS record management for ib.bigbank.com zone

This script processes CSV files containing FQDN and IPv4 mappings to create,
update, and delete DNS records in an idempotent and safe manner.
"""

import argparse
import csv
import ipaddress
import logging
import re
import sys
from pathlib import Path
from datetime import datetime

from typing import Dict, List, Optional, Tuple
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..providers.dns_client import DNSClient
from .record_manager import RecordManager
from ..utils.validators import validate_fqdn, validate_ipv4

# Initialize rich console and logger
console = Console()
logger = logging.getLogger(__name__)


class DNSManager:
    """Main DNS management class that orchestrates the entire process."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        """Initialize the DNS manager with configuration."""
        self.config = self._load_config(config_path)
        self.dns_client = DNSClient(self.config)
        self.record_manager = RecordManager(self.dns_client)
        self._config_logger()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}")
            sys.exit(1)

    def _config_logger(self):
        """Configure logging."""
        logging_config = self.config.get("logging", {})
        if logging_config:
            log_level = logging_config.get("level", "INFO")
            log_file = logging_config.get("file", "dns_manager.log")

            logging.basicConfig(
                level=log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler(sys.stdout),
                ],
            )
            return

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

    def _get_default_config(self) -> Dict:
        """Return default configuration."""
        return {
            "dns_providers": {
                "aws": {
                    "access_key_id": "",
                    "secret_access_key": "",
                    "region": "us-east-1",
                }
            },
            "default_provider": "aws",
            "logging": {"level": "INFO", "file": "dns_manager.log"},
        }

    def process_csv(self, csv_path: str, zone: str, dry_run: bool = False, output_file: Optional[str] = None) -> bool:
        """Process CSV file and manage DNS records."""
        try:
            # Parse CSV file
            records = self._parse_csv(csv_path)
            if not records:
                console.print("[red]No valid records found in CSV file[/red]")
                return False

            console.print(
                f"[green]Successfully parsed {len(records)} records from CSV[/green]"
            )
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
                
                # Save dry run output to file if specified
                if output_file:
                    self._save_dry_run_output(changes, output_file)
                    console.print(f"[green]Dry run output saved to: {output_file}[/green]")
                
                return True

            # Apply changes
            if changes["total_changes"] > 0:
                self._confirm_changes(changes)
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

    def _parse_csv(self, csv_path: str) -> List[Dict[str, str]]:
        """Parse CSV file and validate records."""
        records = []

        try:
            with open(csv_path, "r") as f:
                reader = csv.DictReader(f)

                # Validate CSV structure
                if "FQDN" not in reader.fieldnames or "IPv4" not in reader.fieldnames:
                    raise ValueError("CSV must contain 'FQDN' and 'IPv4' columns")

                for row_num, row in enumerate(
                    reader, start=2
                ):  # Start at 2 to account for header
                    fqdn = row["FQDN"].strip()
                    ipv4 = row["IPv4"].strip()

                    # Validate FQDN and IPv4
                    if not validate_fqdn(fqdn):
                        console.print(
                            f"[yellow]Warning: Invalid FQDN '{fqdn}' at row {row_num}, skipping[/yellow]"
                        )
                        continue

                    if not validate_ipv4(ipv4):
                        console.print(
                            f"[yellow]Warning: Invalid IPv4 '{ipv4}' at row {row_num}, skipping[/yellow]"
                        )
                        continue

                    records.append({"fqdn": fqdn, "ipv4": ipv4, "type": "A"})

        except FileNotFoundError:
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        except Exception as e:
            raise Exception(f"Error parsing CSV: {e}")

        return records

    def _display_changes_summary(self, changes: Dict):
        """Display a summary of planned changes."""
        table = Table(title="DNS Changes Summary")
        table.add_column("Operation", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Details", style="white")

        if changes["creates"]:
            table.add_row(
                "Create",
                str(len(changes["creates"])),
                ", ".join([r["fqdn"] for r in changes["creates"]]),
            )

        if changes["updates"]:
            table.add_row(
                "Update",
                str(len(changes["updates"])),
                ", ".join([r["fqdn"] for r in changes["updates"]]),
            )

        if changes["deletes"]:
            table.add_row(
                "Delete",
                str(len(changes["deletes"])),
                ", ".join([r["fqdn"] for r in changes["deletes"]]),
            )

        if changes["no_changes"]:
            table.add_row(
                "No Change",
                str(len(changes["no_changes"])),
                ", ".join([r["fqdn"] for r in changes["no_changes"]]),
            )

        console.print(table)
        console.print(f"\n[bold]Total changes: {changes['total_changes']}[/bold]")

    def _confirm_changes(self, changes: Dict) -> bool:
        """Ask user to confirm changes."""
        console.print(
            f"\n[bold]About to apply {changes['total_changes']} DNS changes[/bold]"
        )

        # Show detailed changes
        if changes.get("creates", []):
            console.print("\n[green]Records to create:[/green]")
            for record in changes["creates"]:
                console.print(f"  + {record['fqdn']} -> {record['ipv4']}")

        if changes.get("updates", []):
            console.print("\n[yellow]Records to update:[/yellow]")
            for record in changes["updates"]:
                console.print(f"  ~ {record['fqdn']} -> {record['ipv4']}")

        if changes.get("deletes", []):
            console.print("\n[red]Records to delete:[/red]")
            for record in changes["deletes"]:
                console.print(f"  - {record['fqdn']}")

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
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
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
            console.print(f"[red]Warning: Failed to save dry run output to {output_file}: {e}[/red]")


if __name__ == "__main__":
    main()
