#!/usr/bin/env python3
"""
Generate bidirectional mappings between production and anonymized Netbox databases.

This script queries both databases, matches records by ID, and creates
forward (real → anonymized) and reverse (anonymized → real) mappings.
"""

import json
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MappingGenerator:
    """Generate mappings between production and anonymized Netbox databases."""

    def __init__(self):
        """Initialize mapping generator with database connections."""
        self.prod_conn = None
        self.anon_conn = None
        self.mappings = {
            "forward": {},
            "reverse": {},
            "metadata": {}
        }
        self.total_mappings = 0

    def connect_databases(self):
        """Connect to both production and anonymized databases."""
        # Production database connection
        # Since the production database is in Docker without exposed port,
        # we need to use docker exec to run psql commands
        # For now, we'll use a different approach
        try:
            logger.info("🔍 Connecting to production database...")
            # Get Docker container IP
            import subprocess
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                 "netbox-docker-postgres-1"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                docker_ip = result.stdout.strip()
                logger.info(f"📍 Found Docker container IP: {docker_ip}")
                self.prod_conn = psycopg2.connect(
                    host=docker_ip,
                    port=5432,
                    database="netbox",
                    user="netbox",
                    password="J5brHrAXFLQSif0K",
                    cursor_factory=RealDictCursor
                )
                logger.info("✅ Connected to production database via Docker IP")
            else:
                raise Exception("Could not get Docker container IP")

        except Exception as e:
            logger.error(f"❌ Failed to connect to production database: {e}")
            logger.error("💡 Tip: Make sure netbox-docker-postgres-1 container is running")
            raise

        # Anonymized database connection
        try:
            logger.info("🔍 Connecting to anonymized database...")
            self.anon_conn = psycopg2.connect(
                host="localhost",
                port=5433,  # Mapped to 5433 on host
                database="netbox_anonymized",
                user="netbox",
                password="netbox",
                cursor_factory=RealDictCursor
            )
            logger.info("✅ Connected to anonymized database")
        except Exception as e:
            logger.error(f"❌ Failed to connect to anonymized database: {e}")
            raise

    def query_production(self, query: str) -> List[Dict]:
        """Execute query on production database."""
        with self.prod_conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def query_anonymized(self, query: str) -> List[Dict]:
        """Execute query on anonymized database."""
        with self.anon_conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def process_table_column(self, table: str, column: str) -> int:
        """
        Process a single table/column combination to generate mappings.

        Args:
            table: Table name
            column: Column name

        Returns:
            Number of mappings created
        """
        key = f"{table}.{column}"
        self.mappings["forward"][key] = {}
        self.mappings["reverse"][key] = {}

        # Query both databases
        query = f"""
            SELECT id, {column}
            FROM {table}
            WHERE {column} IS NOT NULL
            AND {column} != ''
            ORDER BY id
        """

        try:
            prod_rows = self.query_production(query)
            anon_rows = self.query_anonymized(query)
        except Exception as e:
            logger.warning(f"⚠️ Failed to query {table}.{column}: {e}")
            return 0

        # Convert to dictionaries indexed by ID
        prod_dict = {row['id']: row[column] for row in prod_rows}
        anon_dict = {row['id']: row[column] for row in anon_rows}

        # Match by ID and create mappings
        mappings_created = 0
        for row_id in prod_dict:
            if row_id not in anon_dict:
                logger.warning(f"⚠️ ID {row_id} exists in production but not in anonymized for {table}")
                continue

            original = prod_dict[row_id]
            anonymized = anon_dict[row_id]

            # Skip if values are identical (not anonymized)
            if original == anonymized:
                continue

            # Skip null or empty values
            if not original or not anonymized:
                continue

            # Forward mapping: real → anonymized
            self.mappings["forward"][key][original] = anonymized

            # Reverse mapping: anonymized → real
            self.mappings["reverse"][key][anonymized] = original

            mappings_created += 1

        logger.info(f"📊 Processing {table}.{column}... ({mappings_created} mappings)")
        return mappings_created

    def generate_mappings(self) -> Dict:
        """
        Generate all mappings between production and anonymized databases.

        Returns:
            Dictionary with forward, reverse mappings and metadata
        """
        # Tables to process (priority order based on plan)
        tables_to_map = [
            # Critical for site queries
            ("dcim_site", ["name", "slug"]),

            # Critical for device queries
            ("dcim_device", ["name", "serial", "asset_tag"]),

            # Useful for DNS queries
            ("ipam_ipaddress", ["dns_name"]),

            # Useful for tenant queries
            ("tenancy_tenant", ["name", "slug"]),

            # Lower priority
            ("dcim_interface", ["name"]),
            ("ipam_vlan", ["name"]),
            ("circuits_provider", ["name", "slug"]),
            ("circuits_circuit", ["cid"]),
        ]

        total_mappings = 0
        tables_processed = 0

        for table, columns in tables_to_map:
            for column in columns:
                try:
                    mappings_created = self.process_table_column(table, column)
                    total_mappings += mappings_created
                    if mappings_created > 0:
                        tables_processed += 1
                except Exception as e:
                    logger.error(f"❌ Failed to process {table}.{column}: {e}")
                    continue

        # Add metadata
        self.mappings["metadata"] = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "production_db": "netbox@localhost:8000",
            "anonymized_db": "netbox_anonymized@localhost:8001",
            "tables_processed": tables_processed,
            "total_mappings": total_mappings,
            "schema_version": "1.0"
        }

        self.total_mappings = total_mappings
        return self.mappings

    def validate_mappings(self) -> List[str]:
        """
        Validate generated mappings for correctness.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check bidirectionality
        for key in self.mappings["forward"]:
            if key not in self.mappings["reverse"]:
                errors.append(f"Missing reverse mapping for {key}")
            else:
                # Check every forward mapping has reverse
                for original, anonymized in self.mappings["forward"][key].items():
                    if anonymized not in self.mappings["reverse"][key]:
                        errors.append(f"Forward mapping {original}→{anonymized} missing reverse")
                    elif self.mappings["reverse"][key][anonymized] != original:
                        errors.append(f"Reverse mapping mismatch for {anonymized}")

        # Check hash formats
        for key in self.mappings["forward"]:
            for original, anonymized in self.mappings["forward"][key].items():
                if len(anonymized) == 64:
                    # Should be SHA256 (hex)
                    if not re.match(r'^[a-f0-9]{64}$', anonymized):
                        errors.append(f"Invalid SHA256 hash: {anonymized}")
                elif len(anonymized) == 32:
                    # Should be MD5 (hex)
                    if not re.match(r'^[a-f0-9]{32}$', anonymized):
                        errors.append(f"Invalid MD5 hash: {anonymized}")
                # Else could be other format (e.g., masked address)

        return errors

    def save_mappings(self, output_dir: str = "backend/anonymization/mappings") -> str:
        """
        Save mappings to JSON file with timestamp.

        Args:
            output_dir: Directory to save mappings

        Returns:
            Path to saved file
        """
        # Create output directory if needed
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mappings_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        # Save mappings
        with open(filepath, 'w') as f:
            json.dump(self.mappings, f, indent=2, sort_keys=True)

        logger.info(f"💾 Saved to: {filepath}")

        # Create symlink to latest
        latest_link = os.path.join(output_dir, "mappings_latest.json")
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(os.path.basename(filepath), latest_link)
        logger.info(f"🔗 Created symlink: {latest_link}")

        return filepath

    def close_connections(self):
        """Close database connections."""
        if self.prod_conn:
            self.prod_conn.close()
        if self.anon_conn:
            self.anon_conn.close()

    def run(self) -> bool:
        """
        Run the complete mapping generation process.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Connect to databases
            self.connect_databases()

            # Generate mappings
            logger.info("\n📊 Generating mappings...")
            self.generate_mappings()

            # Validate mappings
            logger.info("\n🔍 Validating mappings...")
            errors = self.validate_mappings()
            if errors:
                logger.error("❌ Mapping validation failed:")
                for error in errors:
                    logger.error(f"  - {error}")
                return False
            logger.info("✅ Mapping validation passed")

            # Save mappings
            logger.info("\n💾 Saving mappings...")
            filepath = self.save_mappings()

            # Print summary
            logger.info("\n" + "="*50)
            logger.info(f"✅ Generated {self.total_mappings} total mappings")
            logger.info(f"📁 Saved to: {filepath}")
            logger.info("="*50)

            return True

        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            return False

        finally:
            self.close_connections()


def main():
    """Main entry point."""
    logger.info("="*50)
    logger.info("🚀 Netbox Anonymization Mapping Generator")
    logger.info("="*50)

    generator = MappingGenerator()
    success = generator.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()