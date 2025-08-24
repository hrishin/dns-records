"""
Validators - Input validation for DNS records

This module provides validation functions for FQDN and IPv4 addresses
to ensure data integrity and safety.
"""

import ipaddress
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)


def validate_fqdn(fqdn: str) -> bool:
    """
    Validate Fully Qualified Domain Name (FQDN).

    Args:
        fqdn: The FQDN to validate

    Returns:
        True if valid, False otherwise
    """
    if not fqdn or not isinstance(fqdn, str):
        return False

    # Check for trailing dot (invalid in strict FQDN validation)
    if fqdn.endswith("."):
        logger.warning(f"FQDN ends with dot: {fqdn}")
        return False

    # Check length
    if len(fqdn) > 253:
        logger.warning(f"FQDN too long: {fqdn}")
        return False

    # Split into labels
    labels = fqdn.split(".")

    # Check number of labels
    if len(labels) < 2:
        logger.warning(f"FQDN must have at least 2 labels: {fqdn}")
        return False

    # Check for empty labels (consecutive dots)
    if any(label == "" for label in labels):
        logger.warning(f"FQDN contains empty labels: {fqdn}")
        return False

    # Validate each label
    for i, label in enumerate(labels):
        if not _validate_label(label, i == 0):
            logger.warning(f"Invalid label '{label}' in FQDN: {fqdn}")
            return False

    return True


def _validate_label(label: str, is_first: bool) -> bool:
    """
    Validate a single domain label.

    Args:
        label: The label to validate
        is_first: Whether this is the first label

    Returns:
        True if valid, False otherwise
    """
    # Check length
    if len(label) == 0 or len(label) > 63:
        return False

    # Check for valid characters
    # Labels can contain letters, digits, and hyphens
    # Cannot start or end with hyphen
    # Cannot contain consecutive hyphens
    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", label):
        return False

    # Check for consecutive hyphens
    if "--" in label:
        return False

    # First label cannot start with digit (RFC 1123)
    if is_first and label[0].isdigit():
        return False

    return True


def validate_ipv4(ipv4: str) -> bool:
    """
    Validate IPv4 address.

    Args:
        ipv4: The IPv4 address to validate

    Returns:
        True if valid, False otherwise
    """
    if not ipv4 or not isinstance(ipv4, str):
        return False

    try:
        # Use ipaddress module for validation
        ipaddress.IPv4Address(ipv4.strip())
        return True
    except ipaddress.AddressValueError:
        logger.warning(f"Invalid IPv4 address: {ipv4}")
        return False


def validate_zone_name(zone: str) -> bool:
    """
    Validate DNS zone name.

    Args:
        zone: The zone name to validate

    Returns:
        True if valid, False otherwise
    """
    if not zone or not isinstance(zone, str):
        return False

    # Zone names should be valid domain names
    if not validate_fqdn(zone):
        return False

    # Zone names typically don't have IP addresses
    if validate_ipv4(zone):
        return False

    return True


def validate_csv_row(row: dict, row_number: int) -> Tuple[bool, list]:
    """
    Validate a CSV row for DNS record creation.

    Args:
        row: Dictionary containing the CSV row data
        row_number: Row number for error reporting

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    required_fields = ["FQDN", "IPv4"]
    for field in required_fields:
        if field not in row:
            errors.append(f"Row {row_number}: Missing required field '{field}'")
            continue

        if not row[field] or not str(row[field]).strip():
            errors.append(f"Row {row_number}: Empty value for field '{field}'")

    # Validate FQDN if present
    if "FQDN" in row and row["FQDN"]:
        fqdn = str(row["FQDN"]).strip()
        if not validate_fqdn(fqdn):
            errors.append(f"Row {row_number}: Invalid FQDN '{fqdn}'")

    # Validate IPv4 if present
    if "IPv4" in row and row["IPv4"]:
        ipv4 = str(row["IPv4"]).strip()
        if not validate_ipv4(ipv4):
            errors.append(f"Row {row_number}: Invalid IPv4 address '{ipv4}'")

    # Check for private IP ranges (optional validation)
    if "IPv4" in row and row["IPv4"]:
        ipv4 = str(row["IPv4"]).strip()
        if validate_ipv4(ipv4):
            try:
                ip = ipaddress.IPv4Address(ipv4)
                if not _is_private_ip(ip):
                    logger.warning(
                        f"Row {row_number}: IPv4 '{ipv4}' is not in private range"
                    )
            except ipaddress.AddressValueError:
                pass  # Already caught by validate_ipv4

    return len(errors) == 0, errors


def _is_private_ip(ip: ipaddress.IPv4Address) -> bool:
    """
    Check if an IPv4 address is in a private range.

    Args:
        ip: IPv4Address object

    Returns:
        True if private, False otherwise
    """
    private_ranges = [
        ipaddress.IPv4Network("10.0.0.0/8"),
        ipaddress.IPv4Network("172.16.0.0/12"),
        ipaddress.IPv4Network("192.168.0.0/16"),
        ipaddress.IPv4Network("127.0.0.0/8"),
        ipaddress.IPv4Network("169.254.0.0/16"),
    ]

    return any(ip in private_range for private_range in private_ranges)


def sanitize_fqdn(fqdn: str) -> str:
    """
    Sanitize FQDN by removing invalid characters and normalizing.

    Args:
        fqdn: The FQDN to sanitize

    Returns:
        Sanitized FQDN
    """
    if not fqdn:
        return fqdn

    # Remove leading/trailing whitespace and dots
    fqdn = fqdn.strip().strip(".")

    # Convert to lowercase
    fqdn = fqdn.lower()

    # Remove any invalid characters (keep only letters, digits, hyphens, dots)
    fqdn = re.sub(r"[^a-z0-9.-]", "", fqdn)

    # Remove consecutive dots
    fqdn = re.sub(r"\.+", ".", fqdn)

    # Remove leading/trailing dots again
    fqdn = fqdn.strip(".")

    return fqdn


def sanitize_ipv4(ipv4: str) -> str:
    """
    Sanitize IPv4 address by removing whitespace and normalizing.

    Args:
        ipv4: The IPv4 address to sanitize

    Returns:
        Sanitized IPv4 address
    """
    if not ipv4:
        return ipv4

    # Remove whitespace
    ipv4 = ipv4.strip()

    # Validate that it's still a valid IPv4 after sanitization
    if validate_ipv4(ipv4):
        return ipv4
    else:
        # Return original if sanitization made it invalid
        return ipv4


def validate_batch_records(records: list) -> Tuple[bool, list]:
    """
    Validate a batch of DNS records.

    Args:
        records: List of record dictionaries

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check for duplicates
    fqdns = [record.get("fqdn", "") for record in records]
    duplicates = [fqdn for fqdn in set(fqdns) if fqdns.count(fqdn) > 1]

    if duplicates:
        errors.append(f"Duplicate FQDNs found: {', '.join(duplicates)}")

    # Validate each record
    for i, record in enumerate(records):
        is_valid, record_errors = validate_csv_row(record, i + 1)
        if not is_valid:
            errors.extend(record_errors)

    return len(errors) == 0, errors
