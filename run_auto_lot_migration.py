#!/usr/bin/env python
"""Run the auto calculate lot size migration"""
import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Read SQL file
sql_file = Path("backend/database/migrations/add_auto_calculate_lot_size.sql")
sql = sql_file.read_text()

# Connect and run
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

try:
    print("Running migration: add_auto_calculate_lot_size.sql")
    cur.execute(sql)
    conn.commit()
    print("✓ Migration completed successfully!")
    
    # Verify the column was added
    cur.execute("""
        SELECT column_name, data_type, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'accounts' 
        AND column_name = 'use_calculated_lot_size'
    """)
    result = cur.fetchone()
    if result:
        print(f"✓ Column added: {result[0]} ({result[1]}, default: {result[2]})")
    else:
        print("⚠ Column might have already existed")
        
except Exception as e:
    print(f"✗ Error: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()
