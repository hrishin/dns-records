"""
Step definitions for BIND provider integration tests.
"""

import time
import dns.resolver
from behave import given, when, then
from dns_records_manager.providers.bind_provider import BINDProvider


@given("I have BIND provider configuration")
def step_impl(context):
    """Set up BIND provider configuration."""
    context.bind_config = context.test_config["dns_providers"]["bind"]


@when("I initialize the BIND provider")
def step_impl(context):
    """Initialize the BIND provider."""
    try:
        context.bind_provider = BINDProvider(context.bind_config)
        context.init_success = True
    except Exception as e:
        context.init_error = str(e)
        context.init_success = False


@then("the provider should be configured correctly")
def step_impl(context):
    """Verify that the provider is configured correctly."""
    assert context.init_success, f"BIND provider initialization failed: {getattr(context, 'init_error', 'Unknown error')}"
    assert context.bind_provider.nameserver == context.bind_config["nameserver"]
    assert context.bind_provider.port == context.bind_config["port"]


@then("the TSIG key should be loaded if available")
def step_impl(context):
    """Verify that the TSIG key is loaded if available."""
    if context.bind_config.get("key_file") and context.bind_config.get("key_name"):
        assert context.bind_provider.keyring is not None, "TSIG key should be loaded"
    else:
        # No key file specified, so keyring can be None
        pass


@given("I have a new DNS record to create")
def step_impl(context):
    """Set up a new DNS record for creation."""
    context.new_record = {
        "fqdn": "newrecord.test.bigbank.com",
        "ipv4": "192.168.1.250"
    }


@when("I create the DNS record using BIND provider")
def step_impl(context):
    """Create a DNS record using the BIND provider."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        # Create the record using BIND provider
        record = {
            "fqdn": context.new_record["fqdn"],
            "ipv4": context.new_record["ipv4"],
            "ttl": 300
        }
        context.bind_provider.create_record(
            context.zone, 
            record
        )
        context.create_success = True
        
        # Wait for DNS propagation
        time.sleep(2)
        
    except Exception as e:
        context.create_error = str(e)
        context.create_success = False


@then("the record should be created in BIND")
def step_impl(context):
    """Verify that the record was created in BIND."""
    assert context.create_success, f"Record creation failed: {getattr(context, 'create_error', 'Unknown error')}"


@then("the record should be resolvable")
def step_impl(context):
    """Verify that the created record is resolvable."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [context.test_nameserver]
        resolver.port = context.test_port
        
        answers = resolver.resolve(context.new_record["fqdn"], "A")
        ip_found = str(answers[0])
        assert ip_found == context.new_record["ipv4"], f"IP mismatch: expected {context.new_record['ipv4']}, got {ip_found}"
    except Exception as e:
        assert False, f"Failed to resolve created record: {e}"


@given("there is an existing DNS record")
def step_impl(context):
    """Set up an existing DNS record for testing."""
    context.existing_record = {
        "fqdn": "existing.test.bigbank.com",
        "ipv4": "192.168.1.100"
    }
    
    # Create the record first
    if context.bind_running:
        try:
            record = {
                "fqdn": context.existing_record["fqdn"],
                "ipv4": context.existing_record["ipv4"],
                "ttl": 300
            }
            context.bind_provider.create_record(
                context.zone,
                record
            )
            time.sleep(1)
        except Exception as e:
            context.scenario.skip(f"Failed to create test record: {e}")


@when("I update the record using BIND provider")
def step_impl(context):
    """Update the existing DNS record using BIND provider."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    context.updated_ip = "192.168.1.200"
    
    try:
        # Update the record
        record = {
            "fqdn": context.existing_record["fqdn"],
            "ipv4": context.updated_ip,
            "ttl": 300
        }
        context.bind_provider.update_record(
            context.zone,
            record
        )
        context.update_success = True
        
        # Wait for DNS propagation
        time.sleep(2)
        
    except Exception as e:
        context.update_error = str(e)
        context.update_success = False


@then("the record should be updated in BIND")
def step_impl(context):
    """Verify that the record was updated in BIND."""
    assert context.update_success, f"Record update failed: {getattr(context, 'update_error', 'Unknown error')}"


@then("the new value should be resolvable")
def step_impl(context):
    """Verify that the updated record resolves to the new value."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [context.test_nameserver]
        resolver.port = context.test_port
        
        answers = resolver.resolve(context.existing_record["fqdn"], "A")
        ip_found = str(answers[0])
        assert ip_found == context.updated_ip, f"IP mismatch: expected {context.updated_ip}, got {ip_found}"
    except Exception as e:
        assert False, f"Failed to resolve updated record: {e}"


@when("I delete the record using BIND provider")
def step_impl(context):
    """Delete the existing DNS record using BIND provider."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        # Delete the record
        context.bind_provider.delete_record(
            context.zone,
            context.existing_record["fqdn"],
            "A"
        )
        context.delete_success = True
        
        # Wait for DNS propagation
        time.sleep(2)
        
    except Exception as e:
        context.delete_error = str(e)
        context.delete_success = False


@then("the record should be removed from BIND")
def step_impl(context):
    """Verify that the record was removed from BIND."""
    assert context.delete_success, f"Record deletion failed: {getattr(context, 'delete_error', 'Unknown error')}"


@then("the record should not be resolvable")
def step_impl(context):
    """Verify that the deleted record is no longer resolvable."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [context.test_nameserver]
        resolver.port = context.test_port
        
        resolver.resolve(context.existing_record["fqdn"], "A")
        assert False, f"Deleted record {context.existing_record['fqdn']} is still resolvable"
    except dns.resolver.NXDOMAIN:
        # Expected - record should not exist
        pass
    except Exception as e:
        # Other errors might indicate the record still exists
        assert False, f"Unexpected error checking deleted record: {e}"


@given("there are DNS records in the zone")
def step_impl(context):
    """Set up DNS records in the zone for zone transfer testing."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    # Create some test records
    context.test_zone_records = [
        {"fqdn": "zone1.test.bigbank.com", "ipv4": "192.168.1.101"},
        {"fqdn": "zone2.test.bigbank.com", "ipv4": "192.168.1.102"},
        {"fqdn": "zone3.test.bigbank.com", "ipv4": "192.168.1.103"},
    ]
    
    for record in context.test_zone_records:
        try:
            record = {
                "fqdn": record["fqdn"],
                "ipv4": record["ipv4"],
                "ttl": 300
            }
            context.bind_provider.create_record(
                context.zone,
                record
            )
        except Exception as e:
            context.scenario.skip(f"Failed to create zone test record: {e}")
    
    time.sleep(1)


@when("I perform a zone transfer")
def step_impl(context):
    """Perform a zone transfer to retrieve all records."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    try:
        context.transferred_records = context.bind_provider.get_records(context.zone)
        context.transfer_success = True
    except Exception as e:
        context.transfer_error = str(e)
        context.transfer_success = False


@then("I should receive all zone records")
def step_impl(context):
    """Verify that all zone records were received."""
    assert context.transfer_success, f"Zone transfer failed: {getattr(context, 'transfer_error', 'Unknown error')}"
    assert len(context.transferred_records) >= len(context.test_zone_records), "Not all records were transferred"


@then("the records should be properly formatted")
def step_impl(context):
    """Verify that the transferred records are properly formatted."""
    for record in context.transferred_records:
        assert "fqdn" in record, "Record missing FQDN field"
        assert "ipv4" in record, "Record missing IPv4 field"
        assert record["fqdn"], "FQDN cannot be empty"
        assert record["ipv4"], "IPv4 cannot be empty"


@then("the operations should succeed")
def step_impl(context):
    """Verify that the authenticated operations succeeded."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    # Verify the record was created
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [context.test_nameserver]
        resolver.port = context.test_port
        
        answers = resolver.resolve(context.test_record["fqdn"], "A")
        ip_found = str(answers[0])
        assert ip_found == context.test_record["ipv4"], f"IP mismatch: expected {context.test_record['ipv4']}, got {ip_found}"
    except Exception as e:
        assert False, f"Failed to verify TSIG operation: {e}"

@given("I specify an invalid zone name")
def step_impl(context):
    """Set up scenario with invalid zone name."""
    context.invalid_zone = "invalid.zone.name"


@when("I attempt DNS operations with invalid zone")
def step_impl(context):
    """Attempt DNS operations with invalid zone."""
    try:
        context.bind_provider.get_records(context.invalid_zone)
        context.invalid_zone_success = True
    except Exception as e:
        context.invalid_zone_error = str(e)
        context.invalid_zone_success = False


@then("the operations should fail gracefully with invalid zone")
def step_impl(context):
    """Verify that operations failed gracefully."""
    # Operations should fail but not crash
    assert not context.invalid_zone_success, "Operations should fail with invalid zone"


@then("appropriate error messages should be shown for invalid zone")
def step_impl(context):
    """Verify that appropriate error messages were shown."""
    # Error should be captured
    assert hasattr(context, 'invalid_zone_error'), "Error should be captured"


@given("I have a zone with many records")
def step_impl(context):
    """Set up a zone with many records for performance testing."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    # Create many test records
    context.many_records = []
    for i in range(50):  # Create 50 records
        record = {
            "fqdn": f"bulk{i:03d}.test.bigbank.com",
            "ipv4": f"192.168.{i//256}.{i%256}"
        }
        context.many_records.append(record)
        
        try:
            record = {
                "fqdn": f"bulk{i:03d}.test.bigbank.com",
                "ipv4": f"192.168.{i//256}.{i%256}"
            }
            context.bind_provider.create_record(
                context.zone,
                record
            )
        except Exception as e:
            context.scenario.skip(f"Failed to create bulk test record: {e}")
    
    time.sleep(2)


@when("I retrieve all records from the zone")
def step_impl(context):
    """Retrieve all records from the zone."""
    if not context.bind_running:
        context.scenario.skip("BIND DNS server is not running")
    
    start_time = time.time()
    try:
        context.bulk_records = context.bind_provider.get_records(context.zone)
        context.bulk_success = True
        context.bulk_time = time.time() - start_time
    except Exception as e:
        context.bulk_error = str(e)
        context.bulk_success = False


@then("all records should be retrieved")
def step_impl(context):
    """Verify that all records were retrieved."""
    assert context.bulk_success, f"Bulk retrieval failed: {getattr(context, 'bulk_error', 'Unknown error')}"
    assert len(context.bulk_records) >= len(context.many_records), "Not all records were retrieved"


@then("the bulk retrieval operation should complete within reasonable time")
def step_impl(context):
    """Verify that the operation completed within reasonable time."""
    bulk_time = getattr(context, 'bulk_time', 0)
    # 50 records should complete within 10 seconds
    assert bulk_time < 10, f"Bulk retrieval took too long: {bulk_time} seconds"
