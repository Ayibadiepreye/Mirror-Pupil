#!/usr/bin/env python3
"""
Fetch last BillirichyFX signal using TDLib (same as telegram_client.py).
"""

import asyncio
import os
from dotenv import load_dotenv
from pytdbot import Client
from pytdbot.types import LogStreamFile

load_dotenv()

async def fetch_last_signal():
    """Fetch recent messages from BillirichyFX channel using TDLib."""
    
    # Get credentials from .env
    api_id = int(os.getenv('TELEGRAM_API_ID'))
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    
    billirichy_channel_id = -1001859598768
    
    print("🔗 Connecting to Telegram using TDLib...")
    
    # Create TDLib client (uses tdlib/database for session)
    client = Client(
        api_id=api_id,
        api_hash=api_hash,
        database_encryption_key="mirrorpupil_encryption",
        files_directory="tdlib/files",
        td_verbosity=1,
        td_log=LogStreamFile("tdlib.log")
    )
    
    try:
        await client.start()
        print("✅ Connected to Telegram\n")
        
        # Get channel info
        print(f"📢 Fetching messages from BillirichyFX (ID: {billirichy_channel_id})\n")
        
        # Get last 10 messages
        result = await client.getChatHistory(
            chat_id=billirichy_channel_id,
            limit=10,
            from_message_id=0
        )
        
        if not result or not result.messages:
            print("❌ No messages found")
            return
        
        print(f"📥 Found {len(result.messages)} recent messages\n")
        print("="*80)
        
        # Display all messages
        for idx, msg in enumerate(result.messages, 1):
            print(f"\nMessage #{idx}")
            print("-"*80)
            print(f"Message ID:  {msg.id}")
            print(f"Date:        {msg.date}")
            
            if hasattr(msg.content, 'text') and msg.content.text:
                print(f"Text:")
                print("-"*80)
                print(msg.content.text.text)
            else:
                print("(No text / Media message)")
            
            print("="*80)
        
        # Find the most recent entry signal
        print("\n\n🎯 SEARCHING FOR MOST RECENT ENTRY SIGNAL:")
        print("="*80)
        
        for msg in result.messages:
            if hasattr(msg.content, 'text') and msg.content.text:
                text = msg.content.text.text.upper()
                if any(keyword in text for keyword in ['BUY', 'SELL', 'ENTRY', 'XAUUSD', 'EURUSD', 'GBPUSD']):
                    print(f"\n✅ Found Entry Signal!")
                    print(f"Message ID:  {msg.id}")
                    print(f"Channel ID:  {billirichy_channel_id}")
                    print(f"Date:        {msg.date}")
                    print(f"\nMessage Text:")
                    print("-"*80)
                    print(msg.content.text.text)
                    print("="*80)
                    
                    print(f"\n💡 Signal Details:")
                    print(f"   Message ID:  {msg.id}")
                    print(f"   Channel ID:  {billirichy_channel_id}")
                    print(f"\n📝 To manually re-inject:")
                    print(f"   Copy the signal details above and provide:")
                    print(f"   - Symbol, Direction, Entry, SL, TP")
                    print(f"   Then I'll create the SQL to inject it.")
                    break
        else:
            print("❌ No entry signals found in last 10 messages")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.stop()
        print("\n✅ Disconnected from Telegram")

if __name__ == "__main__":
    asyncio.run(fetch_last_signal())
