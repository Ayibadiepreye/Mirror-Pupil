"""
Mirror Pupil v5.1 - Bot State Manager
Manages global bot running state (started/stopped).
"""

import asyncio
from loguru import logger


class BotState:
    """
    Singleton class to manage bot running state.
    
    When bot is stopped:
    - No new trades will be opened
    - Existing trades continue to be managed
    - Background tasks continue running
    """
    
    def __init__(self):
        self._running = True  # Bot starts in running state
        self._lock = asyncio.Lock()
    
    async def start(self) -> bool:
        """
        Start the bot (allow opening new trades).
        
        Returns:
            True if state changed, False if already running
        """
        async with self._lock:
            if self._running:
                logger.info("Bot already running")
                return False
            self._running = True
            logger.warning("🟢 BOT STARTED - New trades enabled")
            return True
    
    async def stop(self) -> bool:
        """
        Stop the bot (prevent opening new trades).
        
        Returns:
            True if state changed, False if already stopped
        """
        async with self._lock:
            if not self._running:
                logger.info("Bot already stopped")
                return False
            self._running = False
            logger.warning("🔴 BOT STOPPED - No new trades will be opened")
            return True
    
    def is_running(self) -> bool:
        """Check if bot is running."""
        return self._running
    
    def get_status(self) -> str:
        """Get current status as string."""
        return "running" if self._running else "stopped"


# Singleton instance
_bot_state: BotState | None = None


def get_bot_state() -> BotState:
    """Get singleton bot state instance."""
    global _bot_state
    if _bot_state is None:
        _bot_state = BotState()
    return _bot_state
