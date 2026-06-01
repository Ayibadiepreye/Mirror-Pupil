"""
Mirror Pupil v5.1 - Channel Plugin Registry
Manages all registered channel plugins and routes messages to them.
"""

from typing import Dict, Optional
from loguru import logger

from .base import ChannelPlugin
from .billirichy.plugin import BillirichyPlugin
from .firepips.plugin import FirepipsPlugin


class ChannelRegistry:
    """
    Central registry for all channel plugins.
    Maps channel IDs to plugin instances.
    """
    
    def __init__(self):
        self._plugins: Dict[int, ChannelPlugin] = {}
        self._load_builtin_channels()
    
    def _load_builtin_channels(self):
        """Load built-in channel plugins (BillirichyFX and Firepips)."""
        
        # BillirichyFX
        billirichy = BillirichyPlugin(
            channel_id=-1001859598768,
            display_name='BillirichyFX'
        )
        self._plugins[-1001859598768] = billirichy
        logger.info(f"✓ Loaded plugin: {billirichy.display_name} (ID: {billirichy.channel_id})")
        
        # Firepips
        firepips = FirepipsPlugin(
            channel_id=-1001182913499,
            display_name='Firepips'
        )
        self._plugins[-1001182913499] = firepips
        logger.info(f"✓ Loaded plugin: {firepips.display_name} (ID: {firepips.channel_id})")
    
    def get_plugin(self, channel_id: int) -> Optional[ChannelPlugin]:
        """
        Get plugin for a specific channel ID.
        
        Args:
            channel_id: Numeric Telegram channel ID
        
        Returns:
            ChannelPlugin instance or None if not registered
        """
        return self._plugins.get(channel_id)
    
    def get_all_plugins(self) -> Dict[int, ChannelPlugin]:
        """Get all registered plugins."""
        return self._plugins.copy()
    
    def get_channel_ids(self) -> list[int]:
        """Get list of all registered channel IDs."""
        return list(self._plugins.keys())
    
    def register_plugin(self, plugin: ChannelPlugin):
        """
        Register a new channel plugin.
        
        Args:
            plugin: ChannelPlugin instance
        """
        self._plugins[plugin.channel_id] = plugin
        logger.info(f"✓ Registered plugin: {plugin.display_name} (ID: {plugin.channel_id})")
    
    def unregister_plugin(self, channel_id: int):
        """
        Unregister a channel plugin.
        
        Args:
            channel_id: Channel ID to unregister
        """
        if channel_id in self._plugins:
            plugin = self._plugins[channel_id]
            del self._plugins[channel_id]
            logger.info(f"✓ Unregistered plugin: {plugin.display_name} (ID: {channel_id})")
    
    async def route_message(self, channel_id: int, message, is_edit: bool = False):
        """
        Route a message to the appropriate channel plugin.
        
        Args:
            channel_id: Channel ID the message came from
            message: Telegram message object
            is_edit: Whether this is an edited message
        """
        plugin = self.get_plugin(channel_id)
        
        if not plugin:
            logger.warning(f"No plugin registered for channel {channel_id}")
            return
        
        await plugin.route_message(message, is_edit)
    
    def cleanup_waiting_rooms(self):
        """Clean up expired waiting room entries in all plugins."""
        for plugin in self._plugins.values():
            plugin.cleanup_expired_waiting_room()


# Global registry instance
_registry = None


def get_registry() -> ChannelRegistry:
    """Get the global channel registry instance."""
    global _registry
    if _registry is None:
        _registry = ChannelRegistry()
    return _registry
