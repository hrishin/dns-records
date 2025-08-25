"""
BIND DNS provider implementation.

This module provides BIND DNS server integration using the dnspython library.
"""

import logging
import re
from typing import Dict, List, Optional

import dns.name
import dns.query
import dns.rcode
import dns.rdatatype
import dns.resolver
import dns.tsigkeyring
import dns.update
import dns.zone

from .base_provider import DNSProvider
from ..utils.validators import sanitize_fqdn

logger = logging.getLogger(__name__)


class BINDProvider(DNSProvider):
    """BIND DNS provider implementation using dnspython library."""

    def __init__(self, config: Dict):
        """Initialize BIND provider."""
        self.config = config
        self.nameserver = config.get("nameserver", "127.0.0.1")
        self.port = config.get("port", 53)
        self.key_file = config.get("key_file", "")
        self.key_name = config.get("key_name", "")
        self.zone_file = config.get("zone_file", "")

        self.resolver = self._initialize_dns_resolver()

        self.keyring = None
        if self.key_file and self.key_name:
            try:
                with open(self.key_file, "r") as f:
                    key_content = f.read().strip()

                secret = self._parse_bind_key_file(key_content, self.key_name)

                if secret:
                    self.keyring = dns.tsigkeyring.from_text({self.key_name: secret})
                    logger.info(f"TSIG key loaded from {self.key_file}")
                else:
                    logger.warning(
                        f"Could not extract secret for key '{self.key_name}' from {self.key_file}"
                    )
            except Exception as e:
                logger.warning(f"Failed to load TSIG key: {e}")
                logger.debug("TSIG authentication will not be available")

        logger.info(
            f"BIND provider initialized for nameserver {self.nameserver}:{self.port}"
        )

    def _initialize_dns_resolver(self) -> dns.resolver.Resolver:
        """Initialize and configure the DNS resolver with nameserver and port settings."""
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [self.nameserver]
        resolver.port = self.port
        return resolver

    def _parse_bind_key_file(self, key_content: str, key_name: str) -> Optional[str]:
        """Parse BIND key file format to extract the secret for a specific key."""
        try:
            # Look for the key block that matches the key_name
            key_pattern = rf'key\s+"{re.escape(key_name)}"\s*{{(.*?)}}'
            match = re.search(key_pattern, key_content, re.DOTALL)
            if match:
                key_block = match.group(1)
                # Extract the secret from the key block
                secret_match = re.search(r'secret\s+"([^"]+)"', key_block)
                if secret_match:
                    return secret_match.group(1)
            return None
        except Exception as e:
            logger.error(f"Failed to parse BIND key file: {e}")
            return None

    def get_records(self, zone: str) -> List[Dict]:
        """Get all DNS records for a zone using dnspython."""
        try:
            records = []

            try:
                records.extend(self._get_zone_a_records(zone))
            except Exception as e:
                logger.debug(f"No A records found for zone {zone}: {e}")

            records.extend(self._get_zone_transfer_records(zone))
            unique_records = list(
                {
                    (record["fqdn"], record["ipv4"]): record for record in records
                }.values()
            )

            logger.info(f"Retrieved {len(unique_records)} A records from BIND")
            return unique_records

        except Exception as e:
            logger.error(f"Failed to get records from BIND: {e}")
            raise e

    def _get_zone_a_records(self, zone: str) -> List[Dict]:
        """Get A records for a zone and return them as a list of record dictionaries."""
        records = []
        zone_a_records = self._query_dns(zone, "A")
        for ip in zone_a_records:
            normalized_zone = sanitize_fqdn(zone)
            records.append(
                {"fqdn": normalized_zone, "ipv4": ip, "type": "A", "ttl": 300}
            )
        return records

    def _get_zone_transfer_records(self, zone: str) -> List[Dict]:
        """Get A records from zone transfer and return them as a list of record dictionaries."""
        records = []
        zone_obj = self._zone_transfer(zone)
        if zone_obj:
            for name, node in zone_obj.nodes.items():
                for rdataset in node.rdatasets:
                    if rdataset.rdtype == dns.rdatatype.A:
                        fqdn = str(name.derelativize(zone_obj.origin))
                        normalized_fqdn = sanitize_fqdn(fqdn)
                        for rdata in rdataset:
                            records.append(
                                {
                                    "fqdn": normalized_fqdn,
                                    "ipv4": str(rdata),
                                    "type": "A",
                                    "ttl": rdataset.ttl,
                                }
                            )
        return records

    def _query_dns(self, fqdn: str, record_type: str = "A") -> List[str]:
        """Query DNS for specific record type."""
        try:
            answers = self.resolver.resolve(fqdn, record_type)
            return [str(answer) for answer in answers]
        except Exception as e:
            logger.debug(f"DNS query failed for {fqdn} ({record_type}): {e}")
            return []

    def _zone_transfer(self, zone: str):
        """Attempt zone transfer."""
        try:
            zone_obj = dns.zone.from_xfr(
                dns.query.xfr(self.nameserver, zone, port=self.port)
            )
            return zone_obj
        except Exception as e:
            logger.debug(f"Zone transfer not available for {zone}: {e}")
            return None

    def create_record(self, zone: str, record: Dict) -> bool:
        """Create a new DNS record using dnspython."""
        try:
            update = self._create_update_message(zone, record, "add")
            response = dns.query.tcp(
                update, self.nameserver, port=self.port, timeout=30
            )
            if response.rcode() != dns.rcode.NOERROR:
                self._handle_dns_error(response, "create")
            logger.debug(f"Created record {record['fqdn']} -> {record['ipv4']}")
            return True
        except Exception as e:
            logger.error(f"DNS create record query failed: {e}")
            raise e

    def update_record(self, zone: str, record: Dict) -> bool:
        """Update an existing DNS record using dnspython."""
        try:
            update = self._create_update_message(zone, record, "replace")
            response = dns.query.tcp(
                update, self.nameserver, port=self.port, timeout=30
            )
            if response.rcode() != dns.rcode.NOERROR:
                self._handle_dns_error(response, "update")
            logger.debug(f"Updated record {record['fqdn']} -> {record['ipv4']}")
            return True
        except Exception as e:
            logger.error(f"Failed to update record {record['fqdn']}: {e}")
            raise e

    def delete_record(self, zone: str, record: Dict) -> bool:
        """Delete a DNS record using dnspython."""
        try:
            update = self._create_update_message(zone, record, "delete")
            response = dns.query.tcp(
                update, self.nameserver, port=self.port, timeout=30
            )
            if response.rcode() != dns.rcode.NOERROR:
                self._handle_dns_error(response, "delete")

            logger.debug(f"Deleted record {record['fqdn']} -> {record['ipv4']}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete record {record['fqdn']}: {e}")
            raise e

    def _create_update_message(
        self, zone: str, record: Dict, action: str
    ) -> dns.update.Update:
        """Create a DNS update message."""
        update = dns.update.Update(zone, keyring=self.keyring)

        fqdn = dns.name.from_text(record["fqdn"])
        ttl = record.get("ttl", 300)

        if action == "add":
            update.add(fqdn, ttl, dns.rdatatype.A, record["ipv4"])
        elif action == "delete":
            update.delete(fqdn, dns.rdatatype.A)
        elif action == "replace":
            update.replace(fqdn, ttl, dns.rdatatype.A, record["ipv4"])

        return update

    def _handle_dns_error(self, response: dns.message.Message, operation: str) -> None:
        """Handle DNS error responses by logging and raising appropriate exceptions."""
        error_message = (
            f"DNS update failed with response code: {dns.rcode.to_text(response.rcode())}"
        )
        if response.answer:
            error_message += f", server response: {response.answer}"
        logger.error(error_message)
        raise RuntimeError(f"Failed to {operation} the record: {error_message}")
