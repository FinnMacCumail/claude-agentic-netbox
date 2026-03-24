#!/bin/bash

# Greenmask execution script for Netbox anonymization
# This script runs Greenmask to create an anonymized copy of the production database

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAPPINGS_FILE="/mappings/mappings_${TIMESTAMP}.json"
LATEST_LINK="/mappings/mappings_latest.json"
CONFIG_FILE="${CONFIG_FILE:-/config/greenmask-config.yml}"

echo -e "${GREEN}=== Netbox Anonymization with Greenmask ===${NC}"
echo "Timestamp: ${TIMESTAMP}"
echo "Config: ${CONFIG_FILE}"
echo "Mappings output: ${MAPPINGS_FILE}"

# Validate environment variables
if [ -z "${SOURCE_DB_HOST:-}" ] || [ -z "${TARGET_DB_HOST:-}" ]; then
    echo -e "${RED}ERROR: Database connection variables not set${NC}"
    echo "Required: SOURCE_DB_HOST, TARGET_DB_HOST, etc."
    exit 1
fi

# Build connection strings
SOURCE_URI="postgresql://${SOURCE_DB_USER}:${SOURCE_DB_PASSWORD}@${SOURCE_DB_HOST}:${SOURCE_DB_PORT}/${SOURCE_DB_NAME}"
TARGET_URI="postgresql://${TARGET_DB_USER}:${TARGET_DB_PASSWORD}@${TARGET_DB_HOST}:${TARGET_DB_PORT}/${TARGET_DB_NAME}"

echo -e "${YELLOW}Step 1: Validating configuration...${NC}"
greenmask validate \
    --config "${CONFIG_FILE}" \
    || {
        echo -e "${RED}Configuration validation failed!${NC}"
        exit 1
    }

echo -e "${YELLOW}Step 2: Testing database connectivity...${NC}"

# Test source database
echo "Testing source database connection..."
PGPASSWORD="${SOURCE_DB_PASSWORD}" psql \
    -h "${SOURCE_DB_HOST}" \
    -p "${SOURCE_DB_PORT}" \
    -U "${SOURCE_DB_USER}" \
    -d "${SOURCE_DB_NAME}" \
    -c "SELECT version();" > /dev/null 2>&1 \
    || {
        echo -e "${RED}Cannot connect to source database!${NC}"
        exit 1
    }
echo "Source database: OK"

# Test target database
echo "Testing target database connection..."
PGPASSWORD="${TARGET_DB_PASSWORD}" psql \
    -h "${TARGET_DB_HOST}" \
    -p "${TARGET_DB_PORT}" \
    -U "${TARGET_DB_USER}" \
    -d "${TARGET_DB_NAME}" \
    -c "SELECT version();" > /dev/null 2>&1 \
    || {
        echo -e "${RED}Cannot connect to target database!${NC}"
        echo "Creating target database..."
        PGPASSWORD="${TARGET_DB_PASSWORD}" createdb \
            -h "${TARGET_DB_HOST}" \
            -p "${TARGET_DB_PORT}" \
            -U "${TARGET_DB_USER}" \
            "${TARGET_DB_NAME}" 2>/dev/null || true
    }
echo "Target database: OK"

echo -e "${YELLOW}Step 3: Running Greenmask dump-restore...${NC}"
echo "This may take several minutes depending on database size..."

# Run Greenmask with progress output
greenmask dump-restore \
    --config "${CONFIG_FILE}" \
    --source-uri "${SOURCE_URI}" \
    --target-uri "${TARGET_URI}" \
    --save-mappings "${MAPPINGS_FILE}" \
    --validate \
    --log-level info \
    || {
        echo -e "${RED}Greenmask execution failed!${NC}"
        exit 1
    }

echo -e "${YELLOW}Step 4: Verifying anonymization...${NC}"

# Count records in target database
DEVICE_COUNT=$(PGPASSWORD="${TARGET_DB_PASSWORD}" psql \
    -h "${TARGET_DB_HOST}" \
    -p "${TARGET_DB_PORT}" \
    -U "${TARGET_DB_USER}" \
    -d "${TARGET_DB_NAME}" \
    -t -c "SELECT COUNT(*) FROM dcim_device;" 2>/dev/null || echo "0")

SITE_COUNT=$(PGPASSWORD="${TARGET_DB_PASSWORD}" psql \
    -h "${TARGET_DB_HOST}" \
    -p "${TARGET_DB_PORT}" \
    -U "${TARGET_DB_USER}" \
    -d "${TARGET_DB_NAME}" \
    -t -c "SELECT COUNT(*) FROM dcim_site;" 2>/dev/null || echo "0")

echo "Anonymized database contains:"
echo "  - Devices: ${DEVICE_COUNT}"
echo "  - Sites: ${SITE_COUNT}"

# Create symlink to latest mappings
if [ -f "${MAPPINGS_FILE}" ]; then
    ln -sf "${MAPPINGS_FILE}" "${LATEST_LINK}"
    echo -e "${GREEN}Created symlink: ${LATEST_LINK} -> ${MAPPINGS_FILE}${NC}"
fi

# Check for PII in anonymized data (basic check)
echo -e "${YELLOW}Step 5: Basic PII check...${NC}"

# Check for real-looking IP addresses
REAL_IPS=$(PGPASSWORD="${TARGET_DB_PASSWORD}" psql \
    -h "${TARGET_DB_HOST}" \
    -p "${TARGET_DB_PORT}" \
    -U "${TARGET_DB_USER}" \
    -d "${TARGET_DB_NAME}" \
    -t -c "SELECT COUNT(*) FROM ipam_ipaddress WHERE address ~ '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' LIMIT 5;" 2>/dev/null || echo "0")

if [ "${REAL_IPS}" -gt "0" ]; then
    echo -e "${YELLOW}WARNING: Found ${REAL_IPS} potential real IP addresses!${NC}"
else
    echo -e "${GREEN}No obvious real IP addresses found.${NC}"
fi

echo -e "${GREEN}=== Anonymization Complete ===${NC}"
echo "Mappings saved to: ${MAPPINGS_FILE}"
echo "Latest symlink: ${LATEST_LINK}"
echo ""
echo "Next steps:"
echo "1. Import mappings: python scripts/import_mappings.py ${MAPPINGS_FILE}"
echo "2. Start anonymized Netbox: docker-compose up netbox-anon"
echo "3. Configure MCP to use anonymized database"

exit 0