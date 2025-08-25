import csv
import logging
from typing import Dict, List

from ..utils.validators import validate_fqdn, validate_ipv4

logger = logging.getLogger(__name__)


class CSVParser:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def parse(self) -> List[Dict[str, str]]:
        """Parse CSV file and validate records."""
        records = []

        try:
            with open(self.csv_path, "r") as f:
                reader = csv.DictReader(f)

                if "FQDN" not in reader.fieldnames or "IPv4" not in reader.fieldnames:
                    raise ValueError("CSV must contain 'FQDN' and 'IPv4' columns")

                for row_num, row in enumerate(reader, start=2):
                    fqdn = row["FQDN"].strip()
                    ipv4 = row["IPv4"].strip()

                    # Validate FQDN and IPv4
                    if not validate_fqdn(fqdn):
                        logger.warning(
                            f"Invalid FQDN '{fqdn}' at row {row_num}, skipping"
                        )
                        continue

                    if not validate_ipv4(ipv4):
                        logger.warning(
                            f"Invalid IPv4 '{ipv4}' at row {row_num}, skipping"
                        )
                        continue

                    records.append({"fqdn": fqdn, "ipv4": ipv4, "type": "A"})

            logger.info(f"Successfully parsed {len(records)} records from CSV")

        except FileNotFoundError:
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        except Exception as e:
            raise Exception(f"Error parsing CSV: {e}")

        return records
