"""
Check which parser/logic module Setonfx channel is using
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.database.manager import DatabaseManager
from loguru import logger

async def main():
    # Initialize database
    db = DatabaseManager()
    
    try:
        # Get all enabled channels
        channels = await db.get_enabled_channels()
        
        # Find Setonfx or the channel that received the message
        setonfx_channel = None
        message_channel = None
        
        for ch in channels:
            if ch.display_name == 'Setonfx' or ch.channel_id == -1003708350949:
                setonfx_channel = ch
            if ch.channel_id == -1001859598768:
                message_channel = ch
        
        print("\n" + "="*80)
        print("CHANNEL INVESTIGATION")
        print("="*80)
        
        if setonfx_channel:
            print("\n✓ SETONFX CHANNEL FOUND:")
            print(f"  Channel ID:            {setonfx_channel.channel_id}")
            print(f"  Display Name:          {setonfx_channel.display_name}")
            print(f"  Signal Prefix:         {setonfx_channel.signal_prefix}")
            print(f"  Entry Logic Module:    {setonfx_channel.entry_logic_module}")
            print(f"  Management Module:     {setonfx_channel.management_logic_module}")
            print(f"  Priority:              {setonfx_channel.priority}")
            print(f"  Enabled:               {setonfx_channel.enabled}")
        else:
            print("\n❌ SETONFX CHANNEL NOT FOUND IN DATABASE")
        
        print("\n" + "-"*80)
        print(f"MESSAGE RECEIVED FROM: -1001859598768")
        print("-"*80)
        
        if message_channel:
            print(f"\n✓ CHANNEL -1001859598768 FOUND:")
            print(f"  Display Name:          {message_channel.display_name}")
            print(f"  Signal Prefix:         {message_channel.signal_prefix}")
            print(f"  Entry Logic Module:    {message_channel.entry_logic_module}")
            print(f"  Management Module:     {message_channel.management_logic_module}")
            print(f"  Enabled:               {message_channel.enabled}")
            
            if not message_channel.enabled:
                print("\n⚠️  WARNING: This channel is DISABLED!")
                print("⚠️  The bot will NOT process messages from disabled channels!")
        else:
            print("\n❌ CHANNEL -1001859598768 NOT IN DATABASE!")
            print("❌ That's why the bot ignored the message!")
            print("\n💡 SOLUTION: Add this channel to the database or update the channel_id")
        
        if setonfx_channel and message_channel and setonfx_channel.channel_id != message_channel.channel_id:
            print("\n⚠️  CHANNEL ID MISMATCH!")
            print(f"⚠️  Setonfx is configured as: {setonfx_channel.channel_id}")
            print(f"⚠️  But message came from:    {message_channel.channel_id}")
            print(f"⚠️  These are DIFFERENT channels!")
        
        print("\n" + "="*80)
        print("ALL ENABLED CHANNELS:")
        print("="*80)
        for ch in channels:
            print(f"{ch.channel_id:20} {ch.display_name:30} [{ch.signal_prefix}]")
        print("="*80)
        print()
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
