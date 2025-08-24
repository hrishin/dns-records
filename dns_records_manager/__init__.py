"""
DNS Records Manager - Automated DNS record management

A comprehensive tool for managing DNS records across multiple providers
with support for BIND, AWS Route53, Cloudflare, and more.
"""

__version__ = "1.0.0"
__author__ = "DNS Records Manager Team"
__description__ = "Automated DNS record management for enterprise environments"

from .core.dns_manager import DNSManager
from .core.record_manager import RecordManager
from .providers.dns_client import DNSClient

__all__ = [
    "DNSManager",
    "RecordManager", 
    "DNSClient",
]
