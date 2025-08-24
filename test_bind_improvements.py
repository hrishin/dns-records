#!/usr/bin/env python3
"""
Test script for improved BIND DNS provider with RNDC support.
This demonstrates the enhanced reliability compared to the original nsupdate-only approach.
"""

import logging
import sys
from dns_client import BINDProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_bind_provider():
    """Test the improved BIND provider."""

    # Configuration for BIND provider
    config = {
        "nameserver": "127.0.0.1",
        "port": 53,
        # "key_file": "/etc/bind/rndc.key",  # Optional
        # "key_name": "rndc-key",            # Optional
        "zone_file": "./zones/ib.bigbank.com.zone",  # Path to zone file
    }

    try:
        print("Initializing improved BIND provider...")
        provider = BINDProvider(config)

        print(f"RNDC available: {provider.rndc_available}")

        # Test zone status check
        zone = "ib.bigbank.com"
        print(f"\nChecking zone status for {zone}...")
        status = provider.check_zone_status(zone)
        print(f"Zone status: {status}")

        # Test record operations
        test_record = {
            "fqdn": "test.example.com",
            "ipv4": "192.168.1.100",
            "type": "A",
            "ttl": 300,
        }

        print(f"\nTesting record creation for {test_record['fqdn']}...")
        try:
            success = provider.create_record(zone, test_record)
            print(f"Record creation: {'SUCCESS' if success else 'FAILED'}")
        except Exception as e:
            print(f"Record creation failed: {e}")

        # Test getting records
        print(f"\nRetrieving records from {zone}...")
        try:
            records = provider.get_records(zone)
            print(f"Found {len(records)} records")
            for record in records[:5]:  # Show first 5 records
                print(f"  {record['fqdn']} -> {record['ipv4']}")
        except Exception as e:
            print(f"Failed to get records: {e}")

        print("\nTest completed!")

    except Exception as e:
        print(f"Error initializing BIND provider: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure BIND tools are installed: sudo apt-get install bind9utils")
        print("2. Check if RNDC is available: which rndc")
        print("3. Verify zone file path exists and is writable")
        print("4. Ensure proper permissions for zone file operations")
        return False

    return True


if __name__ == "__main__":
    success = test_bind_provider()
    sys.exit(0 if success else 1)
