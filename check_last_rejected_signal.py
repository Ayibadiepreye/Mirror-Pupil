#!/usr/bin/env python3
"""
Check the last rejected BillirichyFX signal from notifications table.
Shows the signal details so you can manually add it to message_cache for re-execution.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment
load_dotenv()

async def check_last_rejected():
    """Find the last rejected signal from BillirichyFX."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Get BillirichyFX channel_id
        billirichy_channel_id = -1001859598768
        
        # Find last rejected trade notification
        print("🔍 Searching for last rejected BillirichyFX signal...\n")
        
        rejected = await conn.fetch("""
            SELECT 
                notification_id,
                created_at,
                title,
                message,
                metadata
            FROM notifications
            WHERE 
                category = 'RISK'
                AND severity = 'WARNING'
                AND title LIKE 'Trade Rejected:%'
                AND created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        if not rejected:
            print("✅ No rejected trades in the last 24 hours")
            await conn.close()
            return
        
        print(f"📋 Found {len(rejected)} rejected signal(s) in last 24 hours:\n")
        
        for idx, notif in enumerate(rejected, 1):
            print(f"{'='*60}")
            print(f"#{idx} - {notif['created_at']}")
            print(f"{'='*60}")
            print(f"Title:   {notif['title']}")
            print(f"Message: {notif['message']}")
            
            if notif['metadata']:
                import json
                meta = notif['metadata']
                print(f"\nSignal Details:")
                print(f"  Symbol:    {meta.get('symbol', 'N/A')}")
                print(f"  Direction: {meta.get('direction', 'N/A')}")
                print(f"  Reason:    {meta.get('reason', 'N/A')}")
                print(f"  Account:   {meta.get('account_key', 'N/A')}")
                print(f"  Channel:   {meta.get('channel_name', 'N/A')}")
            
            print()
        
        # Get the most recent one
        latest = rejected[0]
        print(f"\n{'='*60}")
        print(f"🎯 MOST RECENT REJECTED SIGNAL:")
        print(f"{'='*60}")
        
        if latest['metadata']:
            meta = latest['metadata']
            symbol = meta.get('symbol', 'UNKNOWN')
            direction = meta.get('direction', 'UNKNOWN')
            reason = meta.get('reason', 'UNKNOWN')
            
            print(f"Symbol:    {symbol}")
            print(f"Direction: {direction}")
            print(f"Rejected:  {latest['created_at']}")
            print(f"Reason:    {reason}")
            
            print(f"\n{'='*60}")
            print(f"⚠️  MANUAL RE-EXECUTION NOT RECOMMENDED")
            print(f"{'='*60}")
            print(f"The trade was rejected by risk enforcer for a reason.")
            print(f"")
            print(f"If you want to force it, you need:")
            print(f"1. The original Telegram message ID")
            print(f"2. Full signal details (entry, SL, TP)")
            print(f"")
            print(f"Better approach:")
            print(f"- Fix the code issue (smart fallback is now in place)")
            print(f"- Restart the bot")
            print(f"- Wait for next signal")
            print(f"")
            print(f"Or use the /execute_manual command from the bot (if available)")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_last_rejected())
