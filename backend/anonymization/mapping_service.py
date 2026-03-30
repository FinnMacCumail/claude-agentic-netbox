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
        self.reverse_mappings: Dict[str, Dict[str, str]] = {}  # anon → original
        self.metadata: Dict = {}
        self.loaded_at: Optional[datetime] = None
        self.tables_count = 0
        self.mappings_count = 0

    def load_mappings(self) -> None:
        """
        Load Greenmask mappings from JSON file.

        Expected format:
        {
          "forward": {
            "dcim_device.name": {
              "core-switch-nyc-01": "device-7a3f2b",
              "access-sw-lon-01": "device-x2p9q7"
            },
            "dcim_site.name": {
              "NYC-DC1": "site-9x4k1"
            }
          },
          "reverse": {
            "dcim_device.name": {
              "device-7a3f2b": "core-switch-nyc-01",
              "device-x2p9q7": "access-sw-lon-01"
            },
            "dcim_site.name": {
              "site-9x4k1": "NYC-DC1"
            }
          },
          "metadata": {
            "generated_at": "2026-03-30T16:30:00Z",
            "total_mappings": 1816
          }
        }

        Raises:
            FileNotFoundError: If mappings file doesn't exist.
            json.JSONDecodeError: If file is not valid JSON.
        """
        logger.info(f"Loading Greenmask mappings from {self.mappings_file}")

        if not self.mappings_file.exists():
            raise FileNotFoundError(
                f"Greenmask mappings file not found: {self.mappings_file}\n"
                f"Run: python scripts/generate_mappings.py"
            )

        with open(self.mappings_file, "r") as f:
            data = json.load(f)

        # Reset mappings before loading new ones
        self.forward_mappings.clear()
        self.reverse_mappings.clear()
        self.mappings_count = 0

        # Load forward and reverse mappings
        if "forward" in data:
            self.forward_mappings = data["forward"]
        if "reverse" in data:
            self.reverse_mappings = data["reverse"]
        if "metadata" in data:
            self.metadata = data["metadata"]

        # Count total mappings
        for table_column in self.forward_mappings:
            self.mappings_count += len(self.forward_mappings[table_column])

        self.tables_count = len(self.forward_mappings)
        self.loaded_at = datetime.utcnow()

        logger.info(
            f"Loaded {self.mappings_count} mappings across {self.tables_count} "
            f"tables from Greenmask (generated: {self.metadata.get('generated_at', 'unknown')})"
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
        # Try with entity_type first for accuracy
        if entity_type and entity_type in self.reverse_mappings:
            return self.reverse_mappings[entity_type].get(anonymized)

        # Fall back to searching all tables
        for table_column, mappings in self.reverse_mappings.items():
            if anonymized in mappings:
                return mappings[anonymized]

        return None

    def get_all_original_values(self, entity_type: str) -> list:
        """
        Get all original values for a specific entity type.

        Args:
            entity_type: Table.column identifier (e.g., "dcim_site.name").

        Returns:
            List of original values.
        """
        if entity_type in self.forward_mappings:
            return list(self.forward_mappings[entity_type].keys())
        return []

    def get_all_anonymized_values(self, entity_type: str) -> list:
        """
        Get all anonymized values for a specific entity type.

        Args:
            entity_type: Table.column identifier (e.g., "dcim_site.name").

        Returns:
            List of anonymized values.
        """
        if entity_type in self.forward_mappings:
            return list(self.forward_mappings[entity_type].values())
        return []

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