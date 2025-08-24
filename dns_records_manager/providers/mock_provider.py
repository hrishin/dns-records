"""
Mock DNS provider for testing and demonstration.

This module provides a mock DNS provider that stores records in memory
for safe testing and demonstration purposes.
"""

import logging
from typing import Dict, List

from .base_provider import DNSProvider

logger = logging.getLogger(__name__)


class MockDNSProvider(DNSProvider):
    """Mock DNS provider for testing and demonstration purposes."""

    def __init__(self, config: Dict = None):
        """Initialize mock provider."""
        self.records = []
        logger.info("Mock DNS provider initialized")

    def _normalize_fqdn(self, fqdn: str) -> str:
        """Normalize FQDN by removing trailing dot for consistent handling."""
        return fqdn.rstrip(".") if fqdn else fqdn

    def get_records(self, zone: str) -> List[Dict]:
        """Get all DNS records for a zone."""
        logger.info(f"Mock: Retrieved {len(self.records)} records")
        return self.records.copy()

    def create_record(self, zone: str, record: Dict) -> bool:
        """Create a new DNS record."""
        self.records.append(record.copy())
        logger.info(f"Mock: Created record {record['fqdn']} -> {record['ipv4']}")
        return True

    def update_record(self, zone: str, record: Dict) -> bool:
        """Update an existing DNS record."""
        normalized_fqdn = self._normalize_fqdn(record["fqdn"])
        for i, existing in enumerate(self.records):
            if self._normalize_fqdn(existing["fqdn"]) == normalized_fqdn:
                self.records[i] = record.copy()
                logger.info(
                    f"Mock: Updated record {record['fqdn']} -> {record['ipv4']}"
                )
                return True

        raise ValueError(f"Record {record['fqdn']} not found for update")

    def delete_record(self, zone: str, record: Dict) -> bool:
        """Delete a DNS record."""
        normalized_fqdn = self._normalize_fqdn(record["fqdn"])
        for i, existing in enumerate(self.records):
            if self._normalize_fqdn(existing["fqdn"]) == normalized_fqdn:
                del self.records[i]
                logger.info(f"Mock: Deleted record {record['fqdn']}")
                return True

        raise ValueError(f"Record {record['fqdn']} not found for deletion")
