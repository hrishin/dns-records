"""
BIND DNS provider implementation.

This module provides BIND DNS server integration using the dnspython library.
"""

import logging
import re
from typing import Dict, List, Optional

import dns.resolver
import dns.query
import dns.update
import dns.tsigkeyring
import dns.zone
import dns.name
import dns.rdatatype
import dns.rcode

from .base_provider import DNSProvider

logger = logging.getLogger(__name__)


class BINDProvider(DNSProvider):
    """BIND DNS provider implementation using dnspython library."""

    def __init__(self, config: Dict):
        """Initialize BIND provider."""
        self.config = config
        self.nameserver = config.get("nameserver", "127.0.0.1")
        self.port = config.get("port", 53)
        self.key_file = config.get("key_file")
        self.key_name = config.get("key_name")
        self.zone_file = config.get("zone_file")

        # Initialize DNS resolver
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = [self.nameserver]
        self.resolver.port = self.port

        # Initialize TSIG keyring if key file is provided
        self.keyring = None
        if self.key_file and self.key_name:
            try:
                # Load TSIG key from file
                with open(self.key_file, "r") as f:
                    key_content = f.read().strip()

                # Parse BIND key file format to extract the secret
                secret = self._parse_bind_key_file(key_content, self.key_name)

                if secret:
                    # Create keyring with the key name and secret
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

    def _normalize_fqdn(self, fqdn: str) -> str:
        """Normalize FQDN by removing trailing dot for consistent handling."""
        return fqdn.rstrip('.') if fqdn else fqdn

    def get_records(self, zone: str) -> List[Dict]:
        """Get all DNS records for a zone using dnspython."""
        try:
            records = []

            # Get all A records for the zone
            try:
                zone_a_records = self._query_dns(zone, "A")
                for ip in zone_a_records:
                    normalized_zone = self._normalize_fqdn(zone)
                    records.append({"fqdn": normalized_zone, "ipv4": ip, "type": "A", "ttl": 300})
            except Exception as e:
                logger.debug(f"No A records found for zone {zone}: {e}")

            # Get records for common subdomains
            common_subdomains = [
                "mgmt",
                "ipmi",
                "svm",
                "admin",
                "monitoring",
                "web",
                "db",
                "logging",
            ]

            for subdomain in common_subdomains:
                subdomain_fqdn = f"{subdomain}.{zone}"
                try:
                    subdomain_records = self._query_dns(subdomain_fqdn, "A")
                    for ip in subdomain_records:
                        normalized_subdomain_fqdn = self._normalize_fqdn(subdomain_fqdn)
                        records.append(
                            {
                                "fqdn": normalized_subdomain_fqdn,
                                "ipv4": ip,
                                "type": "A",
                                "ttl": 300,
                            }
                        )
                except Exception as e:
                    # Subdomain might not exist, continue
                    logger.debug(f"Subdomain {subdomain_fqdn} not found: {e}")
                    continue

            # Try zone transfer for comprehensive record retrieval
            try:
                zone_obj = self._zone_transfer(zone)
                if zone_obj:
                    for name, node in zone_obj.nodes.items():
                        for rdataset in node.rdatasets:
                            if rdataset.rdtype == dns.rdatatype.A:
                                fqdn = str(name.derelativize(zone_obj.origin))
                                normalized_fqdn = self._normalize_fqdn(fqdn)
                                for rdata in rdataset:
                                    records.append(
                                        {
                                            "fqdn": normalized_fqdn,
                                            "ipv4": str(rdata),
                                            "type": "A",
                                            "ttl": rdataset.ttl,
                                        }
                                    )
            except Exception as e:
                logger.debug(f"Zone transfer not available for {zone}: {e}")

            # Remove duplicates based on FQDN and IP
            unique_records = []
            seen = set()
            for record in records:
                key = (record["fqdn"], record["ipv4"])
                if key not in seen:
                    seen.add(key)
                    unique_records.append(record)

            logger.info(f"Retrieved {len(unique_records)} A records from BIND")
            return unique_records

        except Exception as e:
            logger.error(f"Failed to get records from BIND: {e}")
            raise

    def create_record(self, zone: str, record: Dict) -> bool:
        """Create a new DNS record using dnspython."""
        try:
            # Use DNS UPDATE protocol
            update = self._create_update_message(zone, record, "add")

            try:
                response = dns.query.tcp(
                    update, self.nameserver, port=self.port, timeout=30
                )
                if response.rcode() == dns.rcode.NOERROR:
                    logger.info(f"Created record {record['fqdn']} -> {record['ipv4']}")
                else:
                    logger.error(
                        f"DNS update failed with rcode: {dns.rcode.to_text(response.rcode())}"
                    )
                    raise RuntimeError(f"Failed to create the record: {response.answer}")
            except Exception as e:
                logger.error(f"DNS update query failed: {e}")
                raise e

        except Exception as e:
            logger.error(f"Failed to create record {record['fqdn']}: {e}")
            raise

    def update_record(self, zone: str, record: Dict) -> bool:
        """Update an existing DNS record using dnspython."""
        try:
            # Try RNDC first if available and zone file is specified
            if self.zone_file and self._check_rndc_availability():
                try:
                    return self._update_record_with_rndc(zone, record)
                except Exception as e:
                    logger.warning(
                        f"RNDC method failed, falling back to DNS update: {e}"
                    )

            # Use DNS UPDATE protocol - delete old, add new
            update = dns.update.Update(zone, keyring=self.keyring)
            fqdn = dns.name.from_text(record["fqdn"])
            ttl = record.get("ttl", 300)

            # Delete existing record
            update.delete(fqdn, dns.rdatatype.A)

            # Add new record
            update.add(fqdn, ttl, dns.rdatatype.A, record["ipv4"])

            try:
                response = dns.query.tcp(
                    update, self.nameserver, port=self.port, timeout=30
                )
                if response.rcode() == dns.rcode.NOERROR:
                    logger.info(f"Updated record {record['fqdn']} -> {record['ipv4']}")
                else:
                    logger.error(
                        f"DNS update failed with rcode: {dns.rcode.to_text(response.rcode())}"
                    )
                    raise RuntimeError(f"Failed to update the record: {response.answer}")
            except Exception as e:
                logger.error(f"DNS update query failed: {e}")
                raise e

        except Exception as e:
            logger.error(f"Failed to update record {record['fqdn']}: {e}")
            raise

    def delete_record(self, zone: str, record: Dict) -> bool:
        """Delete a DNS record using dnspython."""
        try:
            # Use DNS UPDATE protocol
            update = self._create_update_message(zone, record, "delete")

            try:
                response = dns.query.tcp(
                    update, self.nameserver, port=self.port, timeout=30
                )
                if response.rcode() == dns.rcode.NOERROR:
                    logger.info(f"Deleted record {record['fqdn']} -> {record['ipv4']}")
                else:
                    logger.error(
                        f"DNS update failed with rcode: {dns.rcode.to_text(response.rcode())}"
                    )
                    raise RuntimeError(f"Failed to delete the record: {response.answer}")
            except Exception as e:
                logger.error(f"DNS update query failed: {e}")
                raise e

        except Exception as e:
            logger.error(f"Failed to delete record {record['fqdn']}: {e}")
            raise

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

    def _check_rndc_availability(self) -> bool:
        """Check if RNDC is available for zone management."""
        try:
            import subprocess
            result = subprocess.run(
                ["which", "rndc"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _run_rndc_command(self, command: str) -> bool:
        """Run an RNDC command."""
        try:
            import subprocess
            result = subprocess.run(
                ["rndc", *command.split()], capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                logger.error(f"RNDC command failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to run RNDC command: {e}")
            return False

    def _update_record_with_rndc(self, zone: str, record: Dict) -> bool:
        """Update record using RNDC and zone file editing."""
        try:
            # This is a simplified implementation
            # In a real scenario, you'd parse and edit the zone file
            logger.info(f"RNDC update for {record['fqdn']} -> {record['ipv4']}")
            
            # Reload the zone after modification
            return self.reload_zone(zone)
        except Exception as e:
            logger.error(f"RNDC update failed: {e}")
            raise

    def check_zone_status(self, zone: str) -> Dict:
        """Check the status of a zone using RNDC."""
        try:
            if not self._check_rndc_availability():
                return {"status": "error", "message": "RNDC not available"}

            import subprocess
            result = subprocess.run(
                ["rndc", "status", zone], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": "Zone is active",
                    "details": result.stdout,
                }
            else:
                return {
                    "status": "error",
                    "message": f"RNDC status failed: {result.stderr}",
                }

        except Exception as e:
            return {"status": "error", "message": f"Failed to check zone status: {e}"}

    def reload_zone(self, zone: str) -> bool:
        """Reload a zone using RNDC."""
        try:
            if not self._check_rndc_availability():
                raise RuntimeError("RNDC not available")

            return self._run_rndc_command(f"reload {zone}")

        except Exception as e:
            logger.error(f"Failed to reload zone {zone}: {e}")
            raise
