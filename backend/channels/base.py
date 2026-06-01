"""
Mirror Pupil v5.1 - Channel Plugin Base Classes
Abstract interfaces that all channel plugins must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class ParsedSignal:
    """
    Structured representation of a parsed entry signal.
    Returned by ChannelPlugin.parse_entry()
    """
    channel_id: int
    msg_id: int
    symbol: str
    direction: str          # 'BUY' or 'SELL'
    entry_price: Optional[float]
    sl: Optional[float]
    tp: Optional[List[float]]   # List supports multi-TP (e.g., [1960, 1980, 2000])
    order_type: str         # 'MARKET', 'LIMIT', 'STOP'
    is_reentry: bool
    raw_text: str
    timestamp: datetime
    
    def __str__(self):
        tp_str = f"{self.tp}" if self.tp else "None"
        return (
            f"ParsedSignal({self.symbol} {self.direction} @ {self.entry_price or 'MARKET'} "
            f"SL={self.sl} TP={tp_str} Type={self.order_type} ReEntry={self.is_reentry})"
        )


@dataclass
class ParsedManagement:
    """
    Structured representation of a parsed management action.
    Returned by ChannelPlugin.parse_management()
    """
    channel_id: int
    msg_id: int
    reply_to_msg_id: Optional[int]
    action: str             # 'BREAKEVEN', 'CLOSE_ALL', 'MODIFY_SL', 'PARTIAL_CLOSE_50', etc.
    symbol: Optional[str]   # For symbol-specific actions
    direction: Optional[str]  # For direction-specific actions
    new_sl: Optional[float]
    new_tp: Optional[float]
    close_pct: Optional[float]  # For partial closes (0.5 = 50%, 0.75 = 75%)
    raw_text: str
    timestamp: datetime
    
    def __str__(self):
        details = []
        if self.symbol:
            details.append(f"Symbol={self.symbol}")
        if self.direction:
            details.append(f"Dir={self.direction}")
        if self.new_sl:
            details.append(f"NewSL={self.new_sl}")
        if self.new_tp:
            details.append(f"NewTP={self.new_tp}")
        if self.close_pct:
            details.append(f"Close={self.close_pct*100:.0f}%")
        
        details_str = " ".join(details) if details else ""
        return f"ParsedManagement({self.action} {details_str})".strip()


@dataclass
class BareSignal:
    """
    Incomplete signal waiting for SL (waiting room).
    """
    channel_id: int
    msg_id: int
    symbol: str
    direction: str
    entry_price: Optional[float]
    order_type: str
    raw_text: str
    timestamp: datetime
    expires_at: datetime


class ChannelPlugin(ABC):
    """
    Abstract base class for all channel plugins.
    Every signal channel must implement this interface.
    
    A plugin is responsible for:
    1. Normalizing symbols (e.g., "gold" -> "XAUUSD")
    2. Parsing entry signals from messages
    3. Parsing management actions from messages
    4. Routing messages to the appropriate handler
    """
    
    def __init__(self, channel_id: int, display_name: str):
        self.channel_id = channel_id
        self.display_name = display_name
        self._waiting_room: dict = {}  # {(symbol, direction): BareSignal}
    
    @property
    @abstractmethod
    def signal_prefix(self) -> str:
        """
        Short code used in signal IDs (e.g., 'B' for BillirichyFX, 'F' for Firepips).
        Must be 2-4 characters, unique across all channels.
        """
        ...
    
    @abstractmethod
    def normalize_symbol(self, raw: str) -> Optional[str]:
        """
        Normalize a raw symbol string to standard format.
        
        Args:
            raw: Raw symbol from message (e.g., "gold", "xau", "XAUUSD")
        
        Returns:
            Normalized symbol (e.g., "XAUUSD") or None if excluded/invalid
        
        Examples:
            normalize_symbol("gold") -> "XAUUSD"
            normalize_symbol("btc") -> None (excluded)
        """
        ...
    
    @abstractmethod
    async def parse_entry(self, message, raw_text: str) -> Optional[ParsedSignal]:
        """
        Parse a message as a potential entry signal.
        
        Args:
            message: Telegram message object
            raw_text: Cleaned message text
        
        Returns:
            ParsedSignal if parseable, None to ignore
        
        Note:
            If signal is incomplete (no SL), add to waiting room instead of returning.
        """
        ...
    
    @abstractmethod
    async def parse_management(self, message, raw_text: str) -> Optional[ParsedManagement]:
        """
        Parse a message as a management action.
        
        Args:
            message: Telegram message object
            raw_text: Cleaned message text
        
        Returns:
            ParsedManagement if parseable, None to ignore
        """
        ...
    
    async def route_message(self, message, is_edit: bool = False):
        """
        Default routing logic for messages.
        Channels can override if they need custom routing.
        
        Routing priority:
        1. If edited message → try management, then waiting room completion
        2. If reply to known trade → management
        3. If reply to waiting room entry → waiting room completion
        4. Else → try management keywords, then entry parsing
        """
        from loguru import logger
        
        msg_id = message.id
        reply_to = getattr(message, 'reply_to_message_id', None)
        
        # Extract text
        raw_text = self._extract_text(message)
        if not raw_text:
            return
        
        # Clean text
        clean_text = self._clean_text(raw_text)
        
        logger.debug(f"[{self.display_name}] Routing message {msg_id} (edit={is_edit})")
        
        # Edited messages: try management first, then waiting room
        if is_edit:
            # Check if this completes a waiting room entry
            if self._is_waiting_room_entry(msg_id):
                await self._handle_waiting_room_completion(message, clean_text)
                return
            
            # Try management
            mgmt = await self.parse_management(message, clean_text)
            if mgmt:
                logger.info(f"[{self.display_name}] {mgmt}")
                # TODO: When we have trade execution, dispatch management action here
                return
            
            logger.debug(f"[{self.display_name}] Edited message {msg_id} - no action")
            return
        
        # New messages: check reply context
        if reply_to:
            # TODO: When we have database, check if reply_to is an active trade
            # For now, skip reply handling
            pass
        
        # Check if this completes a waiting room entry
        if await self._try_complete_waiting_room(message, clean_text):
            return
        
        # Try management keywords (some channels post management without replying)
        mgmt = await self.parse_management(message, clean_text)
        if mgmt:
            logger.info(f"[{self.display_name}] {mgmt}")
            # TODO: When we have trade execution, dispatch management action here
            return
        
        # Try entry parsing
        signal = await self.parse_entry(message, clean_text)
        if signal:
            logger.info(f"[{self.display_name}] {signal}")
            # TODO: When we have trade execution, dispatch entry signal here
            return
        
        logger.debug(f"[{self.display_name}] Message {msg_id} - no match")
    
    def _extract_text(self, message) -> str:
        """Extract text from Telegram message object."""
        text = ""
        if hasattr(message, 'content') and hasattr(message.content, 'text'):
            if hasattr(message.content.text, 'text'):
                text = message.content.text.text
            else:
                text = str(message.content.text)
        return text
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize message text.
        - Lowercase
        - Remove emojis
        - Collapse whitespace
        """
        import re
        
        # Lowercase
        text = text.lower()
        
        # Remove emojis (keep alphanumeric, spaces, and common punctuation)
        text = re.sub(r'[^\w\s\.\,\:\;\-\@\#\$\%\(\)\/\+\=]', ' ', text)
        
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _add_to_waiting_room(self, bare_signal: BareSignal):
        """Add incomplete signal to waiting room."""
        from loguru import logger
        
        key = (bare_signal.symbol, bare_signal.direction)
        
        # If already exists, update expiry
        if key in self._waiting_room:
            logger.info(
                f"[{self.display_name}] Waiting room: Updated expiry for "
                f"{bare_signal.symbol} {bare_signal.direction}"
            )
        else:
            logger.info(
                f"[{self.display_name}] Waiting room: Added "
                f"{bare_signal.symbol} {bare_signal.direction} (expires in 15 min)"
            )
        
        self._waiting_room[key] = bare_signal
    
    def _is_waiting_room_entry(self, msg_id: int) -> bool:
        """Check if msg_id is in waiting room."""
        return any(bs.msg_id == msg_id for bs in self._waiting_room.values())
    
    async def _try_complete_waiting_room(self, message, clean_text: str) -> bool:
        """
        Try to complete a waiting room entry with this message.
        Returns True if completed, False otherwise.
        """
        # Subclasses can override for custom completion logic
        return False
    
    async def _handle_waiting_room_completion(self, message, clean_text: str):
        """Handle completion of a waiting room entry via edit."""
        from loguru import logger
        
        msg_id = message.id
        
        # Find the bare signal
        bare_signal = None
        for bs in self._waiting_room.values():
            if bs.msg_id == msg_id:
                bare_signal = bs
                break
        
        if not bare_signal:
            return
        
        logger.info(
            f"[{self.display_name}] Waiting room: Attempting completion for "
            f"{bare_signal.symbol} {bare_signal.direction}"
        )
        
        # Try to parse as complete signal now
        signal = await self.parse_entry(message, clean_text)
        if signal and signal.sl:
            # Remove from waiting room
            key = (bare_signal.symbol, bare_signal.direction)
            del self._waiting_room[key]
            
            logger.info(f"[{self.display_name}] Waiting room: Completed! {signal}")
            # TODO: When we have trade execution, dispatch signal here
        else:
            logger.debug(f"[{self.display_name}] Waiting room: Still incomplete")
    
    def cleanup_expired_waiting_room(self):
        """Remove expired entries from waiting room."""
        from datetime import datetime
        from loguru import logger
        
        now = datetime.now()
        expired = [
            key for key, bs in self._waiting_room.items()
            if bs.expires_at <= now
        ]
        
        for key in expired:
            bs = self._waiting_room[key]
            logger.info(
                f"[{self.display_name}] Waiting room: Expired "
                f"{bs.symbol} {bs.direction} (msg_id={bs.msg_id})"
            )
            del self._waiting_room[key]
