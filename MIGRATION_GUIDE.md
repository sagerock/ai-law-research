# Production Database Migration Guide

The AI summary caching feature requires a new `ai_summaries` table in the production database.

## Quick Migration Steps

### Option 1: Using Python Script (Recommended)

1. Get your Railway PostgreSQL URL from the Railway dashboard:
   - Go to https://railway.app
   - Select your PostgreSQL service
   - Go to "Variables" tab
   - Copy the `DATABASE_URL` value

2. Run the migration script:
   ```bash
   cd /Volumes/T7/Scripts/AI\ Law\ Researcher/legal-research-tool
   export DATABASE_URL='your-postgresql-url-here'
   python3 scripts/migrate_production.py
   ```

### Option 2: Using Railway CLI

If you have the Railway CLI installed:

```bash
railway run python3 scripts/migrate_production.py
```

### Option 3: Manual SQL (Railway Dashboard)

1. Go to your Railway PostgreSQL service
2. Open the "Query" tab
3. Copy and paste the contents of `scripts/add_ai_summaries_table.sql`
4. Execute the query

## What This Creates

The migration creates:
- `ai_summaries` table with columns:
  - `id` (primary key)
  - `case_id` (foreign key to cases)
  - `summary` (the AI-generated brief)
  - `model` (e.g., "gpt-5-mini")
  - `input_tokens` and `output_tokens`
  - `cost` (in USD)
  - `created_at` timestamp
- Index on `case_id` for fast lookups
- Unique constraint on `case_id` (one summary per case)

## Verification

After running the migration, verify it worked by visiting any case page on your production site. The AI summary should:
1. Not show an error on page load
2. Generate successfully when you click "Generate Brief"
3. Display instantly on subsequent visits to that case

## Troubleshooting

If you see `relation "ai_summaries" does not exist` errors:
- The migration hasn't been run yet
- Follow one of the options above to create the table

If the table exists but summaries aren't caching:
- Check the Railway logs for any database connection errors
- Verify the `DATABASE_URL` environment variable is set in Railway
