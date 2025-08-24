#!/usr/bin/env python3
"""
DNS Records Manager - Command Line Interface

Main entry point for the DNS Records Manager CLI.
"""

import argparse
import logging
import sys
from pathlib import Path

from ..core.dns_manager import DNSManager


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DNS Records Manager - Automated DNS record management"
    )
    parser.add_argument(
        "--config", "-c",
        default="configs/config.yaml",
        help="Configuration file path (default: config.yaml)"
    )
    parser.add_argument(
        "--zone", "-z",
        required=True,
        help="DNS zone to manage"
    )
    parser.add_argument(
        "--csv", "-f",
        required=True,
        help="CSV file containing DNS records"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    parser.add_argument(
        "--output-file", "-o",
        help="File to save dry run diff output (only used with --dry-run)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.output_file and not args.dry_run:
        print("Error: --output-file can only be used with --dry-run")
        sys.exit(1)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Validate inputs
    if not Path(args.config).exists():
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)

    if not Path(args.csv).exists():
        print(f"Error: CSV file '{args.csv}' not found")
        sys.exit(1)

    try:
        # Initialize DNS manager
        dns_manager = DNSManager(args.config)
        
        # Process CSV
        success = dns_manager.process_csv(
            args.csv, 
            args.zone, 
            dry_run=args.dry_run,
            output_file=args.output_file if args.dry_run else None
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


if __name__ == "__main__":
    main()
