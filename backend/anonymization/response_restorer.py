"""
Response restorer for replacing anonymized values with original values.

Restores real values in Claude's responses so users see actual data.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional

from backend.anonymization.mapping_service import MappingService
from backend.anonymization.models import ResponseRestorationResult

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

        # Regex patterns for hash detection
        self.hash_patterns = {
            "sha256": re.compile(r"\b([a-f0-9]{64})\b"),  # SHA256 hashes
            "md5": re.compile(r"\b([a-f0-9]{32})\b"),     # MD5 hashes
        }

    def restore(self, response: str) -> ResponseRestorationResult:
        """
        Restore original values in response.

        Args:
            response: Claude's response with anonymized values.

        Returns:
            ResponseRestorationResult with restored text and metadata.
        """
        if not response:
            return ResponseRestorationResult(
                original_response=response,
                restored_response=response,
                restorations_applied={},
                hashes_found=0,
            )

        restored_response = response
        restorations_applied = {}
        hashes_found = 0

        # Track replacements (start, end, hash, original) to avoid overlaps
        replacements_made = []

        # Find all SHA256 hashes
        for match in self.hash_patterns["sha256"].finditer(response):
            hash_value = match.group(0)
            hashes_found += 1

            # Try to find original value (search all entity types)
            original = self.mapping_service.get_original(hash_value)

            if original:
                replacements_made.append(
                    (match.start(), match.end(), hash_value, original)
                )
                restorations_applied[hash_value] = original
                logger.info(f"✅ Restored '{hash_value[:16]}...' → '{original}'")
            else:
                logger.debug(f"ℹ️ Hash '{hash_value[:16]}...' not in mappings")

        # Find all MD5 hashes (serials, asset tags)
        for match in self.hash_patterns["md5"].finditer(response):
            hash_value = match.group(0)
            hashes_found += 1

            original = self.mapping_service.get_original(hash_value)

            if original:
                replacements_made.append(
                    (match.start(), match.end(), hash_value, original)
                )
                restorations_applied[hash_value] = original
                logger.info(f"✅ Restored '{hash_value}' → '{original}'")

        # Apply replacements (longest first to avoid conflicts)
        replacements_made.sort(key=lambda x: x[1] - x[0], reverse=True)

        # Apply replacements from end to start to preserve positions
        for start, end, hash_value, original in sorted(replacements_made, key=lambda x: x[0], reverse=True):
            restored_response = (
                restored_response[:start] + original + restored_response[end:]
            )

        return ResponseRestorationResult(
            original_response=response,
            restored_response=restored_response,
            restorations_applied=restorations_applied,
            hashes_found=hashes_found,
        )

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
            "total_hashes_found": 0,
            "sha256_hashes": 0,
            "md5_hashes": 0,
            "restorable_values": 0,
            "unique_hashes": set(),
        }

        # Count SHA256 hashes
        for match in self.hash_patterns["sha256"].finditer(response):
            hash_value = match.group(0)
            stats["total_hashes_found"] += 1
            stats["sha256_hashes"] += 1
            stats["unique_hashes"].add(hash_value)

            # Check if restorable
            if self.mapping_service.get_original(hash_value):
                stats["restorable_values"] += 1

        # Count MD5 hashes
        for match in self.hash_patterns["md5"].finditer(response):
            hash_value = match.group(0)
            stats["total_hashes_found"] += 1
            stats["md5_hashes"] += 1
            stats["unique_hashes"].add(hash_value)

            # Check if restorable
            if self.mapping_service.get_original(hash_value):
                stats["restorable_values"] += 1

        # Convert set to list for JSON serialization
        stats["unique_hashes"] = list(stats["unique_hashes"])

        return stats