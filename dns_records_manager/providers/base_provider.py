"""
Base DNS provider interface.

This module defines the abstract base class that all DNS providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class DNSProvider(ABC):
    """Abstract base class for DNS providers."""

    @abstractmethod
    def get_records(self, zone: str) -> List[Dict]:
        """Get all DNS records for a zone."""
        pass

    @abstractmethod
    def create_record(self, zone: str, record: Dict) -> bool:
        """Create a new DNS record."""
        pass

    @abstractmethod
    def update_record(self, zone: str, record: Dict) -> bool:
        """Update an existing DNS record."""
        pass

    @abstractmethod
    def delete_record(self, zone: str, record: Dict) -> bool:
        """Delete a DNS record."""
        pass
