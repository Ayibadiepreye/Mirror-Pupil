"""
Fetch the last 2 messages from BillirichyFX channel to verify it's the correct channel.
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram_client import HumanLikeTelegramClient
from datetime import datetime

load_dotenv()

async def fetch_recent_messages(channel_id: int, limit: int = 2):
    """
    Fetch the most recent messages from a channel.
    
    Args:
        channel_id: Telegram channel ID (e.g., -1001859598768)
        limit: Number of messages to fetch
    """
    
    # Get credentials from environment
    api_id = int(os.getenv("TELEGRAM_API_ID"))
    api_hash = os.getenv("TELEGRAM_API_HASH")
    phone = os.getenv("TELEGRAM_PHONE")
    encryption_key = os.getenv("TDLIB_ENCRYPTION_KEY")
    files_dir = os.getenv("TDLIB_FILES_DIR", "./tdlib_data")
    
    print("=" * 80)
    print("BillirichyFX Channel Message Verification")
    print("=" * 80)
    print(f"\n📱 Phone: {phone}")
    print(f"🔍 Channel ID: {channel_id}")
    print(f"📊 Fetching last {limit} messages...")
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
        
        # Fetch chat history
        print(f"📥 Fetching messages from channel {channel_id}...")
        
        # Get chat history
        result = await client.client.getChatHistory(
            chat_id=channel_id,
            from_message_id=0,
            offset=0,
            limit=limit
        )
        
        if result and hasattr(result, 'messages') and result.messages:
            messages = result.messages
            print(f"✓ Found {len(messages)} message(s)")
            print()
            print("=" * 80)
            print("MESSAGES")
            print("=" * 80)
            print()
            
            for i, msg in enumerate(messages, 1):
                msg_id = msg.id if hasattr(msg, 'id') else 'Unknown'
                msg_date = datetime.fromtimestamp(msg.date) if hasattr(msg, 'date') else 'Unknown'
                
                # Extract message content
                content = "No text content"
                if hasattr(msg, 'content'):
                    if hasattr(msg.content, 'text'):
                        if hasattr(msg.content.text, 'text'):
                            content = msg.content.text.text
                    elif hasattr(msg.content, 'caption'):
                        if hasattr(msg.content.caption, 'text'):
                            content = msg.content.caption.text
                
                print(f"Message #{i}")
                print(f"  ID: {msg_id}")
                print(f"  Date: {msg_date}")
                print(f"  Content:")
                print("-" * 80)
                print(content)
                print("-" * 80)
                print()
            
            # Verify if these look like trading signals
            print("=" * 80)
            print("VERIFICATION")
            print("=" * 80)
            print()
            
            # Check for trading-related keywords
            all_text = " ".join([
                (msg.content.text.text if hasattr(msg, 'content') and 
                 hasattr(msg.content, 'text') and 
                 hasattr(msg.content.text, 'text') else "")
                for msg in messages
            ]).upper()
            
            trading_keywords = ['BUY', 'SELL', 'GOLD', 'XAUUSD', 'ENTRY', 'SL', 'TP', 'LONG', 'SHORT']
            found_keywords = [kw for kw in trading_keywords if kw in all_text]
            
            if found_keywords:
                print(f"✓ Trading keywords found: {', '.join(found_keywords)}")
                print("✓ This appears to be a trading signals channel!")
            else:
                print("⚠️ No trading keywords found in recent messages")
                print("   Either:")
                print("   1. This is the correct channel but no recent signals")
                print("   2. This might be the wrong channel")
            
        else:
            print("❌ No messages found in channel")
            print("   Possible reasons:")
            print("   1. Channel is empty")
            print("   2. You don't have access to the channel")
            print("   3. Channel ID is incorrect")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print()
        print("⏳ Disconnecting...")
        await client.stop()
        print("✓ Disconnected")


async def main():
    """Main entry point"""
    
    # BillirichyFX channel ID from database
    channel_id = -1001859598768
    
    await fetch_recent_messages(channel_id, limit=2)


if __name__ == "__main__":
    asyncio.run(main())
