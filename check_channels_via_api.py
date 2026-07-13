#!/usr/bin/env python3
"""
Check channel subscriptions via the backend API
"""

import requests
import json

# Backend API URL (Tailscale)
API_BASE = "https://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil/api"

# You'll need a valid auth token - this is just for checking
# If AUTH_DISABLED=true in backend, this will work without auth

def check_channels():
    print("=" * 100)
    print("CHECKING CHANNEL SUBSCRIPTIONS VIA API")
    print("=" * 100)
    print()
    
    try:
        # Get all accounts
        print("Fetching accounts...")
        response = requests.get(f"{API_BASE}/accounts/", timeout=10)
        
        if response.status_code == 401:
            print("❌ Authentication required. Backend AUTH_DISABLED must be true or you need a valid token.")
            return
        
        response.raise_for_status()
        accounts = response.json()
        
        print(f"✓ Found {len(accounts)} account(s)\n")
        
        # Get all channels
        print("Fetching channels...")
        response = requests.get(f"{API_BASE}/channels/", timeout=10)
        response.raise_for_status()
        channels = response.json()
        
        print(f"✓ Found {len(channels)} channel(s)\n")
        
        # Display channels
        print("=" * 100)
        print("AVAILABLE CHANNELS:")
        print("=" * 100)
        for ch in channels:
            status = "✅ ENABLED" if ch['enabled'] else "❌ DISABLED"
            print(f"  {ch['display_name']:<20} (ID: {ch['channel_id']:<20}) {status}")
        
        print("\n" + "=" * 100)
        print("ACCOUNTS AND THEIR SUBSCRIPTIONS:")
        print("=" * 100)
        
        # Check each account
        for account in accounts:
            account_key = account['account_key']
            display_name = account.get('display_name') or account_key
            paused = account.get('paused', False)
            breached = account.get('breached', False)
            
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
            
            # Get subscriptions for this account
            try:
                response = requests.get(
                    f"{API_BASE}/accounts/{requests.utils.quote(account_key, safe='')}/subscriptions",
                    timeout=10
                )
                response.raise_for_status()
                subscriptions = response.json()
                
                print(f"   Channel Subscriptions:")
                
                if not subscriptions:
                    print(f"      ⚠️  No channel subscriptions")
                else:
                    for sub in subscriptions:
                        channel_name = sub.get('channel_name', 'Unknown')
                        enabled = sub.get('enabled', False)
                        
                        if enabled:
                            print(f"      ✅ {channel_name} - ENABLED")
                        else:
                            print(f"      ❌ {channel_name} - DISABLED")
            
            except Exception as e:
                print(f"      ❌ Error fetching subscriptions: {e}")
        
        # Summary
        print("\n" + "=" * 100)
        print("SUMMARY:")
        print("=" * 100)
        
        billirichy_count = 0
        for account in accounts:
            try:
                response = requests.get(
                    f"{API_BASE}/accounts/{requests.utils.quote(account['account_key'], safe='')}/subscriptions",
                    timeout=10
                )
                if response.status_code == 200:
                    subs = response.json()
                    for sub in subs:
                        if 'BillirichyFX' in sub.get('channel_name', '') and sub.get('enabled'):
                            billirichy_count += 1
                            break
            except:
                pass
        
        print(f"Total Accounts: {len(accounts)}")
        print(f"Accounts with BillirichyFX enabled: {billirichy_count}")
        print(f"Accounts without BillirichyFX: {len(accounts) - billirichy_count}")
        
        print("\n" + "=" * 100)
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend API")
        print("   Make sure the backend is running and accessible via Tailscale")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_channels()
