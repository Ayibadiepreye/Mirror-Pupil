"""
Get the numeric channel ID from a Telegram channel link.
This uses the Telegram client to resolve the channel username to its numeric ID.
"""

import asyncio
import os
from dotenv import load_dotenv
from pytdbot import Client
from pytdbot.types import LogStreamFile

load_dotenv()

async def get_channel_id(channel_username: str):
    """
    Get numeric channel ID from username (e.g., 'billirichyfxsignals1' -> -1001859598768)
    
    Args:
        channel_username: Username without @ or t.me/ (e.g., 'billirichyfxsignals1')
    """
    
    # Get Telegram credentials from environment
    api_id = int(os.getenv("TELEGRAM_API_ID"))
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")
    
    if not all([api_id, api_hash, phone]):
        print("❌ Missing Telegram credentials in .env file")
        print("   Required: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE")
        return None
    
    # Create client (user account, not bot)
    client = Client(
        api_id=api_id,
        api_hash=api_hash,
        phone=phone,
        database_encryption_key="mirror_pupil_tdlib",
        files_directory="tdlib_files_lookup",
        log_stream=LogStreamFile("tdlib_lookup.log"),
        sleep_threshold=120,
    )
    
    try:
        print(f"🔍 Looking up channel: @{channel_username}")
        print("⏳ Starting Telegram client...")
        
        await client.start()
        print("✓ Client connected")
        
        # Search for the channel
        result = await client.searchPublicChat(username=channel_username)
        
        if result and hasattr(result, 'id'):
            channel_id = result.id
            print(f"\n✓ Found channel!")
            print(f"  Username: @{channel_username}")
            print(f"  Numeric ID: {channel_id}")
            print(f"  Link: https://t.me/{channel_username}")
            
            # Get channel info
            if hasattr(result, 'title'):
                print(f"  Title: {result.title}")
            
            return channel_id
        else:
            print(f"❌ Could not find channel: @{channel_username}")
            print("   Make sure:")
            print("   1. The username is correct")
            print("   2. The channel is public")
            print("   3. The bot has access to the channel")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        await client.stop()
        print("\n✓ Client disconnected")


async def main():
    """Main entry point"""
    
    # Extract username from the URL
    channel_url = "https://t.me/billirichyfxsignals1"
    channel_username = channel_url.split('/')[-1]  # Gets 'billirichyfxsignals1'
    
    print("=" * 60)
    print("Telegram Channel ID Lookup")
    print("=" * 60)
    print()
    
    channel_id = await get_channel_id(channel_username)
    
    if channel_id:
        print("\n" + "=" * 60)
        print("Database Comparison")
        print("=" * 60)
        print(f"\nFound ID: {channel_id}")
        print(f"Database ID: -1001859598768")
        
        if channel_id == -1001859598768:
            print("\n✓ IDs MATCH - Channel is configured correctly!")
        else:
            print("\n❌ IDs DO NOT MATCH - Database needs to be updated!")
            print(f"\nRun this SQL to fix it:")
            print(f"UPDATE channels SET channel_id = {channel_id} WHERE display_name = 'BillirichyFX';")
    else:
        print("\n❌ Could not verify channel ID")


if __name__ == "__main__":
    asyncio.run(main())
