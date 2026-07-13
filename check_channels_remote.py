#!/usr/bin/env python3
"""
Check channel subscriptions - Run this on the server
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection - using localhost since running on the server
DATABASE_URL = "postgresql://kirito:Mirrorpupil2026@localhost:5432/mirror_pupil"

def check_subscriptions():
    """Check which channels are enabled for each account"""
    
    print(f"Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        print("✓ Connected to database\n")
        
        # First, get all channels
        print("=" * 100)
        print("AVAILABLE CHANNELS:")
        print("=" * 100)
        
        cur.execute("""
            SELECT channel_id, display_name, enabled
            FROM channels
            ORDER BY display_name
        """)
        
        channels = cur.fetchall()
        channel_map = {}
        
        for ch in channels:
            status = "✅ ENABLED" if ch['enabled'] else "❌ DISABLED"
            print(f"  {ch['display_name']:<20} (ID: {ch['channel_id']:<20}) {status}")
            channel_map[ch['channel_id']] = ch['display_name']
        
        # Get all accounts
        print("\n" + "=" * 100)
        print("ACCOUNTS AND THEIR CHANNEL SUBSCRIPTIONS:")
        print("=" * 100)
        
        cur.execute("""
            SELECT account_key, display_name, paused, breached
            FROM accounts
            ORDER BY account_key
        """)
        
        accounts = cur.fetchall()
        
        if not accounts:
            print("\n⚠️  No accounts found in database")
        else:
            for account in accounts:
                account_key = account['account_key']
                display_name = account['display_name'] or account_key
                paused = account['paused']
                breached = account['breached']
                
                # Get subscriptions for this account
                cur.execute("""
                    SELECT cs.channel_id, cs.enabled, c.display_name
                    FROM channel_subscriptions cs
                    JOIN channels c ON cs.channel_id = c.channel_id
                    WHERE cs.account_key = %s
                    ORDER BY c.display_name
                """, (account_key,))
                
                subs = cur.fetchall()
                
                print(f"\n📊 Account: {display_name}")
                print(f"   Key: {account_key}")
                
                # Account status
                status_parts = []
                if paused:
                    status_parts.append("⏸️  PAUSED")
                if breached:
                    status_parts.append("🚨 BREACHED")
                if not paused and not breached:
                    status_parts.append("✅ ACTIVE")
                
                print(f"   Status: {' | '.join(status_parts)}")
                print(f"   Channel Subscriptions:")
                
                if not subs:
                    print(f"      ⚠️  No channel subscriptions found")
                else:
                    for sub in subs:
                        channel_name = sub['display_name']
                        sub_enabled = sub['enabled']
                        
                        if sub_enabled:
                            print(f"      ✅ {channel_name} - ENABLED")
                        else:
                            print(f"      ❌ {channel_name} - DISABLED")
        
        # Summary
        print("\n" + "=" * 100)
        print("SUMMARY:")
        print("=" * 100)
        
        total_accounts = len(accounts)
        
        # Count accounts with BillirichyFX enabled
        cur.execute("""
            SELECT COUNT(DISTINCT cs.account_key)
            FROM channel_subscriptions cs
            JOIN channels c ON cs.channel_id = c.channel_id
            WHERE c.display_name = 'BillirichyFX'
            AND cs.enabled = TRUE
        """)
        
        billirichy_enabled = cur.fetchone()['count']
        
        # Count accounts with any channel subscription
        cur.execute("""
            SELECT COUNT(DISTINCT account_key)
            FROM channel_subscriptions
            WHERE enabled = TRUE
        """)
        
        accounts_with_subs = cur.fetchone()['count']
        
        print(f"Total Accounts: {total_accounts}")
        print(f"Accounts with at least one channel subscription: {accounts_with_subs}")
        print(f"Accounts with BillirichyFX enabled: {billirichy_enabled}")
        print(f"Accounts without any subscriptions: {total_accounts - accounts_with_subs}")
        
        print("\n" + "=" * 100)
        
        # Close connection
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_subscriptions()
