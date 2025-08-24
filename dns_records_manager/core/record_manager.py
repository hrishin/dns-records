"""
Record Manager - Core logic for DNS record management

This module handles the analysis of changes between current and desired DNS records,
ensuring idempotent operations and safe zone management.
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class RecordManager:
    """Manages DNS record operations and change analysis."""

    def __init__(self, dns_client):
        """Initialize record manager with DNS client."""
        self.dns_client = dns_client

    def analyze_changes(
        self, current_records, desired_records: List[Dict], zone: str
    ) -> Dict:
        """
        Analyze changes between current and desired DNS records.

        Args:
            current_records: Current DNS records (can be List[Dict] or Dict[str, str])
            desired_records: List of desired DNS records from CSV
            zone: DNS zone name for safety validation

        Returns:
            Dictionary containing categorized changes
        """
        logger.info("Analyzing DNS record changes...")

        # Convert current_records to standard format if it's a dictionary
        if isinstance(current_records, dict):
            current_records = self._dict_to_records_list(current_records)
        elif not isinstance(current_records, list):
            raise ValueError(
                "current_records must be either a list of dictionaries or a dictionary"
            )

        # Create sets for efficient comparison
        current_set = self._records_to_set(current_records)
        desired_set = self._records_to_set(desired_records)

        # Validate zone safety
        self._validate_zone_safety(current_records, desired_records, zone)

        # Analyze changes
        creates = []
        updates = []
        deletes = []
        no_changes = []

        # Find records to create or update
        for desired in desired_records:
            desired_key = (desired["fqdn"], desired["ipv4"])

            if desired_key not in current_set:
                # Check if this is an update or create
                existing_record = self._find_existing_record(
                    current_records, desired["fqdn"]
                )

                if existing_record:
                    # Record exists but IP is different - update
                    updates.append(desired)
                    logger.info(
                        f"Update needed: {desired['fqdn']} {existing_record['ipv4']} -> {desired['ipv4']}"
                    )
                else:
                    # Record doesn't exist - create
                    creates.append(desired)
                    logger.info(
                        f"Create needed: {desired['fqdn']} -> {desired['ipv4']}"
                    )
            else:
                # Record exists and is identical - no change
                no_changes.append(desired)
                logger.info(f"No change needed: {desired['fqdn']} -> {desired['ipv4']}")

        # Find records to delete (records in current but not in desired)
        for current in current_records:
            current_key = (current["fqdn"], current["ipv4"])

            # Only consider records that are in the target zone
            if self._is_in_zone(current["fqdn"], zone):
                if current_key not in desired_set:
                    # Check if this FQDN is completely removed from desired records
                    if not self._fqdn_in_desired(current["fqdn"], desired_records):
                        deletes.append(current)
                        logger.info(
                            f"Delete needed: {current['fqdn']} -> {current['ipv4']}"
                        )

        # Calculate totals
        total_changes = len(creates) + len(updates) + len(deletes)

        changes = {
            "creates": creates,
            "updates": updates,
            "deletes": deletes,
            "no_changes": no_changes,
            "total_changes": total_changes,
        }

        logger.info(
            f"Change analysis complete: {len(creates)} creates, {len(updates)} updates, "
            f"{len(deletes)} deletes, {len(no_changes)} no changes"
        )

        return changes

    def _dict_to_records_list(self, records_dict: Dict[str, str]) -> List[Dict]:
        """Convert dictionary of {fqdn: ip} to list of {fqdn: str, ipv4: str} records."""
        records_list = []
        for fqdn, ip in records_dict.items():
            records_list.append({"fqdn": fqdn, "ipv4": ip})
        return records_list

    def _normalize_fqdn(self, fqdn: str) -> str:
        """Normalize FQDN by removing trailing dot for consistent comparison."""
        return fqdn.rstrip('.') if fqdn else fqdn

    def _records_to_set(self, records: List[Dict]) -> Set[tuple]:
        """Convert list of records to set of (fqdn, ipv4) tuples for efficient comparison."""
        return {(self._normalize_fqdn(record["fqdn"]), record["ipv4"]) for record in records}

    def _find_existing_record(self, current_records, fqdn: str) -> Dict:
        """Find an existing record by FQDN."""
        # Ensure current_records is in list format
        if isinstance(current_records, dict):
            current_records = self._dict_to_records_list(current_records)

        normalized_fqdn = self._normalize_fqdn(fqdn)
        for record in current_records:
            if self._normalize_fqdn(record["fqdn"]) == normalized_fqdn:
                return record
        return None

    def _fqdn_in_desired(self, fqdn: str, desired_records: List[Dict]) -> bool:
        """Check if an FQDN exists in desired records."""
        normalized_fqdn = self._normalize_fqdn(fqdn)
        return any(self._normalize_fqdn(record["fqdn"]) == normalized_fqdn for record in desired_records)

    def _is_in_zone(self, fqdn: str, zone: str) -> bool:
        """Check if an FQDN is within the specified zone."""
        normalized_fqdn = self._normalize_fqdn(fqdn)
        normalized_zone = self._normalize_fqdn(zone)
        return normalized_fqdn.endswith(normalized_zone) or normalized_fqdn == normalized_zone

    def _validate_zone_safety(
        self, current_records, desired_records: List[Dict], zone: str
    ):
        """Validate that operations are safe for the specified zone."""
        logger.info(f"Validating zone safety for zone: {zone}")

        # Check that all desired records are within the zone
        for record in desired_records:
            if not self._is_in_zone(record["fqdn"], zone):
                raise ValueError(f"FQDN '{record['fqdn']}' is not within zone '{zone}'")

        # Log zone boundaries for safety
        zone_boundaries = self._get_zone_boundaries(zone)
        logger.info(f"Zone boundaries: {zone_boundaries}")

        # Check for any records that might be outside the zone
        for record in current_records:
            if not self._is_in_zone(record["fqdn"], zone):
                logger.warning(
                    f"Found record outside target zone: {record['fqdn']} "
                    f"(zone: {zone}) - will not be modified"
                )

    def _get_zone_boundaries(self, zone: str) -> List[str]:
        """Get zone boundaries for safety validation."""
        boundaries = [zone]

        # Add common subdomain patterns for the zone
        common_subdomains = ["mgmt", "ipmi", "svm", "admin", "monitoring"]
        for subdomain in common_subdomains:
            boundaries.append(f"{subdomain}.{zone}")

        return boundaries

    def get_zone_summary(self, zone: str) -> Dict:
        """Get a summary of the current zone state."""
        try:
            current_records = self.dns_client.get_records(zone)

            # Group records by subdomain
            subdomain_groups = {}
            for record in current_records:
                if self._is_in_zone(record["fqdn"], zone):
                    # Extract subdomain
                    normalized_record_fqdn = self._normalize_fqdn(record["fqdn"])
                    normalized_zone = self._normalize_fqdn(zone)
                    
                    if normalized_record_fqdn == normalized_zone:
                        subdomain = "root"
                    else:
                        subdomain = normalized_record_fqdn.replace(f".{normalized_zone}", "")

                    if subdomain not in subdomain_groups:
                        subdomain_groups[subdomain] = []

                    subdomain_groups[subdomain].append(record)

            summary = {
                "zone": zone,
                "total_records": len(current_records),
                "zone_records": len(
                    [r for r in current_records if self._is_in_zone(r["fqdn"], zone)]
                ),
                "subdomain_groups": subdomain_groups,
                "last_updated": self._get_last_updated(current_records),
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to get zone summary: {e}")
            raise

    def _get_last_updated(self, records) -> str:
        """Get the last updated timestamp from records (if available)."""
        # This is a placeholder - actual implementation would depend on
        # the DNS provider's ability to provide timestamps
        return "Unknown"

    def validate_csv_structure(self, csv_records: List[Dict]) -> List[str]:
        """Validate CSV structure and return any validation errors."""
        errors = []

        for i, record in enumerate(
            csv_records, start=2
        ):  # Start at 2 to account for header
            # Check required fields
            if "fqdn" not in record or "ipv4" not in record:
                errors.append(f"Row {i}: Missing required fields")
                continue

            # Check for empty values
            if not record["fqdn"].strip() or not record["ipv4"].strip():
                errors.append(f"Row {i}: Empty FQDN or IPv4 value")
                continue

            # Check for duplicate FQDNs
            normalized_fqdn = self._normalize_fqdn(record["fqdn"])
            fqdn_count = sum(1 for r in csv_records if self._normalize_fqdn(r["fqdn"]) == normalized_fqdn)
            if fqdn_count > 1:
                errors.append(
                    f"Row {i}: Duplicate FQDN '{record['fqdn']}' found {fqdn_count} times"
                )

        return errors

    def get_change_impact(self, changes: Dict) -> Dict:
        """Analyze the impact of proposed changes."""
        impact = {
            "risk_level": "LOW",
            "affected_services": [],
            "estimated_downtime": "0 seconds",
            "rollback_complexity": "LOW",
        }

        # Assess risk level
        if changes["deletes"]:
            impact["risk_level"] = "MEDIUM"
            impact["affected_services"] = [
                f"DNS resolution for {r['fqdn']}" for r in changes["deletes"]
            ]
            impact["estimated_downtime"] = "5-10 minutes"
            impact["rollback_complexity"] = "MEDIUM"

        if changes["updates"]:
            if impact["risk_level"] == "LOW":
                impact["risk_level"] = "MEDIUM"
            impact["affected_services"].extend(
                [f"DNS resolution for {r['fqdn']}" for r in changes["updates"]]
            )
            impact["estimated_downtime"] = "1-2 minutes"

        if changes["creates"]:
            if impact["risk_level"] == "LOW":
                impact["risk_level"] = "LOW"  # Creates are generally safe
            impact["affected_services"].extend(
                [f"New DNS resolution for {r['fqdn']}" for r in changes["creates"]]
            )

        # Remove duplicates
        impact["affected_services"] = list(set(impact["affected_services"]))

        return impact
