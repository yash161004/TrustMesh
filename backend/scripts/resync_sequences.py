import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable is missing.")
        sys.exit(1)
        
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
    print(f"Connecting to Postgres to resync sequences...")
    engine = create_async_engine(database_url, echo=False)
    
    # These tables have auto-increment integer IDs
    tables_with_sequences = [
        "negotiation_messages",
        "ledger_entries",
        "trust_reports"
    ]
    
    # These tables use UUIDs and do not have sequences
    uuid_tables = [
        "negotiation_sessions",
        "users",
        "organizations"
    ]
    
    async with engine.begin() as conn:
        for table in tables_with_sequences:
            seq_name = f"{table}_id_seq"
            print(f"Syncing sequence {seq_name} for table {table}...")
            
            # Execute sequence resync
            query = f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table}), 1))"
            try:
                result = await conn.execute(text(query))
                new_val = result.scalar()
                print(f"  -> Success. Sequence {seq_name} synced to {new_val}.")
            except Exception as e:
                print(f"  -> Error syncing {seq_name}: {e}")
                
        for table in uuid_tables:
            print(f"Skipping table {table} (Uses UUID primary keys, no sequence to sync).")
            
    await engine.dispose()
    print("Resync complete.")

if __name__ == "__main__":
    asyncio.run(main())
