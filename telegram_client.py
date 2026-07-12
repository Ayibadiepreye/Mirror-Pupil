# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - Telegram Client (Pytdbot/TDLib)
Complete implementation with human-like behavior and anti-ban measures.
"""

import asyncio
import random
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime

# Patch pytdbot FIRST (before any other imports!) to handle unknown TDLib update types
import pytdbot.utils.obj_encoder as obj_encoder
import pytdbot.utils as pytdbot_utils
import pytdbot.client as pytdbot_client
from json import dumps

from loguru import logger
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import registry
from backend.channels.registry import get_registry

# Apply comprehensive monkey patches for unknown update types
original_dict_to_obj_obj_encoder = obj_encoder.dict_to_obj
original_dict_to_obj_utils = pytdbot_utils.dict_to_obj

def patched_dict_to_obj(dict_obj, client=None):
    try:
        return original_dict_to_obj_obj_encoder(dict_obj, client)
    except (AttributeError, KeyError) as e:
        # Ignore unknown update types (like UpdateTextCompositionStyles)
        logger.debug(f"[Telegram] Ignoring unknown update type: {dict_obj.get('@type', 'unknown')} error: {e}")
        return None

# Patch all places dict_to_obj could be referenced from
obj_encoder.dict_to_obj = patched_dict_to_obj
pytdbot_utils.dict_to_obj = patched_dict_to_obj
pytdbot_client.dict_to_obj = patched_dict_to_obj

# Also patch process_update to handle dict_to_obj returning None
original_process_update = pytdbot_client.Client.process_update

async def patched_process_update(self, update):
    if not update:
        self.logger.warning("Received None update")
        return
    
    if (self.logger.root.level >= pytdbot_client.DEBUG or self.logger.level >= pytdbot_client.DEBUG):
        self.logger.debug(f"Received: {dumps(update, indent=4)}")
    
    if "@extra" in update:
        if result := self._results.pop(update["@extra"]["id"], None):
            obj = patched_dict_to_obj(update, self)
            result.set_result(obj)
        elif update["@type"] == "error" and "option" in update["@extra"]:
            self.logger.error(f"{update['@extra']['option']}: {update['message']}")
    else:
        update_handler = self._Client__local_handlers.get(update["@type"])
        update_obj = patched_dict_to_obj(update, self)
        
        if update_obj is None:
            logger.debug(f"[Telegram] Skipping unknown update type: {update.get('@type')}")
            return
        
        if update_handler:
            self.loop.create_task(update_handler(update_obj))
        
        if not self.is_rabbitmq and self._Client__is_queue_worker:
            self.queue.put_nowait(update_obj)
        else:
            await self._handle_update(update_obj)

pytdbot_client.Client.process_update = patched_process_update

# Now do the normal imports
from pytdbot import Client
from pytdbot.types import Update, LogStreamFile


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
        self.is_authorized = False
        self._auth_event = asyncio.Event()
        self.reconnect_count = 0
        self._reconnecting = False  # Guard against overlapping reconnect loops
        self._health_check_task: Optional[asyncio.Task] = None  # Track health check task
        self.message_handlers: Dict[int, Callable] = {}  # channel_id -> handler
        self.last_activity = time.time()
        
        # Ensure files directory exists
        self.files_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized HumanLikeTelegramClient with files_dir={files_dir}")
    
    def _apply_pytdbot_patches(self):
        """
        Apply monkey patches to Pytdbot to handle unknown update types gracefully.
        Prevents crashes from unexpected Telegram updates.
        Note: Main patches are already applied at module level before imports.
        """
        logger.info("✓ Pytdbot patches applied at module level")
    
    async def set_authentication_code(self, code: str) -> bool:
        """Submit the authentication code received via SMS/Telegram."""
        if not self.client:
            logger.error("[Telegram] Client not initialized")
            return False
        
        try:
            logger.info(f"[Telegram] Submitting authentication code...")
            result = await self.client.checkAuthenticationCode(code=code)
            
            # Wait a moment for auth state to update
            await asyncio.sleep(1)
            
            # Check if we're still waiting for code (means it was wrong)
            if hasattr(self, '_auth_state') and self._auth_state == "authorizationStateWaitCode":
                logger.error("[Telegram] ❌ Invalid code! Try again.")
                return False
            
            logger.info("[Telegram] ✓ Code accepted!")
            return True
        except Exception as e:
            logger.error(f"[Telegram] ❌ Failed to submit code: {e}")
            return False
    
    async def set_authentication_password(self, password: str) -> bool:
        """Submit the 2FA password."""
        if not self.client:
            logger.error("[Telegram] Client not initialized")
            return False
        
        try:
            logger.info(f"[Telegram] Submitting 2FA password")
            await self.client.checkAuthenticationPassword(password=password)
            return True
        except Exception as e:
            logger.error(f"[Telegram] Failed to set authentication password: {e}")
            return False
    
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
                action={"@type": "chatActionTyping"}
            )
            logger.debug(f"Sent typing indicator to chat {chat_id}")
        except Exception as e:
            logger.warning(f"Failed to send typing indicator: {e}")
    
    async def get_message(self, chat_id: int, message_id: int):
        """
        Fetch a specific message by ID from a chat.
        Used for reply chain traversal to find context.
        
        Args:
            chat_id: The chat/channel ID
            message_id: The message ID to fetch
        
        Returns:
            Message object or None if not found
        """
        if not self.client:
            logger.warning("Cannot get message: client not initialized")
            return None
        
        try:
            result = await self.client.getMessage(
                chat_id=chat_id,
                message_id=message_id
            )
            return result
        except Exception as e:
            logger.debug(f"Could not fetch message {message_id} from chat {chat_id}: {e}")
            return None
    
    async def _health_check_loop(self):
        """
        Periodic health check to verify connection is alive.
        Calls getMe() every 30 seconds with timeout.
        """
        while self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self.client and self.is_running:
                    try:
                        # Add 5 second timeout to prevent hanging
                        me = await asyncio.wait_for(self.client.getMe(), timeout=5.0)
                        if me:
                            logger.debug(f"Health check OK - Connected as {me.first_name}")
                            self.last_activity = time.time()
                        else:
                            logger.warning("Health check failed - getMe() returned None")
                            if not self._reconnecting:
                                asyncio.create_task(self._reconnect_loop())
                    except asyncio.TimeoutError:
                        logger.warning("Health check timeout - connection may be stalled")
                        if not self._reconnecting:
                            asyncio.create_task(self._reconnect_loop())
                    except Exception as e:
                        logger.error(f"Health check error: {e}")
                        if not self._reconnecting:
                            asyncio.create_task(self._reconnect_loop())
                        
            except asyncio.CancelledError:
                logger.debug("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in health check loop: {e}")
    
    async def _reconnect_loop(self):
        """
        Auto-reconnect with exponential backoff.
        Attempts up to max_reconnect_attempts times.
        Protected against overlapping executions.
        """
        # Guard against overlapping reconnect loops
        if self._reconnecting:
            logger.debug("Reconnect already in progress, skipping")
            return
        
        self._reconnecting = True
        
        try:
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
        finally:
            self._reconnecting = False
    
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
                td_log=LogStreamFile(str(self.files_dir / "tdlib.log")),
                user_bot=True  # Important: we're a user account, not a bot
            )
            
            # Register authorization state handler BEFORE starting
            @self.client.on_updateAuthorizationState()
            async def on_authorization_state(c: Client, update: Update):
                auth_state = update.authorization_state.getType()
                logger.info(f"[Telegram] Authorization state: {auth_state}")
                
                if auth_state == "authorizationStateWaitPhoneNumber":
                    logger.info(f"[Telegram] Setting phone number: {self.phone}")
                    await c.setAuthenticationPhoneNumber(phone_number=self.phone)
                
                elif auth_state == "authorizationStateWaitCode":
                    logger.warning("[Telegram] Waiting for authentication code! Please check your Telegram/SMS.")
                    logger.warning("[Telegram] You can enter the code in the terminal, or use the /api/telegram/auth-code endpoint!")
                    
                    async def get_code_from_terminal():
                        from concurrent.futures import ThreadPoolExecutor
                        loop = asyncio.get_event_loop()
                        executor = ThreadPoolExecutor(max_workers=1)
                        try:
                            code = await loop.run_in_executor(executor, lambda: input("Enter authentication code: "))
                            if code:
                                await self.set_authentication_code(code.strip())
                        except Exception as e:
                            logger.error(f"[Telegram] Failed to get code from terminal: {e}")
                    
                    asyncio.create_task(get_code_from_terminal())
                
                elif auth_state == "authorizationStateWaitPassword":
                    logger.warning("[Telegram] Waiting for 2FA password!")
                    logger.warning("[Telegram] You can enter the password in the terminal, or use the /api/telegram/auth-password endpoint!")
                    
                    async def get_password_from_terminal():
                        from concurrent.futures import ThreadPoolExecutor
                        loop = asyncio.get_event_loop()
                        executor = ThreadPoolExecutor(max_workers=1)
                        try:
                            password = await loop.run_in_executor(executor, lambda: input("Enter 2FA password: "))
                            if password:
                                await self.set_authentication_password(password.strip())
                        except Exception as e:
                            logger.error(f"[Telegram] Failed to get password from terminal: {e}")
                    
                    asyncio.create_task(get_password_from_terminal())
                
                elif auth_state == "authorizationStateReady":
                    logger.info("[Telegram] Authorization successful!")
                    self.is_authorized = True
                    self._auth_event.set()
            
            logger.info("Starting Telegram client...")
            
            # Start the client
            await self.client.start()
            
            # Wait for authorization
            logger.info("[Telegram] Waiting for authorization...")
            await self._auth_event.wait()
            
            me = await self.client.getMe()
            if me:
                logger.info(f"✓ Connected as: {me.first_name} {me.last_name or ''} (@{getattr(me, 'username', 'no_username')})")
                logger.info(f"  Phone: {getattr(me, 'phone_number', 'N/A')}")
                logger.info(f"  User ID: {getattr(me, 'id', 'N/A')}")
                self.is_running = True
                self.last_activity = time.time()
                self.reconnect_count = 0
                
                # Start health check loop and store reference
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                
                return True
            else:
                logger.error("Failed to get user info after starting client")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Telegram client: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
                    
                    # Mark as read first (human-like)
                    await self._mark_as_read(chat_id, [message.id])
                    
                    # Show typing indicator (human-like)
                    await self._typing_indicator(chat_id)
                    
                    # Call the registered handler
                    handler = self.message_handlers[chat_id]
                    await handler(message, is_edit=False)
                    
                    self.last_activity = time.time()
            
            # Handle edited messages
            elif hasattr(update, 'message_edited') and update.message_edited:
                message = update.message_edited
                chat_id = message.chat_id
                
                if chat_id in self.message_handlers:
                    logger.info(f"✏️ Edited message in channel {chat_id}: ID={message.id}")
                    
                    # Mark as read
                    await self._mark_as_read(chat_id, [message.id])
                    
                    # Show typing indicator
                    await self._typing_indicator(chat_id)
                    
                    # Call the registered handler with is_edit=True
                    handler = self.message_handlers[chat_id]
                    await handler(message, is_edit=True)
                    
                    self.last_activity = time.time()
            
        except Exception as e:
            logger.error(f"Error handling update: {e}", exc_info=True)
    
    async def listen(self):
        """
        Start listening for updates from registered channels.
        This runs until stopped, allowing proper lifecycle control.
        """
        if not self.client or not self.is_running:
            logger.error("Client not started. Call start() first.")
            return
        
        logger.info(f"👂 Listening to {len(self.message_handlers)} channel(s)...")
        
        try:
            # Register update handlers using decorators (like the old bot)
            @self.client.on_updateNewMessage()
            async def on_new_message(c: Client, update: Update):
                await self._handle_update(update)
            
            @self.client.on_updateMessageEdited()
            async def on_message_edited(c: Client, update: Update):
                await self._handle_update(update)
            
            @self.client.on_updateConnectionState()
            async def on_connection_state(c: Client, update: Update):
                """Handle connection state changes."""
                try:
                    state = update.state.getType() if hasattr(update.state, 'getType') else str(update.state)
                    logger.info(f"Connection state: {state}")
                    
                    if state == "connectionStateReady":
                        logger.info("✓ Connection ready")
                        self.reconnect_count = 0
                    elif state in ["connectionStateClosed", "connectionStateFailed"]:
                        logger.warning(f"Connection lost: {state}")
                        if self.is_running and not self._reconnecting:
                            asyncio.create_task(self._reconnect_loop())
                except Exception as e:
                    logger.error(f"Error handling connection state: {e}")
            
            # Keep the client running without blocking control flow
            # Don't use idle() - use custom loop for better control
            logger.info("✓ Client listening (pytdbot handles updates in background)")
            
            while self.is_running:
                await asyncio.sleep(1)  # Keep event loop alive
                # pytdbot decorators handle updates in background
            
        except asyncio.CancelledError:
            logger.info("Listen loop cancelled")
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
            if self.is_running and not self._reconnecting:
                asyncio.create_task(self._reconnect_loop())
    
    async def stop(self):
        """Stop the client gracefully with proper task cleanup."""
        logger.info("Stopping Telegram client...")
        self.is_running = False
        
        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            logger.debug("Cancelling health check task...")
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                logger.debug("Health check task cancelled")
            except Exception as e:
                logger.warning(f"Error cancelling health check task: {e}")
        
        # Stop the client
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
