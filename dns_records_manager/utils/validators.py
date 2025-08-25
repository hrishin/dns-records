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

    if fqdn.endswith("."):
        logger.warning(f"FQDN ends with dot: {fqdn}")
        return False

    if len(fqdn) > 253:
        logger.warning(f"FQDN too long: {fqdn}")
        return False

    labels = fqdn.split(".")

    if len(labels) < 2:
        logger.warning(f"FQDN must have at least 2 labels: {fqdn}")
        return False

    if any(label == "" for label in labels):
        logger.warning(f"FQDN contains empty labels: {fqdn}")
        return False

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
    if len(label) == 0 or len(label) > 63:
        return False

    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", label):
        return False

    if "--" in label:
        return False

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

    if not validate_fqdn(zone):
        return False

    if validate_ipv4(zone):
        return False

    return True


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

    fqdn = fqdn.strip().strip(".")

    fqdn = fqdn.lower()

    fqdn = re.sub(r"[^a-z0-9.-]", "", fqdn)

    fqdn = re.sub(r"\.+", ".", fqdn)

    fqdn = fqdn.strip(".")

    return fqdn
