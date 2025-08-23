#!/usr/bin/env python3
"""
Test suite for DNS Records Manager

This module provides comprehensive testing for all components of the DNS manager.
"""

import unittest
import tempfile
import os
import csv
import yaml
from unittest.mock import Mock, patch, MagicMock

# Import the modules to test
from dns_manager import DNSManager
from dns_client import DNSClient, MockDNSProvider, BINDProvider
from record_manager import RecordManager
from validators import validate_fqdn, validate_ipv4, validate_csv_row


class TestValidators(unittest.TestCase):
    """Test the validation functions."""

    def test_validate_fqdn_valid(self):
        """Test valid FQDN validation."""
        valid_fqdns = [
            "example.com",
            "sub.example.com",
            "machine1.mgmt.ib.bigbank.com",
            "a.b.c.d.e.f.g.h.i.j.k.l.m.n.o.p.q.r.s.t.u.v.w.x.y.z.com",
        ]

        for fqdn in valid_fqdns:
            with self.subTest(fqdn=fqdn):
                self.assertTrue(validate_fqdn(fqdn))

    def test_validate_fqdn_invalid(self):
        """Test invalid FQDN validation."""
        invalid_fqdns = [
            "",  # Empty
            "single",  # Single label
            ".example.com",  # Starts with dot
            "example.com.",  # Ends with dot
            "example..com",  # Consecutive dots
            "example-.com",  # Ends with hyphen
            "-example.com",  # Starts with hyphen
            "123.example.com",  # Starts with digit
            "a" * 64 + ".com",  # Label too long
        ]

        for fqdn in invalid_fqdns:
            with self.subTest(fqdn=fqdn):
                self.assertFalse(validate_fqdn(fqdn))

    def test_validate_ipv4_valid(self):
        """Test valid IPv4 validation."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.0",
            "172.16.0.1",
            "127.0.0.1",
            "0.0.0.0",
            "255.255.255.255",
        ]

        for ip in valid_ips:
            with self.subTest(ip=ip):
                self.assertTrue(validate_ipv4(ip))

    def test_validate_ipv4_invalid(self):
        """Test invalid IPv4 validation."""
        invalid_ips = [
            "",  # Empty
            "256.1.2.3",  # Octet > 255
            "1.2.3.256",  # Octet > 255
            "1.2.3",  # Too few octets
            "1.2.3.4.5",  # Too many octets
            "1.2.3.abc",  # Non-numeric
            "192.168.1",  # Incomplete
            "192.168.1.",  # Trailing dot
        ]

        for ip in invalid_ips:
            with self.subTest(ip=ip):
                self.assertFalse(validate_ipv4(ip))

    def test_validate_csv_row_valid(self):
        """Test valid CSV row validation."""
        valid_row = {"FQDN": "example.com", "IPv4": "192.168.1.1"}
        is_valid, errors = validate_csv_row(valid_row, 1)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_csv_row_invalid(self):
        """Test invalid CSV row validation."""
        invalid_rows = [
            ({"FQDN": "", "IPv4": "192.168.1.1"}, "Empty FQDN"),
            ({"FQDN": "example.com", "IPv4": ""}, "Empty IPv4"),
            ({"FQDN": "invalid..fqdn", "IPv4": "192.168.1.1"}, "Invalid FQDN"),
            ({"FQDN": "example.com", "IPv4": "256.1.2.3"}, "Invalid IPv4"),
            ({"IPv4": "192.168.1.1"}, "Missing FQDN"),
            ({"FQDN": "example.com"}, "Missing IPv4"),
        ]

        for row, description in invalid_rows:
            with self.subTest(description=description):
                is_valid, errors = validate_csv_row(row, 1)
                self.assertFalse(is_valid)
                self.assertGreater(len(errors), 0)


class TestMockDNSProvider(unittest.TestCase):
    """Test the mock DNS provider."""

    def setUp(self):
        """Set up test fixtures."""
        self.provider = MockDNSProvider()

    def test_create_record(self):
        """Test record creation."""
        record = {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}

        result = self.provider.create_record("example.com", record)
        self.assertTrue(result)
        self.assertEqual(len(self.provider.records), 1)
        self.assertEqual(self.provider.records[0]["fqdn"], "test.example.com")

    def test_update_record(self):
        """Test record update."""
        # Create a record first
        record = {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}
        self.provider.create_record("example.com", record)

        # Update it
        updated_record = {
            "fqdn": "test.example.com",
            "ipv4": "192.168.1.2",
            "type": "A",
        }
        result = self.provider.update_record("example.com", updated_record)

        self.assertTrue(result)
        self.assertEqual(self.provider.records[0]["ipv4"], "192.168.1.2")

    def test_delete_record(self):
        """Test record deletion."""
        # Create a record first
        record = {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}
        self.provider.create_record("example.com", record)

        # Delete it
        result = self.provider.delete_record("example.com", record)

        self.assertTrue(result)
        self.assertEqual(len(self.provider.records), 0)

    def test_get_records(self):
        """Test getting records."""
        # Create some records
        records = [
            {"fqdn": "test1.example.com", "ipv4": "192.168.1.1", "type": "A"},
            {"fqdn": "test2.example.com", "ipv4": "192.168.1.2", "type": "A"},
        ]

        for record in records:
            self.provider.create_record("example.com", record)

        retrieved = self.provider.get_records("example.com")
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0]["fqdn"], "test1.example.com")
        self.assertEqual(retrieved[1]["fqdn"], "test2.example.com")


class TestBINDProvider(unittest.TestCase):
    """Test the BIND DNS provider."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = {"nameserver": "127.0.0.1", "port": 53}
        # Note: These tests will be skipped if dig/nsupdate are not available

    @unittest.skipUnless(
        os.path.exists("/usr/bin/dig") or os.path.exists("/usr/local/bin/dig"),
        "dig command not available",
    )
    def test_bind_provider_initialization(self):
        """Test BIND provider initialization."""
        try:
            provider = BINDProvider(self.config)
            self.assertIsNotNone(provider)
            self.assertEqual(provider.nameserver, "127.0.0.1")
            self.assertEqual(provider.port, 53)
        except RuntimeError as e:
            if "dig and nsupdate not found" in str(e):
                self.skipTest("BIND tools not available")
            else:
                raise

    @unittest.skipUnless(
        os.path.exists("/usr/bin/dig") or os.path.exists("/usr/local/bin/dig"),
        "dig command not available",
    )
    def test_bind_tools_validation(self):
        """Test BIND tools validation."""
        try:
            provider = BINDProvider(self.config)
            # If we get here, tools are available
            self.assertTrue(True)
        except RuntimeError as e:
            if "dig and nsupdate not found" in str(e):
                self.skipTest("BIND tools not available")
            else:
                raise

    def test_bind_config_parsing(self):
        """Test BIND configuration parsing."""
        config = {
            "nameserver": "192.168.1.10",
            "port": 5353,
            "key_file": "/path/to/key",
            "key_name": "my-key",
            "zone_file": "/path/to/zone",
        }

        try:
            provider = BINDProvider(config)
            self.assertEqual(provider.nameserver, "192.168.1.10")
            self.assertEqual(provider.port, 5353)
            self.assertEqual(provider.key_file, "/path/to/key")
            self.assertEqual(provider.key_name, "my-key")
            self.assertEqual(provider.zone_file, "/path/to/zone")
        except RuntimeError as e:
            if "dig and nsupdate not found" in str(e):
                self.skipTest("BIND tools not available")
            else:
                raise


class TestRecordManager(unittest.TestCase):
    """Test the record manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_dns_client = Mock()
        self.record_manager = RecordManager(self.mock_dns_client)

    def test_analyze_changes_create(self):
        """Test analyzing changes for record creation."""
        current_records = []
        desired_records = [
            {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}
        ]

        changes = self.record_manager.analyze_changes(
            current_records, desired_records, "example.com"
        )

        self.assertEqual(len(changes["creates"]), 1)
        self.assertEqual(len(changes["updates"]), 0)
        self.assertEqual(len(changes["deletes"]), 0)
        self.assertEqual(changes["total_changes"], 1)

    def test_analyze_changes_update(self):
        """Test analyzing changes for record update."""
        current_records = [
            {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}
        ]
        desired_records = [
            {"fqdn": "test.example.com", "ipv4": "192.168.1.2", "type": "A"}
        ]

        changes = self.record_manager.analyze_changes(
            current_records, desired_records, "example.com"
        )

        self.assertEqual(len(changes["creates"]), 0)
        self.assertEqual(len(changes["updates"]), 1)
        self.assertEqual(len(changes["deletes"]), 0)
        self.assertEqual(changes["total_changes"], 1)

    def test_analyze_changes_delete(self):
        """Test analyzing changes for record deletion."""
        current_records = [
            {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}
        ]
        desired_records = []

        changes = self.record_manager.analyze_changes(
            current_records, desired_records, "example.com"
        )

        self.assertEqual(len(changes["creates"]), 0)
        self.assertEqual(len(changes["updates"]), 0)
        self.assertEqual(len(changes["deletes"]), 1)
        self.assertEqual(changes["total_changes"], 1)

    def test_analyze_changes_no_change(self):
        """Test analyzing changes when no changes are needed."""
        current_records = [
            {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}
        ]
        desired_records = [
            {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}
        ]

        changes = self.record_manager.analyze_changes(
            current_records, desired_records, "example.com"
        )

        self.assertEqual(len(changes["creates"]), 0)
        self.assertEqual(len(changes["updates"]), 0)
        self.assertEqual(len(changes["deletes"]), 0)
        self.assertEqual(len(changes["no_changes"]), 1)
        self.assertEqual(changes["total_changes"], 0)

    def test_zone_safety_validation(self):
        """Test zone safety validation."""
        current_records = [
            {"fqdn": "test.example.com", "ipv4": "192.168.1.1", "type": "A"}
        ]
        desired_records = [
            {"fqdn": "test.example.com", "ipv4": "192.168.1.2", "type": "A"}
        ]

        # This should not raise an exception
        changes = self.record_manager.analyze_changes(
            current_records, desired_records, "example.com"
        )

        # Test invalid zone
        with self.assertRaises(ValueError):
            self.record_manager.analyze_changes(
                current_records, desired_records, "different.com"
            )


class TestDNSManager(unittest.TestCase):
    """Test the main DNS manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        self.csv_file = os.path.join(self.temp_dir, "test_records.csv")

        # Create test configuration
        config = {
            "dns_providers": {"mock": {}},
            "default_provider": "mock",
            "logging": {"level": "INFO", "file": "test.log"},
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config, f)

        # Create test CSV
        with open(self.csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["FQDN", "IPv4"])
            writer.writerow(["test.example.com", "192.168.1.1"])

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_dns_manager_initialization(self):
        """Test DNS manager initialization."""
        dns_manager = DNSManager(self.config_file)
        self.assertIsNotNone(dns_manager.dns_client)
        self.assertIsNotNone(dns_manager.record_manager)

    def test_csv_parsing(self):
        """Test CSV parsing functionality."""
        dns_manager = DNSManager(self.config_file)

        # Mock the DNS client to return empty records
        dns_manager.dns_client.get_records = Mock(return_value=[])

        # Test dry run
        result = dns_manager.process_csv(self.csv_file, "example.com", dry_run=True)
        self.assertTrue(result)

    def test_invalid_csv_handling(self):
        """Test handling of invalid CSV files."""
        dns_manager = DNSManager(self.config_file)

        # Create invalid CSV
        invalid_csv = os.path.join(self.temp_dir, "invalid.csv")
        with open(invalid_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["FQDN"])  # Missing IPv4 column
            writer.writerow(["test.example.com"])

        # Mock the DNS client
        dns_manager.dns_client.get_records = Mock(return_value=[])

        # This should fail due to invalid CSV structure
        result = dns_manager.process_csv(invalid_csv, "example.com", dry_run=True)
        self.assertFalse(result)  # Should return False on error


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.yaml")
        self.csv_file = os.path.join(self.temp_dir, "test_records.csv")

        # Create test configuration with mock provider
        config = {
            "dns_providers": {"mock": {}},
            "default_provider": "mock",
            "logging": {"level": "INFO", "file": "test.log"},
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config, f)

        # Create test CSV with multiple records
        with open(self.csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["FQDN", "IPv4"])
            writer.writerow(["test1.example.com", "192.168.1.1"])
            writer.writerow(["test2.example.com", "192.168.1.2"])
            writer.writerow(["test3.example.com", "192.168.1.3"])

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_full_workflow(self):
        """Test the complete workflow from CSV to DNS changes."""
        dns_manager = DNSManager(self.config_file)

        # Process CSV in dry-run mode
        result = dns_manager.process_csv(self.csv_file, "example.com", dry_run=True)
        self.assertTrue(result)

        # Verify that the mock provider has the expected records
        mock_provider = dns_manager.dns_client.provider
        self.assertEqual(
            len(mock_provider.records), 0
        )  # Dry run doesn't create records

    def test_record_lifecycle(self):
        """Test the complete lifecycle of DNS records."""
        dns_manager = DNSManager(self.config_file)
        mock_provider = dns_manager.dns_client.provider

        # Start with empty zone
        self.assertEqual(len(mock_provider.records), 0)

        # Add records
        records = [
            {"fqdn": "test1.example.com", "ipv4": "192.168.1.1", "type": "A"},
            {"fqdn": "test2.example.com", "ipv4": "192.168.1.2", "type": "A"},
        ]

        for record in records:
            mock_provider.create_record("example.com", record)

        self.assertEqual(len(mock_provider.records), 2)

        # Update a record
        updated_record = {
            "fqdn": "test1.example.com",
            "ipv4": "192.168.1.10",
            "type": "A",
        }
        mock_provider.update_record("example.com", updated_record)

        # Verify update
        updated = mock_provider.get_records("example.com")
        test1_record = next(r for r in updated if r["fqdn"] == "test1.example.com")
        self.assertEqual(test1_record["ipv4"], "192.168.1.10")

        # Delete a record
        mock_provider.delete_record("example.com", records[1])
        self.assertEqual(len(mock_provider.records), 1)


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
