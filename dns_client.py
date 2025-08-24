"""
DNS Client - Unified interface for DNS provider APIs

This module provides a common interface for different DNS providers,
currently supporting AWS Route53, Cloudflare, and BIND.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uu import Error

from botocore.exceptions import ClientError, NoCredentialsError
import dns.resolver
import dns.query
import dns.update
import dns.tsigkeyring
import dns.zone
import dns.name
import dns.rdatatype
import dns.rcode

logger = logging.getLogger(__name__)


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

    def _parse_bind_key_file(self, key_content: str, key_name: str) -> Optional[str]:
        """Parse BIND key file format to extract the secret for a specific key."""
        try:
            import re

            # Look for the key block that matches the key_name
            key_pattern = rf'key\s+"{re.escape(key_name)}"\s*{{(.*?)}}'
            match = re.search(key_pattern, key_content, re.DOTALL)

            if match:
                key_block = match.group(1)

                # Extract the secret from the key block
                secret_match = re.search(r'secret\s+"([^"]+)"', key_block)
                if secret_match:
                    secret = secret_match.group(1)
                    logger.debug(f"Extracted secret for key '{key_name}'")
                    return secret
                else:
                    logger.warning(f"No secret found in key block for '{key_name}'")
                    return None
            else:
                logger.warning(f"Key '{key_name}' not found in key file")
                return None

        except Exception as e:
            logger.error(f"Error parsing BIND key file: {e}")
            return None

    def _query_dns(self, query: str, record_type: str = "A") -> List[str]:
        """Query DNS using dnspython resolver."""
        try:
            answers = self.resolver.resolve(query, record_type)
            return [str(answer) for answer in answers]
        except dns.resolver.NXDOMAIN:
            # Domain doesn't exist
            return []
        except dns.resolver.NoAnswer:
            # No records of this type
            return []
        except Exception as e:
            logger.error(f"DNS query failed for {query} {record_type}: {e}")
            raise

    def _zone_transfer(self, zone: str) -> Optional[dns.zone.Zone]:
        """Attempt zone transfer using dnspython."""
        try:
            zone_obj = dns.zone.from_xfr(
                dns.query.xfr(self.nameserver, zone, port=self.port)
            )
            return zone_obj
        except Exception as e:
            logger.debug(f"Zone transfer not available for {zone}: {e}")
            return None

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
                    raise Error(f"Failed to create the record:  {response.answer}")
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
                    return True
                else:
                    logger.error(
                        f"DNS update failed with rcode: {dns.rcode.to_text(response.rcode())}"
                    )
                    return False
            except Exception as e:
                logger.error(f"DNS update query failed: {e}")
                raise

        except Exception as e:
            logger.error(f"Failed to update record {record['fqdn']}: {e}")
            raise

    def delete_record(self, zone: str, record: Dict) -> bool:
        """Delete a DNS record using dnspython."""
        try:
            # Try RNDC first if available and zone file is specified
            if self.zone_file and self._check_rndc_availability():
                try:
                    return self._delete_record_with_rndc(zone, record)
                except Exception as e:
                    logger.warning(
                        f"RNDC method failed, falling back to DNS update: {e}"
                    )

            # Use DNS UPDATE protocol
            update = self._create_update_message(zone, record, "delete")

            try:
                response = dns.query.tcp(
                    update, self.nameserver, port=self.port, timeout=30
                )
                if response.rcode() == dns.rcode.NOERROR:
                    logger.info(f"Deleted record {record['fqdn']}")
                    return True
                else:
                    logger.error(
                        f"DNS update failed with rcode: {dns.rcode.to_text(response.rcode())}"
                    )
                    return False
            except Exception as e:
                logger.error(f"DNS update query failed: {e}")
                raise

        except Exception as e:
            logger.error(f"Failed to delete record {record['fqdn']}: {e}")
            raise

    def _check_rndc_availability(self) -> bool:
        """Check if RNDC is available as an alternative to DNS UPDATE."""
        try:
            import subprocess

            result = subprocess.run(
                ["rndc", "-h"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.CalledProcessError,
        ):
            logger.debug("RNDC not available, will use DNS UPDATE only")
            return False

    def _run_rndc_command(self, command: str) -> bool:
        """Run RNDC command for zone management."""
        try:
            import subprocess

            cmd = ["rndc", "-s", self.nameserver, "-p", "953", command]
            if self.key_file:
                cmd.extend(["-k", self.key_file])

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=30
            )
            logger.debug(f"RNDC output: {result.stdout}")
            return True

        except subprocess.TimeoutExpired:
            logger.error("RNDC command timed out after 30 seconds")
            raise RuntimeError("RNDC command timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"RNDC command failed: {e}")
            if e.stderr:
                logger.error(f"RNDC stderr: {e.stderr}")
            raise

    def _create_record_with_rndc(self, zone: str, record: Dict) -> bool:
        """Create a new DNS record using RNDC and zone file editing."""
        try:
            if not self.zone_file:
                raise ValueError("Zone file path required for RNDC method")

            # Read current zone file
            with open(self.zone_file, "r") as f:
                content = f.read()

            # Add new record
            new_record = f"{record['fqdn']}.\t{record.get('ttl', 300)}\tIN\tA\t{record['ipv4']}\n"
            content += new_record

            # Increment serial number (required for zone reload)
            content = self._increment_serial(content)

            # Write back to zone file
            with open(self.zone_file, "w") as f:
                f.write(content)

            # Reload zone with RNDC
            success = self._run_rndc_command(f"reload {zone}")
            if success:
                logger.info(
                    f"Created record {record['fqdn']} -> {record['ipv4']} using RNDC"
                )

            return success

        except Exception as e:
            logger.error(f"RNDC record creation failed: {e}")
            raise

    def _increment_serial(self, content: str) -> str:
        """Increment the serial number in zone file content."""
        import re

        # Find SOA record and increment serial
        soa_pattern = r"(\s+)(\d{10})(\s+; serial)"
        match = re.search(soa_pattern, content)

        if match:
            current_serial = int(match.group(2))
            new_serial = current_serial + 1
            content = re.sub(soa_pattern, f"\\g<1>{new_serial}\\g<3>", content)
            logger.debug(f"Incremented serial from {current_serial} to {new_serial}")

        return content

    def _update_record_with_rndc(self, zone: str, record: Dict) -> bool:
        """Update an existing DNS record using RNDC and zone file editing."""
        try:
            if not self.zone_file:
                raise ValueError("Zone file path required for RNDC method")

            # Read current zone file
            with open(self.zone_file, "r") as f:
                content = f.read()

            # Remove old record and add new one
            lines = content.split("\n")
            new_lines = []
            record_updated = False

            for line in lines:
                if line.strip().startswith(record["fqdn"]) and "A" in line:
                    # Replace the old record
                    new_record = f"{record['fqdn']}.\t{record.get('ttl', 300)}\tIN\tA\t{record['ipv4']}"
                    new_lines.append(new_record)
                    record_updated = True
                else:
                    new_lines.append(line)

            if not record_updated:
                # Record not found, add it
                new_record = f"{record['fqdn']}.\t{record.get('ttl', 300)}\tIN\tA\t{record['ipv4']}"
                new_lines.append(new_record)

            # Reconstruct content
            content = "\n".join(new_lines)

            # Increment serial number
            content = self._increment_serial(content)

            # Write back to zone file
            with open(self.zone_file, "w") as f:
                f.write(content)

            # Reload zone with RNDC
            success = self._run_rndc_command(f"reload {zone}")
            if success:
                logger.info(
                    f"Updated record {record['fqdn']} -> {record['ipv4']} using RNDC"
                )

            return success

        except Exception as e:
            logger.error(f"RNDC record update failed: {e}")
            raise

    def _delete_record_with_rndc(self, zone: str, record: Dict) -> bool:
        """Delete a DNS record using RNDC and zone file editing."""
        try:
            if not self.zone_file:
                raise ValueError("Zone file path required for RNDC method")

            # Read current zone file
            with open(self.zone_file, "r") as f:
                content = f.read()

            # Remove the record
            lines = content.split("\n")
            new_lines = []
            record_found = False

            for line in lines:
                if line.strip().startswith(record["fqdn"]) and "A" in line:
                    # Skip this line (delete the record)
                    record_found = True
                else:
                    new_lines.append(line)

            if not record_found:
                logger.warning(f"Record {record['fqdn']} not found for deletion")

            # Reconstruct content
            content = "\n".join(new_lines)

            # Increment serial number
            content = self._increment_serial(content)

            # Write back to zone file
            with open(self.zone_file, "w") as f:
                f.write(content)

            # Reload zone with RNDC
            success = self._run_rndc_command(f"reload {zone}")
            if success:
                logger.info(f"Deleted record {record['fqdn']} using RNDC")

            return success

        except Exception as e:
            logger.error(f"RNDC record deletion failed: {e}")
            raise

    def check_zone_status(self, zone: str) -> Dict[str, str]:
        """Check the status of a zone using RNDC."""
        try:
            if not self._check_rndc_availability():
                return {"status": "unknown", "message": "RNDC not available"}

            # Get zone status
            import subprocess

            result = subprocess.run(
                ["rndc", "-s", self.nameserver, "-p", "953", "status"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Parse zone status from output
                if zone in result.stdout:
                    return {"status": "active", "message": f"Zone {zone} is active"}
                else:
                    return {
                        "status": "inactive",
                        "message": f"Zone {zone} not found or inactive",
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


class MockDNSProvider(DNSProvider):
    """Mock DNS provider for testing and demonstration purposes."""

    def __init__(self, config: Dict = None):
        """Initialize mock provider."""
        self.records = []
        logger.info("Mock DNS provider initialized")

    def _normalize_fqdn(self, fqdn: str) -> str:
        """Normalize FQDN by removing trailing dot for consistent handling."""
        return fqdn.rstrip('.') if fqdn else fqdn

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
