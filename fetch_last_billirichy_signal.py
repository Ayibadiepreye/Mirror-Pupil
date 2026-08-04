#!/usr/bin/env python3
"""
Fetch the last signal from BillirichyFX Telegram channel.
Shows message details so you can manually re-inject it into the bot.
"""

import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from datetime import datetime, timedelta

# Load environment
load_dotenv()

async def fetch_last_signal():
    """Fetch recent messages from BillirichyFX channel."""
    
    # Get Telegram credentials from .env
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    
    if not all([api_id, api_hash, phone]):
        print("❌ Missing Telegram credentials in .env file")
        print("   Need: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE")
        return
    
    # BillirichyFX channel ID
    billirichy_channel_id = -1001859598768
    
    print("🔗 Connecting to Telegram...")
    
    # Create client (use existing session files)
    # The session files (telegram_session.session) contain auth data
    client = TelegramClient('telegram_session', int(api_id), api_hash)
    
    try:
        # Start without phone - will use existing session
        await client.start()
        print("✅ Connected to Telegram using existing session\n")
        
        # Get channel entity
        channel = await client.get_entity(billirichy_channel_id)
        print(f"📢 Channel: {channel.title}\n")
        
        # Fetch last 10 messages
        print("📥 Fetching last 10 messages...\n")
        print("="*80)
        
        messages = await client.get_messages(channel, limit=10)
        
        for idx, msg in enumerate(messages, 1):
            print(f"\nMessage #{idx}")
            print("-"*80)
            print(f"Message ID:  {msg.id}")
            print(f"Date:        {msg.date}")
            print(f"Text:")
            print("-"*80)
            if msg.text:
                print(msg.text)
            else:
                print("(No text / Media message)")
            print("="*80)
        
        # Show the most recent entry signal
        print("\n\n🎯 MOST RECENT SIGNAL MESSAGE:")
        print("="*80)
        
        for msg in messages:
            if msg.text and any(keyword in msg.text.upper() for keyword in ['BUY', 'SELL', 'ENTRY', 'XAUUSD', 'EURUSD', 'GBPUSD']):
                print(f"Message ID:  {msg.id}")
                print(f"Date:        {msg.date}")
                print(f"Channel ID:  {billirichy_channel_id}")
                print(f"\nMessage Text:")
                print("-"*80)
                print(msg.text)
                print("="*80)
                print(f"\n💡 To manually re-inject this signal:")
                print(f"   1. Copy the message text above")
                print(f"   2. Check if it's already in message_cache (it shouldn't be)")
                print(f"   3. Use the manual execution API endpoint")
                print(f"   4. Or restart bot and it will process next signal with fixed code")
                break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.disconnect()
        print("\n✅ Disconnected from Telegram")

if __name__ == "__main__":
    asyncio.run(fetch_last_signal())
