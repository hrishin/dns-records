"""
DNS Client - Unified interface for DNS provider APIs

This module provides a common interface for different DNS providers,
currently supporting AWS Route53, Cloudflare, and BIND.
"""

import logging
from typing import Dict, List

from .base_provider import DNSProvider
from .bind_provider import BINDProvider
from .mock_provider import MockDNSProvider

logger = logging.getLogger(__name__)


class DNSClient:
    """Unified DNS client that supports multiple providers."""

    def __init__(self, config: Dict):
        """Initialize DNS client with configuration."""
        self.config = config
        self.provider = self._get_provider()

    def _get_provider(self) -> DNSProvider:
        """Get DNS provider based on configuration."""
        provider_name = self.config.get("default_provider", "bind")
        provider_config = self.config.get("dns_providers", {}).get(provider_name, {})

        if provider_name == "bind":
            return BINDProvider(provider_config)
        elif provider_name == "mock":
            return MockDNSProvider(provider_config)
        else:
            logger.warning(f"Unknown provider '{provider_name}', using mock provider")
            return MockDNSProvider()

    def get_records(self, zone: str) -> List[Dict]:
        """Get all DNS records for a zone."""
        return self.provider.get_records(zone)

    def create_record(self, zone: str, record: Dict) -> bool:
        """Create a new DNS record."""
        return self.provider.create_record(zone, record)

    def update_record(self, zone: str, record: Dict) -> bool:
        """Update an existing DNS record."""
        return self.provider.update_record(zone, record)

    def delete_record(self, zone: str, record: Dict) -> bool:
        """Delete a DNS record."""
        return self.provider.delete_record(zone, record)
