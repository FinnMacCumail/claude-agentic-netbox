#!/usr/bin/env python3
"""
Test script to verify the mapping-based anonymization system.

Tests query anonymization and response restoration end-to-end.
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.anonymization.mapping_service import MappingService
from backend.anonymization.query_anonymizer import QueryAnonymizer
from backend.anonymization.response_restorer import ResponseRestorer
from backend.anonymization.models import QueryAnonymizationResult, ResponseRestorationResult

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_mapping_system():
    """Test the complete mapping system."""
    logger.info("="*60)
    logger.info("🧪 Testing Anonymization Mapping System")
    logger.info("="*60)

    # Initialize mapping service
    mappings_file = "backend/anonymization/mappings/mappings_latest.json"
    if not Path(mappings_file).exists():
        logger.error(f"❌ Mapping file not found: {mappings_file}")
        logger.error("   Run: python scripts/generate_mappings.py")
        return False

    logger.info("\n📁 Loading mappings...")
    mapping_service = MappingService(mappings_file)
    mapping_service.load_mappings()

    stats = mapping_service.get_stats()
    logger.info(f"✅ Loaded {stats['mappings_count']} mappings from {stats['tables_count']} tables")
    logger.info(f"   Generated: {mapping_service.metadata.get('generated_at', 'unknown')}")

    # Initialize anonymizer and restorer
    query_anonymizer = QueryAnonymizer(mapping_service)
    response_restorer = ResponseRestorer(mapping_service)

    # Test cases
    test_queries = [
        "Show me all devices at the Albany site",
        "List devices at DM-Albany",
        "What is the status of dmi01-albany-rtr01?",
        "Show routers at Albany and Akron",
        "Find device dmi01-akron-sw01",
    ]

    logger.info("\n" + "="*60)
    logger.info("📝 Testing Query Anonymization")
    logger.info("="*60)

    all_passed = True

    for i, query in enumerate(test_queries, 1):
        logger.info(f"\nTest {i}: \"{query}\"")
        logger.info("-" * 40)

        # Anonymize query
        result = query_anonymizer.anonymize(query)

        if result.mappings_applied:
            logger.info("✅ Anonymization successful!")
            logger.info(f"   Entities found: {result.entities_found}")
            for original, anonymized in result.mappings_applied.items():
                logger.info(f"   • {original} → {anonymized[:16]}...")
            logger.info(f"   Anonymized: {result.anonymized_query}")
        else:
            if "albany" in query.lower() or "akron" in query.lower() or "dmi01" in query.lower():
                logger.error("❌ Failed to anonymize - no mappings applied")
                all_passed = False
            else:
                logger.warning("⚠️ No entities to anonymize in query")

    # Test response restoration
    logger.info("\n" + "="*60)
    logger.info("🔄 Testing Response Restoration")
    logger.info("="*60)

    test_responses = [
        "Found 4 devices at site 5c64bfcc407eab7e470ed8d4319b7f301aae1195d487c0f4fb28b520fea24434",
        "Device 0a25438abc45eb6e97c5d973491fc23446af57cac7524097a702c50818009a94 is active",
        "Devices:\n- 0a25438abc45eb6e97c5d973491fc23446af57cac7524097a702c50818009a94\n- 0906c405235b3f341c736549153407bbd7e8f37a87fe959bd8c70f08682c145d",
    ]

    for i, response in enumerate(test_responses, 1):
        logger.info(f"\nTest {i}:")
        logger.info("-" * 40)
        logger.info(f"Original: {response[:100]}...")

        # Restore response
        result = response_restorer.restore(response)

        if result.restorations_applied:
            logger.info("✅ Restoration successful!")
            logger.info(f"   Hashes found: {result.hashes_found}")
            logger.info(f"   Restored: {len(result.restorations_applied)} values")
            for hash_val, original in list(result.restorations_applied.items())[:3]:
                logger.info(f"   • {hash_val[:16]}... → {original}")
            logger.info(f"   Result: {result.restored_response[:100]}...")
        else:
            logger.warning("⚠️ No hashes found to restore")

    # Test specific mappings
    logger.info("\n" + "="*60)
    logger.info("🔍 Testing Specific Mappings")
    logger.info("="*60)

    # Test site name mapping
    albany_hash = mapping_service.get_anonymized("DM-Albany", "dcim_site.name")
    if albany_hash:
        logger.info(f"✅ DM-Albany → {albany_hash[:16]}...")

        # Test reverse
        original = mapping_service.get_original(albany_hash, "dcim_site.name")
        if original == "DM-Albany":
            logger.info(f"✅ Reverse mapping works: {albany_hash[:16]}... → {original}")
        else:
            logger.error(f"❌ Reverse mapping failed")
            all_passed = False
    else:
        logger.error("❌ Could not find mapping for DM-Albany")
        all_passed = False

    # Test device name mapping
    device_hash = mapping_service.get_anonymized("dmi01-albany-rtr01", "dcim_device.name")
    if device_hash:
        logger.info(f"✅ dmi01-albany-rtr01 → {device_hash[:16]}...")
    else:
        logger.warning("⚠️ Could not find mapping for dmi01-albany-rtr01 (may not exist in DB)")

    # Summary
    logger.info("\n" + "="*60)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED")
    else:
        logger.info("⚠️ SOME TESTS FAILED")
    logger.info("="*60)

    return all_passed


def main():
    """Main entry point."""
    success = test_mapping_system()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()