"""
Behave environment configuration for DNS Records Manager integration tests.
"""

import os
import tempfile
import yaml
import subprocess
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def before_all(context):
    """Set up test environment before all tests."""
    context.base_dir = Path(__file__).parent.parent
    context.test_data_dir = context.base_dir / "test_data"
    context.test_data_dir.mkdir(exist_ok=True)
    
    # Test configuration
    context.test_zone = "test.bigbank.com"
    context.test_nameserver = "44.216.94.190"
    context.test_port = 53
    
    context.test_config = {
        "dns_providers": {
            "bind": {
                "nameserver": context.test_nameserver,
                "port": context.test_port,
                "key_file": str(context.base_dir / "bind" / "update-key.conf"),
                "key_name": "update-key"
            }
        },
        "default_provider": "bind",
        "logging": {
            "level": "DEBUG",
            "file": "test_dns_manager.log"
        }
    }
    
    context.test_config_file = context.test_data_dir / "test_config.yaml"
    with open(context.test_config_file, 'w') as f:
        yaml.dump(context.test_config, f)
    
    context.test_records = [
        {"fqdn": "ns1.test.bigbank.com", "ipv4": "192.168.1.110"}
    ]
    
    context.test_csv_file = context.test_data_dir / "test_records.csv"
    with open(context.test_csv_file, 'w') as f:
        f.write("FQDN,IPv4\n")
        for record in context.test_records:
            f.write(f"{record['fqdn']},{record['ipv4']}\n")
    
    context.bind_running = _check_bind_running(context.test_nameserver, context.test_port)
    if not context.bind_running:
        logger.warning("BIND DNS server is not running. Some tests may fail.")
    
    logger.info("Test environment setup complete")


def before_scenario(context, scenario):
    """Set up each test scenario."""
    context.scenario_name = scenario.name
    context.current_records = []
    
    context.scenario_zone = f"{scenario.name.lower().replace(' ', '_')}.{context.test_zone}"
    
    logger.info(f"Starting scenario: {scenario.name}")


def after_scenario(context, scenario):
    """Clean up after each test scenario."""
    try:
        if context.bind_running and hasattr(context, 'dns_manager'):
            _cleanup_test_records(context)
    except Exception as e:
        logger.warning(f"Failed to cleanup test records: {e}")
    
    logger.info(f"Completed scenario: {scenario.name}")


def after_all(context):
    """Clean up test environment after all tests."""
    try:
        if context.test_data_dir.exists():
            import shutil
            shutil.rmtree(context.test_data_dir)
    except Exception as e:
        logger.warning(f"Failed to cleanup test data: {e}")
    
    logger.info("Test environment cleanup complete")


def _check_bind_running(nameserver: str, port: int) -> bool:
    """Check if BIND DNS server is running and accessible."""
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [nameserver]
        resolver.port = port
        resolver.timeout = 2
        resolver.lifetime = 2
        
        resolver.resolve("ns1.test.bigbank.com", "A")
        return True
    except Exception:
        return False


def _cleanup_test_records(context):
    """Clean up test records created during testing."""
    try:
        from dns_records_manager.core.dns_manager import DNSManager
        from dns_records_manager.providers.bind_provider import BINDProvider
        
        cleanup_config = {
            "dns_providers": {
                "bind": {
                    "nameserver": context.test_nameserver,
                    "port": context.test_port,
                    "key_file": str(context.base_dir / "bind" / "update-key.conf"),
                    "key_name": "update-key"
                }
            },
            "default_provider": "bind"
        }
        
        provider = BINDProvider(cleanup_config["dns_providers"]["bind"])
        for record in context.test_records:
            try:
                update = dns.update.Update(context.scenario_zone, keyring=provider.keyring)
                update.delete(record["fqdn"], "A")
                dns.query.tcp(update, context.test_nameserver, port=context.test_port)
            except Exception as e:
                logger.debug(f"Failed to cleanup record {record['fqdn']}: {e}")
                
    except Exception as e:
        logger.warning(f"Failed to cleanup test records: {e}")
