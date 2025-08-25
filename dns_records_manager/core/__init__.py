"""
Core DNS management functionality.

This package contains the main business logic for DNS record management.
"""

from .dns_manager import DNSManager
from .record_manager import RecordHandler

__all__ = ["DNSManager", "RecordHandler"]
