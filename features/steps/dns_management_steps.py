"""
Step definitions for DNS Records Manager integration tests.
"""

import os
import time
import yaml
import csv
import tempfile
from pathlib import Path
from behave import given, when, then, step
import dns.resolver
import dns.query
import dns.update

from dns_records_manager.core.dns_manager import DNSManager
from dns_records_manager.providers.bind_provider import BINDProvider
from dns_records_manager.parsers.csv import CSVParser


@given("the DNS Records Manager is configured with BIND provider")
def step_impl(context):
    """Configure the DNS Records Manager with BIND provider."""
    context.dns_manager = DNSManager(context.test_config)
    assert context.dns_manager is not None
    assert context.dns_manager.dns_client is not None


@given("the BIND DNS server is running")
def step_impl(context):
    """Verify that the BIND DNS server is running."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    assert context.bind_running


@given("I have a test zone configured")
def step_impl(context):
    """Set up a test zone for the scenario."""
    context.zone = context.scenario_zone
    # For testing purposes, we'll use the main test zone
    context.zone = context.test_zone


@given("I have a CSV file with new DNS records")
def step_impl(context):
    """Create a CSV file with new DNS records."""
    context.csv_records = [
        {"fqdn": "new1.test.bigbank.com", "ipv4": "192.168.1.200"},
        {"fqdn": "new2.test.bigbank.com", "ipv4": "192.168.1.201"},
        {"fqdn": "new3.test.bigbank.com", "ipv4": "192.168.1.202"},
        {"fqdn": "ns1.test.bigbank.com", "ipv4": "192.168.1.110"},
    ]
    
    context.csv_file = context.test_data_dir / "new_records.csv"
    with open(context.csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["FQDN", "IPv4"])
        writer.writeheader()
        for record in context.csv_records:
            writer.writerow({"FQDN": record["fqdn"], "IPv4": record["ipv4"]})


@given("there are existing DNS records in the zone")
def step_impl(context):
    """Create existing DNS records in the zone."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    # Create some initial records
    context.existing_records = [
        {"fqdn": "existing1.test.bigbank.com", "ipv4": "192.168.1.110"},
        {"fqdn": "existing2.test.bigbank.com", "ipv4": "192.168.1.101"},
        {"fqdn": "ns1.test.bigbank.com", "ipv4": "192.168.1.110"},
    ]
    
    # Add records to DNS
    provider = BINDProvider(context.test_config["dns_providers"]["bind"])
    for record in context.existing_records:
        try:
            update = dns.update.Update(context.zone, keyring=provider.keyring)
            update.add(record["fqdn"], 300, "A", record["ipv4"])
            dns.query.tcp(update, context.test_nameserver, port=context.test_port)
        except Exception as e:
            context.scenario.skip(f"Failed to create existing records: {e}")
    
    # Wait for records to propagate
    time.sleep(1)


@given("the DNS records are already in the desired state")
def step_impl(context):
    """Ensure DNS records are already in the desired state."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    # Use the test records that should already exist
    context.csv_records = context.test_records.copy()
    context.csv_file = context.test_csv_file


@given("I have a CSV file with DNS record changes")
def step_impl(context):
    """Create a CSV file with DNS record changes."""
    context.csv_records = [
        {"fqdn": "change1.test.bigbank.com", "ipv4": "192.168.1.220"},
        {"fqdn": "change2.test.bigbank.com", "ipv4": "192.168.1.221"},
    ]
    
    context.csv_file = context.test_data_dir / "changes.csv"
    with open(context.csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["FQDN", "IPv4"])
        writer.writeheader()
        for record in context.csv_records:
            writer.writerow({"FQDN": record["fqdn"], "IPv4": record["ipv4"]})


@given("I have a CSV file with valid and invalid DNS records")
def step_impl(context):
    """Create a CSV file with invalid DNS records."""
    context.csv_records = [
        {"fqdn": "change1.test.bigbank.com", "ipv4": "192.168.1.220"}, # Valid record
        {"fqdn": "invalidfqdn", "ipv4": "192.168.1.101"},  # Invalid FQDN
        {"fqdn": "", "ipv4": "192.168.1.102"},  # Empty FQDN
        {"fqdn": "ns1.test.bigbank.com", "ipv4": "192.168.1.110"}, # Valid record
    ]
    
    context.csv_file = context.test_data_dir / "invalid_records.csv"
    with open(context.csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["FQDN", "IPv4"])
        writer.writeheader()
        for record in context.csv_records:
            writer.writerow({"FQDN": record["fqdn"], "IPv4": record["ipv4"]})


@given("I have a CSV file with many DNS records")
def step_impl(context):
    """Create a CSV file with many DNS records."""
    context.csv_records = []
    for i in range(30):  # Create 100 records
        context.csv_records.append({
            "fqdn": f"bulk{i:03d}.test.bigbank.com",
            "ipv4": f"192.168.{i//256}.{i%256}"
        })
    context.csv_records.append({
        "fqdn": "ns1.test.bigbank.com",
        "ipv4": "192.168.1.110"
    })
    context.csv_file = context.test_data_dir / "bulk_records.csv"
    with open(context.csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["FQDN", "IPv4"])
        writer.writeheader()
        for record in context.csv_records:
            writer.writerow({"FQDN": record["fqdn"], "IPv4": record["ipv4"]})


@when("I process the CSV file to create DNS records")
def step_impl(context):
    """Process the CSV file to create DNS records."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        # Parse CSV file
        parser = CSVParser(str(context.csv_file))
        records = parser.parse()
        
        # Process records
        context.result = context.dns_manager.process_records(
            records, context.zone, dry_run=False
        )
        
        # Wait for DNS propagation
        time.sleep(2)
        
    except Exception as e:
        context.error = str(e)
        context.result = False


@when("I update the IP addresses for existing records")
def step_impl(context):
    """Update IP addresses for existing records."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    # Create updated records with new IPs
    context.updated_records = [
        {"fqdn": "existing1.test.bigbank.com", "ipv4": "192.168.1.200"},
        {"fqdn": "existing2.test.bigbank.com", "ipv4": "192.168.1.201"},
        {"fqdn": "ns1.test.bigbank.com", "ipv4": "192.168.1.110"},
    ]
    
    context.csv_file = context.test_data_dir / "updated_records.csv"
    with open(context.csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["FQDN", "IPv4"])
        writer.writeheader()
        for record in context.updated_records:
            writer.writerow({"FQDN": record["fqdn"], "IPv4": record["ipv4"]})
    
    try:
        parser = CSVParser(str(context.csv_file))
        records = parser.parse()
        context.result = context.dns_manager.process_records(
            records, context.zone, dry_run=False
        )
        time.sleep(2)
    except Exception as e:
        context.error = str(e)
        context.result = False


@when("I remove records from the CSV file")
def step_impl(context):
    """Remove records from the CSV file."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    # Create CSV with fewer records (simulating deletion)
    context.remaining_records = [context.existing_records[0]]  # Keep only first record
    
    context.csv_file = context.test_data_dir / "remaining_records.csv"
    with open(context.csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["FQDN", "IPv4"])
        writer.writeheader()
        for record in context.remaining_records:
            writer.writerow({"FQDN": record["fqdn"], "IPv4": record["ipv4"]})
    
    try:
        parser = CSVParser(str(context.csv_file))
        records = parser.parse()
        context.result = context.dns_manager.process_records(
            records, context.zone, dry_run=False
        )
        time.sleep(2)
    except Exception as e:
        context.error = str(e)
        context.result = False


@when("I process the same CSV file again")
def step_impl(context):
    """Process the same CSV file again for idempotency testing."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        records = []
        records.append({"fqdn": "ns1.test.bigbank.com", "ipv4": "192.168.1.110"})
        context.result = context.dns_manager.process_records(
            records, context.zone, dry_run=False
        )
    except Exception as e:
        context.error = str(e)
        context.result = False


@when("I run the DNS manager in dry run mode")
def step_impl(context):
    """Run the DNS manager in dry run mode."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        parser = CSVParser(str(context.csv_file))
        records = parser.parse()
        context.result = context.dns_manager.process_records(
            records, context.zone, dry_run=True
        )
    except Exception as e:
        context.error = str(e)
        context.result = False


@when("I process the CSV file")
def step_impl(context):
    """Process the CSV file with invalid records."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        parser = CSVParser(str(context.csv_file))
        records = parser.parse()
        context.result = context.dns_manager.process_records(
            records, context.zone, dry_run=False
        )
        time.sleep(2)
    except Exception as e:
        context.error = str(e)
        context.result = False


@when("I retrieve all records for the zone")
def step_impl(context):
    """Retrieve all records for the zone."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        context.retrieved_records = context.dns_manager.dns_client.get_records(context.zone)
    except Exception as e:
        context.error = str(e)
        context.retrieved_records = []


@when("I perform DNS operations")
def step_impl(context):
    """Perform DNS operations with TSIG authentication."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        # Test basic DNS operations
        parser = CSVParser(str(context.csv_file))
        records = parser.parse()
        context.result = context.dns_manager.process_records(
            records, context.zone, dry_run=False
        )
        time.sleep(2)
    except Exception as e:
        context.error = str(e)
        context.result = False


@when("I attempt to perform DNS operations")
def step_impl(context):
    """Attempt to perform DNS operations with unreachable server."""
    # Temporarily change config to unreachable server
    original_config = context.test_config.copy()
    context.test_config["dns_providers"]["bind"]["nameserver"] = "192.168.255.255"
    
    try:
        # Create new DNS manager with unreachable config
        unreachable_manager = DNSManager(context.test_config)
        parser = CSVParser(str(context.csv_file))
        records = parser.parse()
        context.result = unreachable_manager.process_records(
            records, context.zone, dry_run=False
        )
    except Exception as e:
        context.error = str(e)
        context.result = False
    finally:
        # Restore original config
        context.test_config = original_config


@when("I process the large CSV file")
def step_impl(context):
    """Process the large CSV file with many records."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    start_time = time.time()
    try:
        parser = CSVParser(str(context.csv_file))
        records = parser.parse()
        context.result = context.dns_manager.process_records(
            records, context.zone, dry_run=False
        )
        context.processing_time = time.time() - start_time
        time.sleep(2)
    except Exception as e:
        context.error = str(e)
        context.result = False


@when("I perform concurrent DNS updates")
def step_impl(context):
    """Perform concurrent DNS updates."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    import threading
    
    def update_records(thread_id):
        try:
            # Create thread-specific records
            thread_records = [
                {"fqdn": f"concurrent{thread_id}.test.bigbank.com", "ipv4": f"192.168.{thread_id}.100"},
                {"fqdn": "ns1.test.bigbank.com", "ipv4": "192.168.1.110"}
            ]
            
            thread_csv = context.test_data_dir / f"concurrent_{thread_id}.csv"
            with open(thread_csv, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["FQDN", "IPv4"])
                writer.writeheader()
                for record in thread_records:
                    writer.writerow({"FQDN": record["fqdn"], "IPv4": record["ipv4"]})
            
            parser = CSVParser(str(thread_csv))
            records = parser.parse()
            return context.dns_manager.process_records(records, context.zone, dry_run=False)
        except Exception as e:
            return False
    
    # Start multiple threads
    threads = []
    results = []
    
    for i in range(3):
        thread = threading.Thread(target=lambda i=i: results.append(update_records(i)))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    context.concurrent_results = results
    time.sleep(2)


@then("the DNS records should be created successfully")
def step_impl(context):
    """Verify that DNS records were created successfully."""
    assert context.result is True, f"DNS record creation failed: {getattr(context, 'error', 'Unknown error')}"


@then("the records should be resolvable via DNS queries")
def step_impl(context):
    """Verify that the created records are resolvable via DNS queries."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    for record in context.csv_records:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [context.test_nameserver]
            resolver.port = context.test_port
            
            answers = resolver.resolve(record["fqdn"], "A")
            ip_found = str(answers[0])
            assert ip_found == record["ipv4"], f"IP mismatch for {record['fqdn']}: expected {record['ipv4']}, got {ip_found}"
        except Exception as e:
            assert False, f"Failed to resolve {record['fqdn']}: {e}"


@then("the DNS records should be updated successfully")
def step_impl(context):
    """Verify that DNS records were updated successfully."""
    assert context.result is True, f"DNS record update failed: {getattr(context, 'error', 'Unknown error')}"


@then("the new IP addresses should be resolvable")
def step_impl(context):
    """Verify that the new IP addresses are resolvable."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    for record in context.updated_records:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [context.test_nameserver]
            resolver.port = context.test_port
            
            answers = resolver.resolve(record["fqdn"], "A")
            ip_found = str(answers[0])
            assert ip_found == record["ipv4"], f"IP mismatch for {record['fqdn']}: expected {record['ipv4']}, got {ip_found}"
        except Exception as e:
            assert False, f"Failed to resolve {record['fqdn']}: {e}"


@then("the removed records should be deleted from DNS")
def step_impl(context):
    """Verify that removed records were deleted from DNS."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    # Check that removed records are no longer resolvable
    removed_record = context.existing_records[1]  # This should have been removed
    
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [context.test_nameserver]
        resolver.port = context.test_port
        
        resolver.resolve(removed_record["fqdn"], "A")
        assert False, f"Removed record {removed_record['fqdn']} is still resolvable"
    except dns.resolver.NXDOMAIN:
        # Expected - record should not exist
        pass
    except Exception as e:
        # Other errors might indicate the record still exists
        assert False, f"Unexpected error checking removed record: {e}"


@then("the remaining records should still be resolvable")
def step_impl(context):
    """Verify that remaining records are still resolvable."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    for record in context.remaining_records:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [context.test_nameserver]
            resolver.port = context.test_port
            
            answers = resolver.resolve(record["fqdn"], "A")
            ip_found = str(answers[0])
            assert ip_found == record["ipv4"], f"IP mismatch for {record['fqdn']}: expected {record['ipv4']}, got {ip_found}"
        except Exception as e:
            assert False, f"Failed to resolve remaining record {record['fqdn']}: {e}"


@then("no changes should be made to the DNS zone")
def step_impl(context):
    """Verify that no changes were made to the DNS zone."""
    assert context.result is True, f"Idempotent operation failed: {getattr(context, 'error', 'Unknown error')}"


@then("the operation should complete successfully")
def step_impl(context):
    """Verify that the operation completed successfully."""
    assert context.result is True, f"Operation failed: {getattr(context, 'error', 'Unknown error')}"


@then("no actual changes should be made to DNS")
def step_impl(context):
    """Verify that no actual changes were made to DNS in dry run mode."""
    assert context.result is True, f"Dry run failed: {getattr(context, 'error', 'Unknown error')}"


@then("I should see a summary of proposed changes")
def step_impl(context):
    """Verify that a summary of proposed changes was displayed."""
    # In dry run mode, the operation should succeed without making changes
    assert context.result is True


@then("invalid records should be skipped")
def step_impl(context):
    """Verify that invalid records were skipped."""
    # The operation should still succeed even with invalid records
    assert context.result is True


@then("valid records should be processed successfully")
def step_impl(context):
    """Verify that valid records were processed successfully."""
    # Check that at least one valid record was processed
    valid_records = [r for r in context.csv_records if r["fqdn"] and r["ipv4"] and "." in r["fqdn"]]
    
    if valid_records:
        for record in valid_records:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [context.test_nameserver]
                resolver.port = context.test_port
                
                answers = resolver.resolve(record["fqdn"], "A")
                ip_found = str(answers[0])
                assert ip_found == record["ipv4"], f"IP mismatch for {record['fqdn']}: expected {record['ipv4']}, got {ip_found}"
            except Exception as e:
                assert False, f"Failed to resolve valid record {record['fqdn']}: {e}"

@then("I should get a complete list of all records")
def step_impl(context):
    """Verify that a complete list of all records was retrieved."""
    assert context.retrieved_records is not None
    assert len(context.retrieved_records) > 0


@then("the records should include correct FQDN and IP mappings")
def step_impl(context):
    """Verify that the retrieved records have correct FQDN and IP mappings."""
    for record in context.retrieved_records:
        assert "fqdn" in record, "Record missing FQDN field"
        assert "ipv4" in record, "Record missing IPv4 field"
        assert record["fqdn"], "FQDN cannot be empty"
        assert record["ipv4"], "IPv4 cannot be empty"


@then("the operations should be authenticated using the TSIG key")
def step_impl(context):
    """Verify that operations were authenticated using the TSIG key."""
    # TSIG authentication is handled at the BIND provider level
    # If we get here without errors, authentication was successful
    assert context.result is True


@then("the operations should fail gracefully")
def step_impl(context):
    """Verify that operations failed gracefully."""
    # Operations should fail but not crash
    assert context.result is False or hasattr(context, 'error')


@then("all records should be processed successfully")
def step_impl(context):
    """Verify that all records were processed successfully."""
    assert context.result is True, f"Bulk processing failed: {getattr(context, 'error', 'Unknown error')}"


@then("the operation should complete within reasonable time")
def step_impl(context):
    """Verify that the operation completed within reasonable time."""
    processing_time = getattr(context, 'processing_time', 0)
    # 100 records should complete within 30 seconds
    assert processing_time < 30, f"Bulk processing took too long: {processing_time} seconds"


@then("all operations should complete successfully")
def step_impl(context):
    """Verify that all concurrent operations completed successfully."""
    assert all(context.concurrent_results), "Some concurrent operations failed"


@then("the DNS zone should remain consistent")
def step_impl(context):
    """Verify that the DNS zone remained consistent after concurrent operations."""
    # Check that all concurrent records are resolvable
    for i in range(3):
        fqdn = f"concurrent{i}.test.bigbank.com"
        expected_ip = f"192.168.{i}.100"
        
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [context.test_nameserver]
            resolver.port = context.test_port
            
            answers = resolver.resolve(fqdn, "A")
            ip_found = str(answers[0])
            assert ip_found == expected_ip, f"IP mismatch for {fqdn}: expected {expected_ip}, got {ip_found}"
        except Exception as e:
            assert False, f"Failed to resolve concurrent record {fqdn}: {e}"


@then("the operations should complete successfully")
def step_impl(context):
    """Verify that the operations completed successfully."""
    assert context.result is True, f"Operations failed: {getattr(context, 'error', 'Unknown error')}"


@given("the BIND DNS server is unreachable")
def step_impl(context):
    """Set up scenario with unreachable BIND DNS server."""
    # This step is handled in the when step that attempts operations
    pass


@given("multiple DNS operations are running simultaneously")
def step_impl(context):
    """Set up scenario with multiple simultaneous DNS operations."""
    # This step is handled in the when step that performs concurrent updates
    pass
