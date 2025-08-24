#!/usr/bin/env python3
"""
DNS Records Manager - Command Line Interface

Main entry point for the DNS Records Manager CLI.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict

import yaml

from ..core.dns_manager import DNSManager
from ..parsers.csv import CSVParser

logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DNS Records Manager - Automated DNS record management"
    )

    parser.add_argument(
        "--config",
        "-c",
        default="configs/config.yaml",
        help="Configuration file path (default: config.yaml)",
    )

    parser.add_argument("--zone", "-z", required=True, help="DNS zone to manage")

    parser.add_argument(
        "--csv", "-f", required=True, help="CSV file containing DNS records"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )

    parser.add_argument(
        "--output-file",
        "-o",
        help="File to save dry run diff output (only used with --dry-run)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.output_file and not args.dry_run:
        print("Error: --output-file can only be used with --dry-run")
        sys.exit(1)

    if not Path(args.config).exists():
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)

    if not Path(args.csv).exists():
        print(f"Error: CSV file '{args.csv}' not found")
        sys.exit(1)

    config = load_config(args.config)
    config_logger(config)

    try:
        dns_manager = DNSManager(config)
        records = CSVParser(args.csv).parse()

        success = dns_manager.process_records(
            records,
            args.zone,
            dry_run=args.dry_run,
            output_file=args.output_file if args.dry_run else None,
        )

        if success:
            print("DNS record management completed successfully")
            sys.exit(0)
        else:
            print("DNS record management failed")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.warning(f"Config file {config_path} not found, using defaults")
        return get_default_config()
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file: {e}")
        sys.exit(1)


def get_default_config() -> Dict:
    """Return default configuration."""
    return {
        "dns_providers": {"mock": {}},
        "default_provider": "mock",
        "logging": {"level": "INFO", "file": "dns_records_manager.log"},
    }


def config_logger(config: Dict):
    """Configure logging."""
    logging_config = config.get("logging", None)
    if logging_config:
        log_level = logging_config.get("level", "INFO")
        log_file = logging_config.get("file", "dns_records_manager.log")

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


if __name__ == "__main__":
    main()
