# Production Database Setup

## Overview

The production PostgreSQL database on Railway needs to be initialized with the schema and populated with case data.

## Step 1: Get Railway PostgreSQL Connection String

1. Go to your Railway project: https://railway.app/project/your-project
2. Click on the **PostgreSQL** service
3. Go to the **Variables** tab
4. Copy the **DATABASE_URL** value (it looks like: `postgresql://postgres:password@hostname:5432/railway`)

## Step 2: Run the Setup Script

```bash
# Set the production database URL (get this from Railway's PostgreSQL service variables)
export DATABASE_URL='<your-railway-postgres-url>'

# Make the script executable
chmod +x scripts/setup_production_db.py

# Run the migration
python3 scripts/setup_production_db.py
```

## What the Script Does

1. **Creates Schema**: Runs `migrations/001_init.sql` to create all tables, indexes, and functions
2. **Migrates Courts**: Copies all court data from local to production
3. **Migrates Cases**: Copies all 102 Ohio Supreme Court cases from local to production
4. **Verifies**: Confirms all data was migrated successfully

## Expected Output

```
================================================================================
🔄 SETTING UP PRODUCTION DATABASE
================================================================================

📊 Connecting to production PostgreSQL...

📋 Creating database schema...
   ✅ Schema created successfully

📥 Connecting to local PostgreSQL...

📤 Migrating courts...
   ✅ Migrated X courts

📤 Migrating cases...
   Migrated 10/102 cases...
   Migrated 20/102 cases...
   ...

================================================================================
✅ MIGRATION COMPLETE!
================================================================================
  Courts migrated: X
  Cases migrated: 102
  Errors: 0

📊 Production Database Status:
  Total courts: X
  Total cases: 102

🎉 Your production database is ready!
```

## After Setup

Once the database is populated:
1. The backend will automatically connect to it (using Railway's DATABASE_URL)
2. Search results will include the case IDs
3. Case detail pages will load from PostgreSQL
4. The application will be fully functional

## Troubleshooting

**Error: "relation already exists"**
- This is safe to ignore - the script uses `IF NOT EXISTS` clauses
- It means the table was already created

**Error: "password authentication failed"**
- Double-check your DATABASE_URL
- Make sure you copied it exactly from Railway

**Error: "connection refused"**
- Your local PostgreSQL might not be running
- Start it with: `docker-compose up -d`
