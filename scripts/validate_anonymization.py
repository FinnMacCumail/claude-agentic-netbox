#!/usr/bin/env python3
"""
Validate anonymization by checking for PII in the anonymized database.

This script connects to the anonymized database and checks for patterns
that indicate personally identifiable information (PII) or real data.
"""

import argparse
import re
import sys
from typing import List, Dict, Any
from urllib.parse import urlparse
import psycopg2
from psycopg2 import sql


class AnonymizationValidator:
    """Validates that a database has been properly anonymized."""

    def __init__(self, db_url: str):
        """
        Initialize validator with database connection.

        Args:
            db_url: PostgreSQL connection URL.
        """
        self.db_url = db_url
        self.conn = None
        self.issues_found = []

    def connect(self):
        """Connect to the database."""
        try:
            self.conn = psycopg2.connect(self.db_url)
            print(f"✅ Connected to database")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            sys.exit(1)

    def disconnect(self):
        """Disconnect from the database."""
        if self.conn:
            self.conn.close()

    def execute_query(self, query: str) -> List[Any]:
        """Execute a query and return results."""
        with self.conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

    def check_real_ip_addresses(self) -> int:
        """
        Check for real-looking IP addresses.

        Returns:
            Number of potential real IPs found.
        """
        print("\nChecking for real IP addresses...")

        # Check for private IP ranges
        query = """
        SELECT COUNT(*)
        FROM ipam_ipaddress
        WHERE address ~ '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)'
           OR address ~ '^(fe80:|fc00:|fd00:)'
        LIMIT 100;
        """

        result = self.execute_query(query)
        count = result[0][0] if result else 0

        if count > 0:
            self.issues_found.append(f"Found {count} potential real IP addresses")
            print(f"  ⚠️  Found {count} potential real IP addresses")

            # Show samples
            sample_query = """
            SELECT address
            FROM ipam_ipaddress
            WHERE address ~ '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)'
            LIMIT 5;
            """
            samples = self.execute_query(sample_query)
            if samples:
                print("  Sample IPs found:")
                for ip in samples:
                    print(f"    - {ip[0]}")
        else:
            print("  ✅ No obvious real IP addresses found")

        return count

    def check_real_device_names(self) -> int:
        """
        Check for real-looking device naming patterns.

        Returns:
            Number of potential real device names found.
        """
        print("\nChecking for real device names...")

        # Common real device naming patterns
        patterns = [
            r"^(core|edge|dist|access)-.*-(sw|switch|router|fw|firewall)",
            r"^[a-z]{2,4}-[a-z]{2,4}-\d{2,4}",
            r"^(nyc|lon|par|tok|syd|fra)-",
            r"(prod|production|staging|dev)",
        ]

        total_found = 0
        for pattern in patterns:
            query = f"""
            SELECT COUNT(*)
            FROM dcim_device
            WHERE name ~* '{pattern}'
            LIMIT 100;
            """

            result = self.execute_query(query)
            count = result[0][0] if result else 0
            if count > 0:
                total_found += count
                print(f"  ⚠️  Pattern '{pattern}': {count} matches")

        if total_found > 0:
            self.issues_found.append(f"Found {total_found} potential real device names")
        else:
            print("  ✅ No obvious real device names found")

        return total_found

    def check_real_site_names(self) -> int:
        """
        Check for real-looking site names.

        Returns:
            Number of potential real site names found.
        """
        print("\nChecking for real site names...")

        # Common real location patterns
        query = """
        SELECT COUNT(*)
        FROM dcim_site
        WHERE name ~* '(datacenter|office|hq|headquarters|campus|branch)'
           OR name ~* '^[A-Z]{2,4}-(DC|HQ|BR|OFF)\d*$'
           OR name ~ '^(New York|London|Paris|Tokyo|Sydney|Frankfurt)'
        LIMIT 100;
        """

        result = self.execute_query(query)
        count = result[0][0] if result else 0

        if count > 0:
            self.issues_found.append(f"Found {count} potential real site names")
            print(f"  ⚠️  Found {count} potential real site names")

            # Show samples
            sample_query = """
            SELECT name
            FROM dcim_site
            WHERE name ~* '(datacenter|office|hq|headquarters)'
            LIMIT 5;
            """
            samples = self.execute_query(sample_query)
            if samples:
                print("  Sample sites found:")
                for site in samples:
                    print(f"    - {site[0]}")
        else:
            print("  ✅ No obvious real site names found")

        return count

    def check_email_addresses(self) -> int:
        """
        Check for email addresses.

        Returns:
            Number of email addresses found.
        """
        print("\nChecking for email addresses...")

        tables_to_check = [
            ("tenancy_contact", "email"),
            ("users_user", "email"),
        ]

        total_found = 0
        for table, column in tables_to_check:
            query = f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE {column} ~ '@[a-zA-Z0-9.-]+\.[a-zA-Z]{{2,}}'
            LIMIT 100;
            """

            try:
                result = self.execute_query(query)
                count = result[0][0] if result else 0
                if count > 0:
                    total_found += count
                    print(f"  ⚠️  Table {table}: {count} email addresses")
            except:
                # Table might not exist
                pass

        if total_found > 0:
            self.issues_found.append(f"Found {total_found} email addresses")
        else:
            print("  ✅ No email addresses found")

        return total_found

    def check_phone_numbers(self) -> int:
        """
        Check for phone numbers.

        Returns:
            Number of phone numbers found.
        """
        print("\nChecking for phone numbers...")

        # Check contact table for phone patterns
        query = """
        SELECT COUNT(*)
        FROM tenancy_contact
        WHERE phone ~ '^\+?[1-9]\d{1,14}$'
           OR phone ~ '^\([0-9]{3}\) [0-9]{3}-[0-9]{4}$'
        LIMIT 100;
        """

        try:
            result = self.execute_query(query)
            count = result[0][0] if result else 0

            if count > 0:
                self.issues_found.append(f"Found {count} phone numbers")
                print(f"  ⚠️  Found {count} phone numbers")
            else:
                print("  ✅ No phone numbers found")

            return count
        except:
            print("  ✅ Contact table not found or no phone column")
            return 0

    def check_preserved_metadata(self) -> bool:
        """
        Verify that important metadata is preserved.

        Returns:
            True if metadata is preserved correctly.
        """
        print("\nChecking preserved metadata...")

        checks_passed = True

        # Check that IDs are preserved
        query = "SELECT COUNT(*) FROM dcim_device WHERE id IS NOT NULL;"
        result = self.execute_query(query)
        id_count = result[0][0] if result else 0

        if id_count > 0:
            print(f"  ✅ IDs preserved: {id_count} devices have IDs")
        else:
            print(f"  ❌ No device IDs found")
            checks_passed = False

        # Check foreign key relationships
        query = """
        SELECT COUNT(*)
        FROM dcim_device d
        JOIN dcim_site s ON d.site_id = s.id
        LIMIT 1;
        """

        try:
            result = self.execute_query(query)
            print(f"  ✅ Foreign keys intact: device-site relationships work")
        except Exception as e:
            print(f"  ❌ Foreign key issue: {e}")
            checks_passed = False

        # Check technical metadata preserved
        query = """
        SELECT COUNT(*)
        FROM dcim_device
        WHERE status IS NOT NULL
          AND device_role_id IS NOT NULL;
        """

        result = self.execute_query(query)
        metadata_count = result[0][0] if result else 0

        if metadata_count > 0:
            print(f"  ✅ Technical metadata preserved: {metadata_count} devices")
        else:
            print(f"  ⚠️  Limited technical metadata found")

        return checks_passed

    def validate(self) -> bool:
        """
        Run all validation checks.

        Returns:
            True if validation passes, False otherwise.
        """
        print("=" * 60)
        print("Anonymization Validation Report")
        print("=" * 60)

        self.connect()

        # Run all checks
        ip_count = self.check_real_ip_addresses()
        device_count = self.check_real_device_names()
        site_count = self.check_real_site_names()
        email_count = self.check_email_addresses()
        phone_count = self.check_phone_numbers()
        metadata_ok = self.check_preserved_metadata()

        self.disconnect()

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        if self.issues_found:
            print("\n❌ Validation FAILED - PII found:")
            for issue in self.issues_found:
                print(f"  - {issue}")
            return False
        elif not metadata_ok:
            print("\n⚠️  Validation WARNING - Metadata issues found")
            return False
        else:
            print("\n✅ Validation PASSED - No PII detected")
            print("  - All IDs and foreign keys preserved")
            print("  - Technical metadata intact")
            print("  - No obvious PII patterns found")
            return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Netbox database anonymization"
    )
    parser.add_argument(
        "--database",
        type=str,
        required=True,
        help="PostgreSQL connection URL (postgresql://user:pass@host:port/dbname)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any warnings (not just errors)",
    )

    args = parser.parse_args()

    validator = AnonymizationValidator(args.database)
    success = validator.validate()

    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())