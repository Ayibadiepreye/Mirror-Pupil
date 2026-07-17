"""
Mirror Pupil v5.1 - Channel Plugin Registry
Manages all registered channel plugins and routes messages to them.
"""

from typing import Dict, Optional
from loguru import logger

from .base import ChannelPlugin, DynamicChannelPlugin
from .billirichy.plugin import BillirichyPlugin
from .firepips.plugin import FirepipsPlugin


class ChannelRegistry:
    """
    Central registry for all channel plugins.
    Maps channel IDs to plugin instances.
    """
    
    def __init__(self):
        self._plugins: Dict[int, ChannelPlugin] = {}
        self._trade_executor = None  # Will be injected
        self._db = None  # Will be set during initialization
        self._initialized = False
    
    async def initialize(self, db):
        """
        Initialize registry by loading channels from database.
        Must be called before using the registry.
        
        Args:
            db: DatabaseManager instance
        """
        if self._initialized:
            logger.warning("ChannelRegistry already initialized")
            return
        
        self._db = db
        await self._load_channels_from_db()
        self._initialized = True
        logger.info(f"✓ ChannelRegistry initialized with {len(self._plugins)} plugin(s)")
    
    async def _load_channels_from_db(self):
        """
        Load enabled channels from database and create dynamic plugin instances.
        Supports mix-and-match of entry and management logic modules.
        """
        channels = await self._db.get_enabled_channels()
        
        VALID_ENTRY_MODULES = ["billirichy.entry", "firepips.entry"]
        VALID_MANAGEMENT_MODULES = ["billirichy.management", "firepips.management"]
        
        for channel in channels:
            # Validate entry module
            if channel.entry_logic_module not in VALID_ENTRY_MODULES:
                logger.warning(
                    f"⚠️ Skipping {channel.display_name} (ID: {channel.channel_id}): "
                    f"Unknown entry module '{channel.entry_logic_module}'. "
                    f"Valid options: {', '.join(VALID_ENTRY_MODULES)}"
                )
                continue
            
            # Validate management module
            if channel.management_logic_module not in VALID_MANAGEMENT_MODULES:
                logger.warning(
                    f"⚠️ Skipping {channel.display_name} (ID: {channel.channel_id}): "
                    f"Unknown management module '{channel.management_logic_module}'. "
                    f"Valid options: {', '.join(VALID_MANAGEMENT_MODULES)}"
                )
                continue
            
            try:
                # Create dynamic plugin with configured logic modules
                plugin = DynamicChannelPlugin(
                    channel_id=channel.channel_id,
                    display_name=channel.display_name,
                    entry_module=channel.entry_logic_module,
                    management_module=channel.management_logic_module,
                    signal_prefix=channel.signal_prefix
                )
                
                # Inject trade executor if available
                if self._trade_executor:
                    plugin._trade_executor = self._trade_executor
                
                # Inject database for smart matching
                plugin._db = self._db
                
                self._plugins[channel.channel_id] = plugin
                
                logger.info(
                    f"✓ Loaded plugin: {channel.display_name} (ID: {channel.channel_id}) "
                    f"[Entry: {channel.entry_logic_module}, Management: {channel.management_logic_module}]"
                )
                
            except Exception as e:
                logger.error(
                    f"✗ Failed to load plugin for {channel.display_name} (ID: {channel.channel_id}): {e}"
                )
    
    def inject_trade_executor(self, trade_executor):
        """
        Inject TradeExecutor into all plugins.
        Must be called after TradeExecutor is initialized.
        """
        self._trade_executor = trade_executor
        for plugin in self._plugins.values():
            plugin._trade_executor = trade_executor
        logger.info(f"✓ Injected TradeExecutor into {len(self._plugins)} plugin(s)")
    
    def inject_telegram_client(self, telegram_client):
        """
        Inject Telegram client into all plugins for reply chain traversal.
        Must be called after Telegram client is initialized.
        """
        for plugin in self._plugins.values():
            plugin._telegram_client = telegram_client
        logger.info(f"✓ Injected Telegram client into {len(self._plugins)} plugin(s)")
    
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
        # Inject trade executor if already available
        if self._trade_executor:
            plugin._trade_executor = self._trade_executor
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
