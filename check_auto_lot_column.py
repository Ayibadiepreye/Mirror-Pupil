#!/usr/bin/env python
"""Check if use_calculated_lot_size column exists"""
import asyncio
from backend.database.manager import DatabaseManager

async def main():
    db = DatabaseManager()
    await db.connect()
    
    # Check if column exists
    result = await db.fetch_one("""
        SELECT column_name, data_type, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'accounts' 
        AND column_name = 'use_calculated_lot_size'
    """)
    
    if result:
        print(f"✓ Column EXISTS: {result['column_name']} ({result['data_type']}, default: {result['column_default']})")
    else:
        print("✗ Column DOES NOT EXIST - need to run migration")
        print("\nTo add it, run:")
        print("python -c \"import asyncio; from backend.database.manager import DatabaseManager; asyncio.run(DatabaseManager().execute_file('backend/database/migrations/add_auto_calculate_lot_size.sql'))\"")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
