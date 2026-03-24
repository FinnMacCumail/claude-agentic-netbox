#!/usr/bin/env python3
"""
Import Greenmask mappings for use by the anonymization service.

This script reads a Greenmask mapping JSON file and makes it available
to the anonymization service for query/response translation.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def validate_mappings(mappings: Dict[str, Any]) -> bool:
    """
    Validate the structure of Greenmask mappings.

    Args:
        mappings: The mapping dictionary to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not isinstance(mappings, dict):
        print("ERROR: Mappings must be a dictionary")
        return False

    for table_column, values in mappings.items():
        if not isinstance(table_column, str):
            print(f"ERROR: Table/column key must be string, got: {type(table_column)}")
            return False

        if "." not in table_column:
            print(f"WARNING: Expected format 'table.column', got: {table_column}")

        if not isinstance(values, dict):
            print(f"ERROR: Mappings for {table_column} must be a dictionary")
            return False

        for original, anonymized in values.items():
            if not isinstance(original, str) or not isinstance(anonymized, str):
                print(f"ERROR: Mapping values must be strings in {table_column}")
                return False

    return True


def import_mappings(
    mappings_file: Path, output_dir: Path = Path("backend/anonymization/mappings")
) -> bool:
    """
    Import Greenmask mappings.

    Args:
        mappings_file: Path to the Greenmask mapping JSON file.
        output_dir: Directory to copy the mappings to.

    Returns:
        True if successful, False otherwise.
    """
    print(f"Importing mappings from: {mappings_file}")

    # Check if file exists
    if not mappings_file.exists():
        print(f"ERROR: Mapping file not found: {mappings_file}")
        return False

    # Load mappings
    try:
        with open(mappings_file, "r") as f:
            mappings = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in mapping file: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to read mapping file: {e}")
        return False

    # Validate structure
    if not validate_mappings(mappings):
        return False

    # Count entries
    total_tables = len(mappings)
    total_mappings = sum(len(values) for values in mappings.values())

    print(f"Found {total_mappings} mappings across {total_tables} tables")

    # Show sample mappings
    print("\nSample mappings (first 5 from each table):")
    for table_column, values in list(mappings.items())[:3]:
        print(f"\n  {table_column}:")
        for original, anonymized in list(values.items())[:5]:
            print(f"    {original} -> {anonymized}")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy to backend directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"mappings_{timestamp}.json"

    try:
        with open(output_file, "w") as f:
            json.dump(mappings, f, indent=2)
        print(f"\nMappings saved to: {output_file}")
    except Exception as e:
        print(f"ERROR: Failed to save mappings: {e}")
        return False

    # Create symlink to latest
    latest_link = output_dir / "mappings_latest.json"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(output_file.name)
    print(f"Created symlink: {latest_link} -> {output_file.name}")

    # Generate statistics
    stats = {
        "imported_at": datetime.now().isoformat(),
        "source_file": str(mappings_file),
        "tables_count": total_tables,
        "mappings_count": total_mappings,
        "tables": list(mappings.keys()),
    }

    stats_file = output_dir / "mappings_stats.json"
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Statistics saved to: {stats_file}")

    print("\n✅ Import successful!")
    print(f"The mapping service can now load from: {latest_link}")

    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import Greenmask mappings for anonymization service"
    )
    parser.add_argument(
        "mappings_file",
        type=Path,
        help="Path to Greenmask mapping JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/anonymization/mappings"),
        help="Output directory for mappings (default: backend/anonymization/mappings)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate mappings without importing",
    )

    args = parser.parse_args()

    if args.validate_only:
        # Just validate
        try:
            with open(args.mappings_file, "r") as f:
                mappings = json.load(f)
            if validate_mappings(mappings):
                print("✅ Mappings are valid")
                return 0
            else:
                print("❌ Mappings validation failed")
                return 1
        except Exception as e:
            print(f"ERROR: {e}")
            return 1

    # Import mappings
    success = import_mappings(args.mappings_file, args.output_dir)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())