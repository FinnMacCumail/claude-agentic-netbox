"""
Response restorer for replacing anonymized values with original values.

Restores real values in Claude's responses so users see actual data.
"""

import logging
from typing import Dict, List, Tuple

from backend.anonymization.mapping_service import MappingService

logger = logging.getLogger(__name__)


class ResponseRestorer:
    """
    Restores original values in Claude's responses.

    Replaces anonymized values with real values so users see actual data.
    """

    def __init__(self, mapping_service: MappingService):
        """
        Initialize with mapping service.

        Args:
            mapping_service: Service for looking up anonymization mappings.
        """
        self.mapping_service = mapping_service

    def restore(self, response: str) -> str:
        """
        Restore original values in response.

        Args:
            response: Claude's response with anonymized values.

        Returns:
            Response with real values restored.
        """
        if not response:
            return response

        restored = response
        replacements_made = 0

        # PATTERN: Get all reverse mappings
        # Sort by length (longest first) to avoid partial replacements
        # Example: "device-7a3f2b-backup" before "device-7a3f2b"
        reverse_mappings = [
            (anon, orig)
            for anon, orig in self.mapping_service.reverse_mappings.items()
            if ":" not in anon  # Skip table.column prefixed keys
        ]

        # Sort by anonymized value length (longest first)
        sorted_mappings = sorted(
            reverse_mappings, key=lambda x: len(x[0]), reverse=True
        )

        # Track replacements to avoid conflicts
        replacement_positions: List[Tuple[int, int]] = []

        # PATTERN: Replace anonymized → original
        for anonymized, original in sorted_mappings:
            if anonymized in restored:
                # Find all occurrences
                start = 0
                while True:
                    pos = restored.find(anonymized, start)
                    if pos == -1:
                        break

                    # Check if this position overlaps with a previous replacement
                    end_pos = pos + len(anonymized)
                    overlaps = any(
                        (pos < r_end and end_pos > r_start)
                        for r_start, r_end in replacement_positions
                    )

                    if not overlaps:
                        # Perform replacement
                        restored = (
                            restored[:pos] + original + restored[end_pos:]
                        )
                        replacement_positions.append((pos, pos + len(original)))
                        replacements_made += 1
                        logger.debug(f"Restored '{anonymized}' → '{original}'")

                        # Adjust start position for next search
                        start = pos + len(original)
                    else:
                        # Skip this occurrence due to overlap
                        start = end_pos

        if replacements_made > 0:
            logger.info(f"Restored {replacements_made} values in response")

        return restored

    def restore_json(self, json_data: Dict) -> Dict:
        """
        Restore original values in JSON response data.

        Recursively processes dictionaries and lists to restore values.

        Args:
            json_data: JSON response data with anonymized values.

        Returns:
            JSON data with real values restored.
        """
        if isinstance(json_data, dict):
            restored = {}
            for key, value in json_data.items():
                # Restore the key if it's anonymized
                restored_key = self._restore_single_value(key)

                # Recursively restore the value
                if isinstance(value, (dict, list)):
                    restored[restored_key] = self.restore_json(value)
                elif isinstance(value, str):
                    restored[restored_key] = self._restore_single_value(value)
                else:
                    restored[restored_key] = value
            return restored

        elif isinstance(json_data, list):
            return [self.restore_json(item) for item in json_data]

        elif isinstance(json_data, str):
            return self._restore_single_value(json_data)

        else:
            return json_data

    def _restore_single_value(self, value: str) -> str:
        """
        Restore a single anonymized value.

        Args:
            value: Potentially anonymized value.

        Returns:
            Original value if found, or input value if not anonymized.
        """
        if not isinstance(value, str):
            return value

        # Try to get original value
        original = self.mapping_service.get_original(value)
        if original:
            logger.debug(f"Restored single value '{value}' → '{original}'")
            return original

        return value

    def get_restoration_stats(self, response: str) -> Dict:
        """
        Get statistics about potential restorations in a response.

        Args:
            response: Response to analyze.

        Returns:
            Dictionary with restoration statistics.
        """
        stats = {
            "total_anonymized_values": 0,
            "restorable_values": 0,
            "unique_anonymized_values": set(),
        }

        # Check each reverse mapping
        for anonymized in self.mapping_service.reverse_mappings:
            if ":" in anonymized:  # Skip prefixed keys
                continue

            count = response.count(anonymized)
            if count > 0:
                stats["total_anonymized_values"] += count
                stats["restorable_values"] += count
                stats["unique_anonymized_values"].add(anonymized)

        # Convert set to list for JSON serialization
        stats["unique_anonymized_values"] = list(stats["unique_anonymized_values"])

        return stats