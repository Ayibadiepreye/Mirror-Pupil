# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - Telegram Client (Pytdbot/TDLib)
Complete implementation with human-like behavior and anti-ban measures.
"""

import asyncio
import random
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from pytdbot import Client
from pytdbot.types import Update, LogStreamFile
from loguru import logger
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class HumanLikeTelegramClient:
    """
    Pytdbot-based Telegram client with human-like behavior to avoid bans.
    
    Features:
    - Random delays between actions (0.5-2.0s)
    - Mark messages as read
    - Typing indicators
    - Health check loop
    - Auto-reconnect with exponential backoff
    - Monkey patches for unknown update types
    """
    
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        encryption_key: str,
        files_dir: str = "./tdlib_data",
        min_delay: float = 0.5,
        max_delay: float = 2.0,
        mark_as_read: bool = True,
        show_typing: bool = True,
        health_check_interval: int = 30,
        max_reconnect_attempts: int = 10,
        reconnect_base_delay: int = 5
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.encryption_key = encryption_key
        self.files_dir = Path(files_dir)
        
        # Human-like behavior settings
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.mark_as_read_enabled = mark_as_read
        self.show_typing_enabled = show_typing
        self.health_check_interval = health_check_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_base_delay = reconnect_base_delay
        
        # State
        self.client: Optional[Client] = None
        self.is_running = False
        self.reconnect_count = 0
        self.message_handlers: Dict[int, Callable] = {}  # channel_id -> handler
        self.last_activity = time.time()
        
        # Ensure files directory exists
        self.files_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized HumanLikeTelegramClient with files_dir={files_dir}")
    
    def _apply_pytdbot_patches(self):
        """
        Apply monkey patches to Pytdbot to handle unknown update types gracefully.
        Prevents crashes from unexpected Telegram updates.
        """
        try:
            # Patch 1: dict_to_obj in obj_encoder
            from pytdbot.types import obj_encoder
            original_dict_to_obj = obj_encoder.dict_to_obj
            
            def patched_dict_to_obj(data: dict):
                try:
                    return original_dict_to_obj(data)
                except Exception as e:
                    logger.warning(f"Unknown update type in obj_encoder: {data.get('@type')} - {e}")
                    return None
            
            obj_encoder.dict_to_obj = patched_dict_to_obj
            
            # Patch 2: dict_to_obj in pytdbot_utils
            from pytdbot import utils as pytdbot_utils
            if hasattr(pytdbot_utils, 'dict_to_obj'):
                original_utils_dict_to_obj = pytdbot_utils.dict_to_obj
                
                def patched_utils_dict_to_obj(data: dict):
                    try:
                        return original_utils_dict_to_obj(data)
                    except Exception as e:
                        logger.warning(f"Unknown update type in pytdbot_utils: {data.get('@type')} - {e}")
                        return None
                
                pytdbot_utils.dict_to_obj = patched_utils_dict_to_obj
            
            # Patch 3: Client.process_update to skip None updates
            from pytdbot import Client as PytdbotClient
            original_process_update = PytdbotClient.process_update
            
            async def patched_process_update(self, update):
                if update is None:
                    logger.debug("Skipping None update")
                    return
                return await original_process_update(self, update)
            
            PytdbotClient.process_update = patched_process_update
            
            logger.info("✓ Applied Pytdbot monkey patches successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply Pytdbot patches: {e}")
    
    async def _human_delay(self):
        """Add random human-like delay between actions."""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
    
    async def _mark_as_read(self, chat_id: int, message_ids: list[int]):
        """Mark messages as read with human-like delay."""
        if not self.mark_as_read_enabled or not self.client:
            return
        
        try:
            await self._human_delay()
            await self.client.viewMessages(
                chat_id=chat_id,
                message_ids=message_ids,
                force_read=True
            )
            logger.debug(f"Marked {len(message_ids)} message(s) as read in chat {chat_id}")
        except Exception as e:
            logger.warning(f"Failed to mark messages as read: {e}")
    
    async def _typing_indicator(self, chat_id: int):
        """Show typing indicator with human-like delay."""
        if not self.show_typing_enabled or not self.client:
            return
        
        try:
            await self._human_delay()
            await self.client.sendChatAction(
                chat_id=chat_id,
                action="chatActionTyping"
            )
            logger.debug(f"Sent typing indicator to chat {chat_id}")
        except Exception as e:
            logger.warning(f"Failed to send typing indicator: {e}")
    
    async def _health_check_loop(self):
        """
        Periodic health check to verify connection is alive.
        Calls getMe() every 30 seconds.
        """
        while self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self.client:
                    me = await self.client.getMe()
                    if me:
                        logger.debug(f"Health check OK - Connected as {me.first_name}")
                        self.last_activity = time.time()
                    else:
                        logger.warning("Health check failed - getMe() returned None")
                        
            except Exception as e:
                logger.error(f"Health check error: {e}")
                # Don't break the loop - let reconnect logic handle it
    
    async def _reconnect_loop(self):
        """
        Auto-reconnect with exponential backoff.
        Attempts up to max_reconnect_attempts times.
        """
        while self.is_running and self.reconnect_count < self.max_reconnect_attempts:
            try:
                # Wait before reconnecting
                delay = min(
                    self.reconnect_base_delay * (2 ** self.reconnect_count),
                    60  # Max 60 seconds
                )
                logger.info(f"Reconnecting in {delay}s (attempt {self.reconnect_count + 1}/{self.max_reconnect_attempts})")
                await asyncio.sleep(delay)
                
                # Try to reconnect
                await self.start()
                
                if self.client and self.client.is_connected:
                    logger.info("✓ Reconnected successfully")
                    self.reconnect_count = 0  # Reset counter on success
                    return
                else:
                    self.reconnect_count += 1
                    
            except Exception as e:
                logger.error(f"Reconnect attempt failed: {e}")
                self.reconnect_count += 1
        
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.critical(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached. Giving up.")
            self.is_running = False
    
    async def start(self):
        """Initialize and start the Telegram client."""
        try:
            # Apply patches before creating client
            self._apply_pytdbot_patches()
            
            # Create Pytdbot client
            self.client = Client(
                api_id=self.api_id,
                api_hash=self.api_hash,
                database_encryption_key=self.encryption_key,
                files_directory=str(self.files_dir),
                td_verbosity=2,  # TDLib log level
                td_log=LogStreamFile(str(self.files_dir / "tdlib.log"))
            )
            
            logger.info("Starting Telegram client...")
            
            # Start the client
            await self.client.start()
            
            # Wait for authorization
            me = await self.client.getMe()
            if me:
                logger.info(f"✓ Connected as: {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
                logger.info(f"  Phone: {me.phone_number}")
                logger.info(f"  User ID: {me.id}")
                self.is_running = True
                self.last_activity = time.time()
                
                # Start health check loop
                asyncio.create_task(self._health_check_loop())
                
                return True
            else:
                logger.error("Failed to get user info after starting client")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Telegram client: {e}")
            # Trigger reconnect
            if self.is_running:
                asyncio.create_task(self._reconnect_loop())
            return False
    
    def register_channel_handler(self, channel_id: int, handler: Callable):
        """
        Register a message handler for a specific channel.
        
        Args:
            channel_id: Numeric Telegram channel ID (e.g., -1001859598768)
            handler: Async function that takes (message, is_edit) as arguments
        """
        self.message_handlers[channel_id] = handler
        logger.info(f"Registered handler for channel {channel_id}")
    
    async def _handle_update(self, update: Update):
        """
        Internal update handler that routes messages to registered channel handlers.
        Implements human-like behavior (mark as read, typing indicator).
        """
        try:
            # Handle new messages
            if hasattr(update, 'message') and update.message:
                message = update.message
                chat_id = message.chat_id
                
                # Check if we have a handler for this channel
                if chat_id in self.message_handlers:
                    logger.info(f"📨 New message in channel {chat_id}: ID={message.id}")
                    
                    # Show typing indicator (human-like)
                    await self._typing_indicator(chat_id)
                    
                    # Call the registered handler
                    handler = self.message_handlers[chat_id]
                    await handler(message, is_edit=False)
                    
                    # Mark as read (human-like)
                    await self._mark_as_read(chat_id, [message.id])
                    
                    self.last_activity = time.time()
            
            # Handle edited messages
            elif hasattr(update, 'message_edited') and update.message_edited:
                message = update.message_edited
                chat_id = message.chat_id
                
                if chat_id in self.message_handlers:
                    logger.info(f"✏️ Edited message in channel {chat_id}: ID={message.id}")
                    
                    # Show typing indicator
                    await self._typing_indicator(chat_id)
                    
                    # Call the registered handler with is_edit=True
                    handler = self.message_handlers[chat_id]
                    await handler(message, is_edit=True)
                    
                    # Mark as read
                    await self._mark_as_read(chat_id, [message.id])
                    
                    self.last_activity = time.time()
            
            # Handle connection state changes
            elif hasattr(update, 'connection_state'):
                state = update.connection_state
                logger.info(f"Connection state: {state}")
                
                if state == "connectionStateReady":
                    logger.info("✓ Connection ready")
                    self.reconnect_count = 0
                elif state in ["connectionStateClosed", "connectionStateFailed"]:
                    logger.warning(f"Connection lost: {state}")
                    if self.is_running:
                        asyncio.create_task(self._reconnect_loop())
            
        except Exception as e:
            logger.error(f"Error handling update: {e}", exc_info=True)
    
    async def listen(self):
        """
        Start listening for updates from registered channels.
        This is a blocking call that runs until stopped.
        """
        if not self.client or not self.is_running:
            logger.error("Client not started. Call start() first.")
            return
        
        logger.info(f"👂 Listening to {len(self.message_handlers)} channel(s)...")
        
        try:
            # Register the update handler
            self.client.add_handler(self._handle_update)
            
            # Keep the client running
            await self.client.idle()
            
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
            if self.is_running:
                asyncio.create_task(self._reconnect_loop())
    
    async def stop(self):
        """Stop the client gracefully."""
        logger.info("Stopping Telegram client...")
        self.is_running = False
        
        if self.client:
            try:
                await self.client.stop()
                logger.info("✓ Client stopped")
            except Exception as e:
                logger.error(f"Error stopping client: {e}")


# ============================================
# Signal Parser Integration
# ============================================

# Import the channel registry
import sys
from pathlib import Path

# Add backend to path for channel registry
backend_path = Path(__file__).parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# This function would be used if telegram_client.py ran standalone
# But since it's imported by telegram_integration.py, we don't need this import here
# The registry will be accessed through telegram_integration.py instead

async def signal_parser_handler(channel_id: int):
    """
    Create a message handler that routes to the channel registry.
    
    Args:
        channel_id: The channel ID this handler is for
    
    Returns:
        Async handler function
    """
    registry = get_registry()
    
    async def handler(message, is_edit: bool):
        """Route message to the appropriate channel plugin."""
        await registry.route_message(channel_id, message, is_edit)
    
    return handler


async def main():
    """Main entry point for testing the Telegram client with signal parsers."""
    
    # Load config from environment
    api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    phone = os.getenv("TELEGRAM_PHONE", "")
    encryption_key = os.getenv("TDLIB_ENCRYPTION_KEY", "")
    files_dir = os.getenv("TDLIB_FILES_DIR", "./tdlib_data")
    
    if not all([api_id, api_hash, phone, encryption_key]):
        logger.error("Missing required environment variables!")
        logger.error("Please set: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TDLIB_ENCRYPTION_KEY")
        return
    
    # Create client
    client = HumanLikeTelegramClient(
        api_id=api_id,
        api_hash=api_hash,
        phone=phone,
        encryption_key=encryption_key,
        files_dir=files_dir,
        min_delay=float(os.getenv("MIN_HUMAN_DELAY", "0.5")),
        max_delay=float(os.getenv("MAX_HUMAN_DELAY", "2.0")),
        mark_as_read=os.getenv("MARK_AS_READ", "true").lower() == "true",
        show_typing=os.getenv("SHOW_TYPING", "true").lower() == "true",
        health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
        max_reconnect_attempts=int(os.getenv("MAX_RECONNECT_ATTEMPTS", "10")),
        reconnect_base_delay=int(os.getenv("RECONNECT_BASE_DELAY", "5"))
    )
    
    # Initialize channel registry
    logger.info("Initializing channel registry...")
    registry = get_registry()
    
    # Register handlers for each channel
    for channel_id in registry.get_channel_ids():
        handler = await signal_parser_handler(channel_id)
        client.register_channel_handler(channel_id, handler)
    
    logger.info(f"✓ Registered {len(registry.get_channel_ids())} channel handler(s)")
    
    # Start cleanup task for waiting rooms
    async def cleanup_loop():
        while client.is_running:
            await asyncio.sleep(60)  # Every minute
            registry.cleanup_waiting_rooms()
    
    # Start the client
    started = await client.start()
    
    if not started:
        logger.error("Failed to start client")
        return
    
    # Start cleanup task
    asyncio.create_task(cleanup_loop())
    
    # Listen for messages (blocking)
    try:
        await client.listen()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await client.stop()


if __name__ == "__main__":
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # Run the client
    asyncio.run(main())
