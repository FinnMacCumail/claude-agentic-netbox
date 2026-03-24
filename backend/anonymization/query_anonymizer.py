"""
Query anonymizer for replacing real values with anonymized values.

Uses Greenmask mappings to ensure consistency with anonymized database.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from backend.anonymization.mapping_service import MappingService
from backend.anonymization.models import QueryAnonymizationResult

logger = logging.getLogger(__name__)


class QueryAnonymizer:
    """
    Anonymizes user queries by replacing real values with anonymized values.

    Uses Greenmask mappings to ensure consistency with anonymized database.
    """

    def __init__(self, mapping_service: MappingService):
        """
        Initialize with mapping service.

        Args:
            mapping_service: Service for looking up anonymization mappings.
        """
        self.mapping_service = mapping_service

        # PATTERN: Compile regex patterns for different entity types
        self.patterns = {
            "device": re.compile(
                r"\b([\w]+-switch-[\w]+|[\w]+-router-[\w]+|"
                r"[\w]+-firewall-[\w]+|[\w]+-server-[\w]+|"
                r"[\w]+-lb-[\w]+|[\w]+-ap-[\w]+|[\w]+-core-[\w]+|"
                r"core-[\w]+-[\w]+|edge-[\w]+-[\w]+|dist-[\w]+-[\w]+)\b",
                re.IGNORECASE,
            ),
            "site": re.compile(
                r"\b([A-Z]{2,4}-DC\d+|[\w]+-Office|[\w]+-DataCenter|"
                r"[A-Z]{2,4}-HQ|[A-Z]{2,4}-BR\d+|[\w]+-Campus|"
                r"[\w]+-Colo|[\w]+-AWS|[\w]+-Azure|[\w]+-GCP)\b",
                re.IGNORECASE,
            ),
            "ip": re.compile(
                r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b"
            ),
            "mac": re.compile(
                r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"
            ),
            "vlan": re.compile(
                r"\b(vlan[-\s]?\d{1,4}|VLAN[-\s]?\d{1,4})\b",
                re.IGNORECASE,
            ),
            "location": re.compile(
                r"\b(Rack-[\w]+|Row-[\w]+|Cabinet-[\w]+|"
                r"Building-[\w]+|Floor-\d+|Room-[\w]+)\b",
                re.IGNORECASE,
            ),
        }

    def anonymize(self, query: str) -> QueryAnonymizationResult:
        """
        Anonymize a user query.

        Args:
            query: Original user query with real values.

        Returns:
            QueryAnonymizationResult with anonymized query and metadata.
        """
        anonymized_query = query
        mappings_applied = {}
        entities_found = 0

        # Track replacements to avoid double-replacement
        replacements_made: List[Tuple[int, int, str, str]] = []

        # PATTERN: Process each entity type
        for entity_type, pattern in self.patterns.items():
            matches = list(pattern.finditer(query))

            for match in matches:
                matched_text = match.group(0)
                entities_found += 1

                # PATTERN: Lookup in Greenmask mappings
                # Use table.column hint based on entity type
                table_column = self._get_table_column(entity_type)
                anonymized = self.mapping_service.get_anonymized(
                    matched_text, entity_type=table_column
                )

                if anonymized:
                    # Store replacement info
                    replacements_made.append(
                        (match.start(), match.end(), matched_text, anonymized)
                    )
                    mappings_applied[matched_text] = anonymized
                    logger.debug(f"Anonymized '{matched_text}' → '{anonymized}'")
                else:
                    # PATTERN: Handle missing mapping
                    logger.warning(
                        f"No mapping found for '{matched_text}' (type: {entity_type}). "
                        f"This entity may not exist in anonymized DB."
                    )
                    # Keep original value (will likely not match in anon DB)

        # Apply replacements from longest to shortest to avoid partial replacements
        replacements_made.sort(key=lambda x: x[1] - x[0], reverse=True)

        for start, end, original, anonymized in replacements_made:
            # Replace by rebuilding string to handle overlapping matches correctly
            anonymized_query = (
                anonymized_query[:start]
                + anonymized_query[start:end].replace(original, anonymized)
                + anonymized_query[end:]
            )

        return QueryAnonymizationResult(
            original_query=query,
            anonymized_query=anonymized_query,
            mappings_applied=mappings_applied,
            entities_found=entities_found,
        )

    def _get_table_column(self, entity_type: str) -> Optional[str]:
        """
        Map entity type to Netbox table.column.

        Args:
            entity_type: Type of entity detected in query.

        Returns:
            Table and column name in format "table.column".
        """
        mapping = {
            "device": "dcim_device.name",
            "site": "dcim_site.name",
            "ip": "ipam_ipaddress.address",
            "mac": "dcim_interface.mac_address",
            "vlan": "ipam_vlan.name",
            "location": "dcim_location.name",
        }
        return mapping.get(entity_type)

    def get_entity_patterns(self) -> Dict[str, str]:
        """
        Get the entity patterns used for detection.

        Returns:
            Dictionary of entity type to regex pattern string.
        """
        return {
            entity_type: pattern.pattern
            for entity_type, pattern in self.patterns.items()
        }