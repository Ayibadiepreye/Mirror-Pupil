"""
Quick script to fetch the latest Telegram auth code from Telegram.
Uses existing session to read messages.
"""
import asyncio
import os
from dotenv import load_dotenv
from pytdbot import Client
from loguru import logger

load_dotenv()

async def get_auth_code():
    """Fetch latest auth code from Telegram service messages."""
    
    client = Client(
        api_id=int(os.getenv("TELEGRAM_API_ID")),
        api_hash=os.getenv("TELEGRAM_API_HASH"),
        database_encryption_key=os.getenv("TDLIB_ENCRYPTION_KEY"),
        files_directory=os.getenv("TDLIB_FILES_DIR", "./tdlib_data")
    )
    
    logger.info("Starting Telegram client...")
    await client.start()
    
    try:
        # Get "Telegram" service chat (chat_id = 777000)
        telegram_service_id = 777000
        
        logger.info("Fetching recent messages from Telegram service...")
        
        # Get chat history from Telegram service
        result = await client.getChatHistory(
            chat_id=telegram_service_id,
            limit=10,
            from_message_id=0
        )
        
        if not result or not hasattr(result, 'messages'):
            logger.error("Could not fetch messages")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info("RECENT MESSAGES FROM TELEGRAM:")
        logger.info(f"{'='*60}\n")
        
        # Display recent messages
        for msg in result.messages:
            if hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                text = msg.content.text.text if hasattr(msg.content.text, 'text') else str(msg.content.text)
                
                # Check if it's a login code
                if "Login code" in text or "code:" in text:
                    logger.info(f"🔑 AUTH CODE MESSAGE:\n{text}\n")
                else:
                    logger.info(f"📨 {text[:100]}...\n" if len(text) > 100 else f"📨 {text}\n")
        
        logger.info(f"{'='*60}")
        logger.info("Look for messages starting with 'Login code' above")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.stop()
        logger.info("Client stopped")


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>\n",
        level="INFO"
    )
    
    asyncio.run(get_auth_code())
