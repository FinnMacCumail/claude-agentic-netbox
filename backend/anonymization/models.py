"""
Pydantic models for anonymization functionality.
"""

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class MappingEntry(BaseModel):
    """Single anonymization mapping entry."""

    original_value: str
    anonymized_value: str
    value_type: str  # e.g., "dcim_device.name", "dcim_site.name"
    table: str
    column: str


class GreenmaskMapping(BaseModel):
    """Greenmask mapping file structure."""

    mappings: Dict[str, Dict[str, str]]  # table.column -> {original: anonymized}
    run_id: str
    timestamp: datetime
    tables_processed: int


class AnonymizationConfig(BaseModel):
    """Anonymization configuration."""

    enabled: bool = False
    mode: Literal["greenmask"] = "greenmask"
    seed: str
    mappings_file: str
    preserve_vendors: bool = True  # Preserve vendor/model names
    preserve_tags: bool = True  # Preserve generic tags


class QueryAnonymizationResult(BaseModel):
    """Result of query anonymization."""

    original_query: str
    anonymized_query: str
    mappings_applied: Dict[str, str]
    entities_found: int


class ResponseRestorationResult(BaseModel):
    """Result of response restoration."""

    original_response: str
    restored_response: str
    restorations_applied: Dict[str, str]
    hashes_found: int