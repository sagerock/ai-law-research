#!/bin/bash
# Run database migration on production PostgreSQL
# Usage: ./run_production_migration.sh

if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable not set"
    echo "   Please set it to your Railway PostgreSQL URL:"
    echo "   export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    exit 1
fi

echo "================================================"
echo "Running Production Database Migration"
echo "================================================"
echo ""
echo "Creating ai_summaries table..."

psql "$DATABASE_URL" -f "$(dirname "$0")/add_ai_summaries_table.sql"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "Verifying table exists..."
    psql "$DATABASE_URL" -c "SELECT COUNT(*) as cached_summaries FROM ai_summaries;"
else
    echo ""
    echo "❌ Migration failed!"
    exit 1
fi
