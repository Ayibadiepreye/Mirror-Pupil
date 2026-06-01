"""
BillirichyFX - Complete Channel Plugin
Implements the ChannelPlugin interface for BillirichyFX signals.
"""

from typing import Optional
from ..base import ChannelPlugin, ParsedSignal, ParsedManagement
from .symbol_map import normalize_symbol as norm_symbol
from .entry import parse_entry_signal
from .management import parse_management_action


class BillirichyPlugin(ChannelPlugin):
    """
    BillirichyFX channel plugin.
    
    Channel ID: -1001859598768
    Signal Prefix: B
    Priority: 1 (highest)
    """
    
    @property
    def signal_prefix(self) -> str:
        return 'B'
    
    def normalize_symbol(self, raw: str) -> Optional[str]:
        """Normalize symbol using BillirichyFX symbol map."""
        return norm_symbol(raw)
    
    async def parse_entry(self, message, raw_text: str) -> Optional[ParsedSignal]:
        """Parse entry signal from BillirichyFX message."""
        return await parse_entry_signal(
            message,
            raw_text,
            self.channel_id,
            self._add_to_waiting_room
        )
    
    async def parse_management(self, message, raw_text: str) -> Optional[ParsedManagement]:
        """Parse management action from BillirichyFX message."""
        return await parse_management_action(
            message,
            raw_text,
            self.channel_id
        )


# Export the plugin class as 'Plugin' for dynamic loading
Plugin = BillirichyPlugin
