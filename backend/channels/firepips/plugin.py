"""
Firepips - Complete Channel Plugin
Implements the ChannelPlugin interface for Firepips signals.
"""

from typing import Optional
from ..base import ChannelPlugin, ParsedSignal, ParsedManagement
from .symbol_map import normalize_symbol as norm_symbol
from .entry import parse_entry_signal
from .management import parse_management_action
from .context_matcher import FirepipsContextMatcher


class FirepipsPlugin(ChannelPlugin):
    """
    Firepips channel plugin.
    
    Channel ID: -1001182913499
    Signal Prefix: F
    Priority: 2
    """
    
    def __init__(self, channel_id: int, display_name: str):
        super().__init__(channel_id, display_name)
        self._context_matcher = None  # Will be initialized when db is available
    
    @property
    def signal_prefix(self) -> str:
        return 'F'
    
    def normalize_symbol(self, raw: str) -> Optional[str]:
        """Normalize symbol using Firepips symbol map."""
        return norm_symbol(raw)
    
    async def parse_entry(self, message, raw_text: str) -> Optional[ParsedSignal]:
        """Parse entry signal from Firepips message."""
        return await parse_entry_signal(
            message,
            raw_text,
            self.channel_id,
            self._add_to_waiting_room
        )
    
    async def parse_management(self, message, raw_text: str) -> Optional[ParsedManagement]:
        """Parse management action from Firepips message."""
        return await parse_management_action(
            message,
            raw_text,
            self.channel_id
        )
    
    async def _validate_bare_signal_completion(self, bare_signal, new_signal, message):
        """
        Validate bare signal completion using context matcher.
        This method is called by base class during waiting room completion.
        """
        # For now, use the context matcher's validation without db/client
        # In production, this would get client from the trade executor
        from .context_matcher import FirepipsContextMatcher
        
        # Create a temporary matcher (no db needed for validation)
        matcher = FirepipsContextMatcher(db=None, channel_id=self.channel_id)
        
        # Validate using context-aware price checking
        # Note: client=None means it will fall back to basic validation
        # When integrated with trade executor, client will be passed
        return await matcher.validate_bare_signal_completion(
            bare_signal, new_signal, client=None
        )


# Export the plugin class as 'Plugin' for dynamic loading
Plugin = FirepipsPlugin
