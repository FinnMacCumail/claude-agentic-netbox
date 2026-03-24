"""
Mapping service for loading and managing Greenmask anonymization mappings.

This service provides bidirectional lookup between original and anonymized values
using Greenmask's mapping file as the source of truth.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MappingService:
    """
    Loads and manages Greenmask anonymization mappings.

    Provides fast bidirectional lookup between original and anonymized values.
    Uses Greenmask's mapping file as the source of truth.
    """

    def __init__(self, mappings_file: str):
        """
        Initialize mapping service.

        Args:
            mappings_file: Path to Greenmask mapping JSON file.
        """
        self.mappings_file = Path(mappings_file)
        self.forward_mappings: Dict[str, Dict[str, str]] = {}  # original → anon
        self.reverse_mappings: Dict[str, str] = {}  # anon → original
        self.loaded_at: Optional[datetime] = None
        self.tables_count = 0
        self.mappings_count = 0

    def load_mappings(self) -> None:
        """
        Load Greenmask mappings from JSON file.

        Expected format:
        {
          "dcim_device.name": {
            "core-switch-nyc-01": "device-7a3f2b",
            "access-sw-lon-01": "device-x2p9q7"
          },
          "dcim_site.name": {
            "NYC-DC1": "site-9x4k1"
          }
        }

        Raises:
            FileNotFoundError: If mappings file doesn't exist.
            json.JSONDecodeError: If file is not valid JSON.
        """
        logger.info(f"Loading Greenmask mappings from {self.mappings_file}")

        if not self.mappings_file.exists():
            raise FileNotFoundError(
                f"Greenmask mappings file not found: {self.mappings_file}"
            )

        with open(self.mappings_file, "r") as f:
            raw_mappings = json.load(f)

        # Reset mappings before loading new ones
        self.forward_mappings.clear()
        self.reverse_mappings.clear()
        self.mappings_count = 0

        # Build forward and reverse mappings
        for table_column, mapping_dict in raw_mappings.items():
            self.forward_mappings[table_column] = mapping_dict

            # Build reverse index (anon → original)
            for original, anonymized in mapping_dict.items():
                # PATTERN: Include table.column context for disambiguation
                key = f"{table_column}:{anonymized}"
                self.reverse_mappings[key] = original

                # Also store without prefix for faster generic lookup
                # RISK: Collisions if same anon value used in multiple tables
                if anonymized not in self.reverse_mappings:
                    self.reverse_mappings[anonymized] = original

            self.mappings_count += len(mapping_dict)

        self.tables_count = len(raw_mappings)
        self.loaded_at = datetime.utcnow()

        logger.info(
            f"Loaded {self.mappings_count} mappings across {self.tables_count} "
            f"tables from Greenmask"
        )

    def get_anonymized(
        self, original: str, entity_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Get anonymized value for original value.

        Args:
            original: Original value (e.g., "core-switch-nyc-01").
            entity_type: Optional table.column hint (e.g., "dcim_device.name").

        Returns:
            Anonymized value if found, None otherwise.
        """
        # PATTERN: Try with entity_type first for accuracy
        if entity_type and entity_type in self.forward_mappings:
            return self.forward_mappings[entity_type].get(original)

        # PATTERN: Fall back to searching all tables
        for table_column, mappings in self.forward_mappings.items():
            if original in mappings:
                return mappings[original]

        # Not found - may be data added after Greenmask run
        logger.warning(
            f"No anonymized value found for '{original}' "
            f"(type: {entity_type}). May need to re-run Greenmask."
        )
        return None

    def get_original(
        self, anonymized: str, entity_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Get original value for anonymized value (reverse lookup).

        Args:
            anonymized: Anonymized value (e.g., "device-7a3f2b").
            entity_type: Optional table.column hint.

        Returns:
            Original value if found, None otherwise.
        """
        # PATTERN: Try with context first
        if entity_type:
            key = f"{entity_type}:{anonymized}"
            if key in self.reverse_mappings:
                return self.reverse_mappings[key]

        # PATTERN: Fall back to generic lookup
        return self.reverse_mappings.get(anonymized)

    def get_stats(self) -> Dict:
        """Get mapping statistics."""
        return {
            "loaded": self.loaded_at is not None,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "tables_count": self.tables_count,
            "mappings_count": self.mappings_count,
            "file": str(self.mappings_file),
        }

    def is_loaded(self) -> bool:
        """Check if mappings are loaded."""
        return self.loaded_at is not None

    def reload_mappings(self) -> None:
        """Reload mappings from file."""
        logger.info("Reloading mappings...")
        self.load_mappings()