"""
Check if the BillirichyFX channel ID in the database matches the actual Telegram channel.
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram_client import HumanLikeTelegramClient

load_dotenv()

async def main():
    """Check BillirichyFX channel ID"""
    
    print("=" * 70)
    print("BillirichyFX Channel ID Verification")
    print("=" * 70)
    print()
    
    # Get credentials from environment
    api_id = int(os.getenv("TELEGRAM_API_ID"))
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")
    encryption_key = os.getenv("TDLIB_ENCRYPTION_KEY")
    files_dir = os.getenv("TDLIB_FILES_DIR", "./tdlib_data")
    
    print(f"📱 Phone: {phone}")
    print(f"🔍 Looking up: https://t.me/billirichyfxsignals1")
    print()
    
    # Create client
    client = HumanLikeTelegramClient(
        api_id=api_id,
        api_hash=api_hash,
        phone=phone,
        encryption_key=encryption_key,
        files_dir=files_dir
    )
    
    try:
        print("⏳ Connecting to Telegram...")
        await client.start()
        print("✓ Connected to Telegram")
        print()
        
        # Search for the channel by username
        channel_username = "billirichyfxsignals1"
        
        print(f"🔍 Searching for @{channel_username}...")
        result = await client.client.searchPublicChat(username=channel_username)
        
        if result and hasattr(result, 'id'):
            channel_id = result.id
            title = result.title if hasattr(result, 'title') else "Unknown"
            
            print(f"✓ Found channel!")
            print()
            print(f"  Title: {title}")
            print(f"  Username: @{channel_username}")
            print(f"  Telegram ID: {channel_id}")
            print(f"  URL: https://t.me/{channel_username}")
            print()
            
            # Compare with database
            db_id = -1001859598768
            print("=" * 70)
            print("Database Comparison")
            print("=" * 70)
            print(f"  Found ID:    {channel_id}")
            print(f"  Database ID: {db_id}")
            print()
            
            if channel_id == db_id:
                print("✓ IDs MATCH - Channel is configured correctly!")
            else:
                print("❌ IDs DO NOT MATCH!")
                print()
                print("To fix, run this SQL command:")
                print(f"UPDATE channels SET channel_id = {channel_id} WHERE display_name = 'BillirichyFX';")
        else:
            print("❌ Could not find channel")
            print("   Possible reasons:")
            print("   1. Channel username is incorrect")
            print("   2. Channel is private")
            print("   3. You don't have access to the channel")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print()
        print("⏳ Disconnecting...")
        await client.stop()
        print("✓ Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
