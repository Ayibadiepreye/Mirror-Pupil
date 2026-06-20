# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - Telegram Client Integration
Integrates the Telegram client into the FastAPI backend.
"""

import asyncio
import os
from pathlib import Path
from loguru import logger
from typing import Optional

# Import the telegram client from root
import sys
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from telegram_client import HumanLikeTelegramClient
from backend.channels.registry import get_registry


class TelegramIntegration:
    """
    Manages the Telegram client lifecycle within the FastAPI application.
    """
    
    def __init__(self):
        self.client: Optional[HumanLikeTelegramClient] = None
        self.listen_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
    
    async def start(self, db):
        """
        Start the Telegram client and register channel handlers.
        
        Args:
            db: DatabaseManager instance for loading channels
        """
        try:
            # Load config from environment
            api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
            api_hash = os.getenv("TELEGRAM_API_HASH", "")
            phone = os.getenv("TELEGRAM_PHONE", "")
            encryption_key = os.getenv("TDLIB_ENCRYPTION_KEY", "")
            files_dir = os.getenv("TDLIB_FILES_DIR", "./tdlib_data")
            
            if not all([api_id, api_hash, phone, encryption_key]):
                logger.warning("Telegram credentials not configured - skipping Telegram client initialization")
                logger.warning("To enable: Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TDLIB_ENCRYPTION_KEY in .env")
                return False
            
            # Create client
            self.client = HumanLikeTelegramClient(
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
            
            logger.info("Starting Telegram client integration...")
            
            # Start the client
            started = await self.client.start()
            
            if not started:
                logger.error("Failed to start Telegram client")
                return False
            
            # Get channel registry
            registry = get_registry()
            
            # Initialize registry with database (loads channels dynamically)
            await registry.initialize(db)
            
            # Inject telegram client into plugins for reply chain traversal
            registry.inject_telegram_client(self.client)
            
            # Register handlers for each loaded channel
            for channel_id in registry.get_channel_ids():
                handler = self._create_handler(channel_id, registry)
                self.client.register_channel_handler(channel_id, handler)
            
            logger.info(f"✓ Registered {len(registry.get_channel_ids())} Telegram channel handler(s)")
            
            # Start cleanup task for waiting rooms
            self.cleanup_task = asyncio.create_task(self._cleanup_loop(registry))
            
            # Start listen task
            self.listen_task = asyncio.create_task(self.client.listen())
            
            self.is_running = True
            logger.info("✅ Telegram client integration started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Telegram integration: {e}")
            return False
    
    def _create_handler(self, channel_id: int, registry):
        """
        Create a message handler for a specific channel.
        
        Args:
            channel_id: The channel ID
            registry: The channel registry
        
        Returns:
            Async handler function
        """
        async def handler(message, is_edit: bool):
            """Route message to the appropriate channel plugin."""
            try:
                await registry.route_message(channel_id, message, is_edit)
            except Exception as e:
                logger.error(f"Error routing message from channel {channel_id}: {e}", exc_info=True)
        
        return handler
    
    async def _cleanup_loop(self, registry):
        """Periodic cleanup of waiting room entries."""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Every minute
                registry.cleanup_waiting_rooms()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def stop(self):
        """Stop the Telegram client gracefully."""
        if not self.client:
            return
        
        logger.info("Stopping Telegram client integration...")
        self.is_running = False
        
        # Cancel tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        # Stop client
        await self.client.stop()
        
        logger.info("✓ Telegram client integration stopped")


# Global instance
_telegram_integration: Optional[TelegramIntegration] = None


def get_telegram_integration() -> TelegramIntegration:
    """Get or create the global Telegram integration instance."""
    global _telegram_integration
    if _telegram_integration is None:
        _telegram_integration = TelegramIntegration()
    return _telegram_integration
