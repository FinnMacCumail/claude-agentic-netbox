#!/bin/bash
set -e

echo "🔒 Greenmask Database Anonymization"
echo "===================================="

# Configuration
CONFIG_TEMPLATE="/config/greenmask-config.yml"
CONFIG_FILE="/tmp/greenmask-config-generated.yml"

# Export all environment variables for substitution
export SOURCE_DB_HOST
export SOURCE_DB_PORT
export SOURCE_DB_NAME
export SOURCE_DB_USER
export SOURCE_DB_PASSWORD
export TARGET_DB_HOST
export TARGET_DB_PORT
export TARGET_DB_NAME
export TARGET_DB_USER
export TARGET_DB_PASSWORD

echo "📋 Configuration:"
echo "  Source: ${SOURCE_DB_USER}@${SOURCE_DB_HOST}:${SOURCE_DB_PORT}/${SOURCE_DB_NAME}"
echo "  Target: ${TARGET_DB_USER}@${TARGET_DB_HOST}:${TARGET_DB_PORT}/${TARGET_DB_NAME}"
echo ""

# Generate config file with environment variables substituted
echo "🔧 Generating configuration with environment variables..."
sed -e "s|\${SOURCE_DB_HOST}|${SOURCE_DB_HOST}|g" \
    -e "s|\${SOURCE_DB_PORT}|${SOURCE_DB_PORT}|g" \
    -e "s|\${SOURCE_DB_NAME}|${SOURCE_DB_NAME}|g" \
    -e "s|\${SOURCE_DB_USER}|${SOURCE_DB_USER}|g" \
    -e "s|\${SOURCE_DB_PASSWORD}|${SOURCE_DB_PASSWORD}|g" \
    -e "s|\${TARGET_DB_HOST}|${TARGET_DB_HOST}|g" \
    -e "s|\${TARGET_DB_PORT}|${TARGET_DB_PORT}|g" \
    -e "s|\${TARGET_DB_NAME}|${TARGET_DB_NAME}|g" \
    -e "s|\${TARGET_DB_USER}|${TARGET_DB_USER}|g" \
    -e "s|\${TARGET_DB_PASSWORD}|${TARGET_DB_PASSWORD}|g" \
    "${CONFIG_TEMPLATE}" > "${CONFIG_FILE}"

echo "✅ Configuration generated at ${CONFIG_FILE}"
echo ""

# Validate configuration
echo "🔍 Validating configuration..."
greenmask --config "${CONFIG_FILE}" validate

if [ $? -ne 0 ]; then
    echo "❌ Configuration validation failed"
    exit 1
fi

echo "✅ Configuration is valid"
echo ""

# Run dump (anonymize data from source)
echo "📤 Starting dump from source database..."
echo "   This will:"
echo "   1. Connect to production Netbox database"
echo "   2. Dump all tables with pg_dump"
echo "   3. Apply transformations (hashing, masking)"
echo "   4. Store anonymized dump in /mappings"
echo ""

greenmask --config "${CONFIG_FILE}" --log-level info dump

if [ $? -ne 0 ]; then
    echo "❌ Dump failed"
    exit 1
fi

echo "✅ Dump completed successfully"
echo ""

# Run restore (load anonymized data to target)
echo "📥 Starting restore to target database..."
echo "   This will:"
echo "   1. Connect to anonymized Netbox database"
echo "   2. Restore all tables with pg_restore"
echo "   3. Verify data integrity"
echo ""

greenmask --config "${CONFIG_FILE}" --log-level info restore latest

if [ $? -ne 0 ]; then
    echo "❌ Restore failed"
    exit 1
fi

echo ""
echo "✅ Anonymization completed successfully!"
echo ""
echo "📊 Summary:"
echo "  - Source database dumped with transformations"
echo "  - Anonymized data restored to target database"
echo "  - Mappings stored in /mappings directory"
echo ""
echo "🔍 Verify the anonymization:"
echo "  docker exec netbox-anon-db psql -U netbox -d netbox_anonymized -c 'SELECT COUNT(*) FROM dcim_device;'"
echo "  docker exec netbox-anon-db psql -U netbox -d netbox_anonymized -c 'SELECT id, name FROM dcim_device LIMIT 5;'"
