"""
Fetch a specific Telegram message and test parsing
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Import telegram client
from telegram_client import HumanLikeTelegramClient

# Import parsers
from backend.channels.billirichy.entry import parse_entry_signal
from backend.channels.billirichy.management import parse_management_action


async def fetch_and_parse():
    """Fetch message 4571791360 from channel -1001859598768 and test parsers"""
    
    # Initialize client
    api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    phone = os.getenv("TELEGRAM_PHONE", "")
    encryption_key = os.getenv("TDLIB_ENCRYPTION_KEY", "")
    files_dir = os.getenv("TDLIB_FILES_DIR", "./tdlib_data")
    
    client = HumanLikeTelegramClient(
        api_id=api_id,
        api_hash=api_hash,
        phone=phone,
        encryption_key=encryption_key,
        files_dir=files_dir
    )
    
    try:
        # Start client
        logger.info("Starting Telegram client...")
        await client.start()
        
        # Fetch the specific message
        channel_id = -1001859598768
        message_id = 4571791360
        
        logger.info(f"Fetching message {message_id} from channel {channel_id}...")
        message = await client.get_message(channel_id, message_id)
        
        if not message:
            logger.error("Could not fetch message!")
            return
        
        logger.info(f"✓ Message fetched: ID={message.id}")
        
        # Extract text
        text = ""
        if hasattr(message, 'content') and hasattr(message.content, 'text'):
            if hasattr(message.content.text, 'text'):
                text = message.content.text.text
            else:
                text = str(message.content.text)
        
        logger.info(f"Message content type: {type(message.content)}")
        logger.info(f"Message content: {message.content}")
        
        if text:
            logger.info(f"Raw text ({len(text)} chars):\n{text}")
            
            # Clean text (same as routing does)
            import re
            clean_text = text.lower()
            clean_text = re.sub(r'[^\w\s\.\,\:\;\-\@\#\$\%\(\)\/\+\=]', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            logger.info(f"Clean text ({len(clean_text)} chars):\n{clean_text}")
            
            # Test entry parser
            logger.info("\n" + "="*60)
            logger.info("TESTING ENTRY PARSER")
            logger.info("="*60)
            
            def dummy_waiting_room(bare_signal):
                logger.info(f"Bare signal callback: {bare_signal}")
            
            try:
                entry_result = await parse_entry_signal(
                    message,
                    clean_text,
                    channel_id,
                    dummy_waiting_room
                )
                
                if entry_result:
                    logger.info(f"✓ ENTRY PARSED: {entry_result}")
                else:
                    logger.info("✗ Entry parser returned None")
            except Exception as e:
                logger.error(f"Entry parser failed: {e}", exc_info=True)
            
            # Test management parser
            logger.info("\n" + "="*60)
            logger.info("TESTING MANAGEMENT PARSER")
            logger.info("="*60)
            
            try:
                mgmt_result = await parse_management_action(
                    message,
                    clean_text,
                    channel_id,
                    db=None
                )
                
                if mgmt_result:
                    logger.info(f"✓ MANAGEMENT PARSED: {mgmt_result}")
                else:
                    logger.info("✗ Management parser returned None")
            except Exception as e:
                logger.error(f"Management parser failed: {e}", exc_info=True)
            
        else:
            logger.warning("Message has no text content!")
            
            # Check if it's a photo/media message
            if hasattr(message.content, '@type'):
                content_type = message.content.__dict__.get('@type', 'unknown')
                logger.info(f"Message content @type: {content_type}")
                
                # Check for caption
                if hasattr(message.content, 'caption'):
                    caption = message.content.caption
                    if caption and hasattr(caption, 'text'):
                        caption_text = caption.text
                        logger.info(f"Message has caption: {caption_text}")
        
        # Show reply info
        if hasattr(message, 'reply_to_message_id') and message.reply_to_message_id:
            logger.info(f"Message is a reply to: {message.reply_to_message_id}")
        
    finally:
        # Stop client
        logger.info("Stopping client...")
        await client.stop()


if __name__ == "__main__":
    asyncio.run(fetch_and_parse())
