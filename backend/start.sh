#!/bin/bash
set -e

# If the SQLite database doesn't exist, we're on a fresh ephemeral disk.
# We'll seed the demo data so the app isn't completely empty.
if [ ! -f "trustmesh.db" ]; then
    echo "SQLite database not found. Seeding initial demo data..."
    python scripts/seed_demo_data.py
    python scripts/seed_ledger_entries.py
fi

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
