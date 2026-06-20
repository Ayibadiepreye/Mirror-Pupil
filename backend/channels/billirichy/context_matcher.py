"""
BillirichyFX - Context Matcher
Implements Section 4.3: 8-Level Smart Match for Management Actions
"""

import re
from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger

from ...database import DatabaseManager, ActiveTrade


# Price extraction regex
PRICE_RE = re.compile(r'\b(\d{1,5}(?:\.\d{1,5})?)\b')

# Broadcast keywords
BROADCAST_KEYWORDS = [
    'close all', 'exit all', 'close everything', 'exit everything',
    'close trades', 'exit trades'
]


class BillirichyContextMatcher:
    """
    8-Level context matching for BillirichyFX management actions.
    Enhanced with reply chain traversal for deep context extraction.
    
    Levels (applied in order, stop at first match):
    1. Reply-to message ID
    2. Symbol + Direction
    3. Symbol only
    4. Direction only
    5. Price reference (with direction validation)
    6. Recency (last 15 minutes)
    7. Broadcast keyword
    8. Sole trade
    """
    
    def __init__(self, db: DatabaseManager, channel_id: int):
        self.db = db
        self.channel_id = channel_id
    
    async def match_trades(
        self,
        reply_to_msg_id: Optional[int],
        symbol: Optional[str],
        direction: Optional[str],
        text: str,
        account_key: str,
        action: str = None,
        client = None
    ) -> List[ActiveTrade]:
        """
        Match management message to active trades using 8-level algorithm.
        
        Args:
            reply_to_msg_id: Telegram reply-to message ID
            symbol: Extracted symbol from text
            direction: Extracted direction from text
            text: Full message text
            account_key: Account to match trades for
            action: Management action type (for compatibility with Firepips matcher)
            client: TradeLocker client (for compatibility with Firepips matcher)
        
        Returns:
            List of matching ActiveTrade objects
        """
        # Get all active trades for this account and channel
        all_trades = await self.db.get_active_trades_by_account_and_channel(
            account_key, self.channel_id
        )
        
        if not all_trades:
            logger.debug(f"[Context] No active trades for {account_key}")
            return []
        
        # Level 1: Reply-to message ID
        if reply_to_msg_id:
            matches = [t for t in all_trades if t.signal_id.endswith(f"_{reply_to_msg_id}")]
            if matches:
                logger.info(
                    f"[Context L1] Matched {len(matches)} trade(s) by reply-to msg_id={reply_to_msg_id}"
                )
                return matches
        
        # Level 2: Symbol + Direction
        if symbol and direction:
            matches = [
                t for t in all_trades
                if t.symbol == symbol and t.direction == direction
            ]
            if matches:
                logger.info(
                    f"[Context L2] Matched {len(matches)} trade(s) by symbol={symbol} direction={direction}"
                )
                return matches
        
        # Level 3: Symbol only
        if symbol:
            matches = [t for t in all_trades if t.symbol == symbol]
            if matches:
                logger.info(
                    f"[Context L3] Matched {len(matches)} trade(s) by symbol={symbol}"
                )
                return matches
        
        # Level 4: Direction only
        if direction:
            matches = [t for t in all_trades if t.direction == direction]
            if matches:
                logger.info(
                    f"[Context L4] Matched {len(matches)} trade(s) by direction={direction}"
                )
                return matches
        
        # Level 5: Price reference (with direction validation)
        prices = self._extract_prices(text)
        if prices:
            matches = await self._match_by_price(all_trades, prices, direction)
            if matches:
                logger.info(
                    f"[Context L5] Matched {len(matches)} trade(s) by price reference"
                )
                return matches
        
        # Level 6: Recency (last 15 minutes)
        recent_trades = [
            t for t in all_trades
            if t.entry_time and (datetime.utcnow() - t.entry_time) < timedelta(minutes=15)
        ]
        if len(recent_trades) == 1:
            logger.info(
                f"[Context L6] Matched 1 trade by recency (last 15 min)"
            )
            return recent_trades
        
        # Level 7: Broadcast keyword
        if self._has_broadcast_keyword(text):
            logger.info(
                f"[Context L7] Matched {len(all_trades)} trade(s) by broadcast keyword"
            )
            return all_trades
        
        # Level 8: Sole trade
        if len(all_trades) == 1:
            logger.info(
                f"[Context L8] Matched sole trade"
            )
            return all_trades
        
        # No match
        logger.warning(
            f"[Context] UNMATCHED: No trades found for account={account_key} "
            f"symbol={symbol} direction={direction}"
        )
        return []
    
    async def match_trades_with_chain(
        self,
        message,
        symbol: Optional[str],
        direction: Optional[str],
        text: str,
        account_key: str,
        telegram_client = None
    ) -> List[ActiveTrade]:
        """
        Match trades with reply chain traversal.
        
        Chain logic:
        1. Check current message for context (symbol/direction)
        2. If insufficient, follow reply chain backwards
        3. Accumulate context from each message in chain
        4. Stop when sufficient context found OR reach original message
        
        Args:
            message: Full Telegram message object
            symbol: Symbol extracted from current message
            direction: Direction extracted from current message
            text: Current message text
            account_key: Account to match trades for
            telegram_client: Telegram client for fetching messages
        
        Returns:
            List of matching ActiveTrade objects
        """
        reply_to_msg_id = getattr(message, 'reply_to_message_id', None)
        
        # Try matching with current context
        matches = await self.match_trades(
            reply_to_msg_id=reply_to_msg_id,
            symbol=symbol,
            direction=direction,
            text=text,
            account_key=account_key
        )
        
        if matches:
            logger.info(f"[Context] Matched {len(matches)} trade(s) from current message")
            return matches
        
        # If no matches and we have a reply, walk the chain
        if reply_to_msg_id and telegram_client:
            logger.info(f"[Context] No direct match, traversing reply chain from msg {reply_to_msg_id}")
            
            chain_context = await self._walk_reply_chain(
                telegram_client=telegram_client,
                channel_id=self.channel_id,
                starting_msg_id=reply_to_msg_id,
                max_depth=10
            )
            
            # Merge context from chain
            if chain_context['symbol'] and not symbol:
                symbol = chain_context['symbol']
                logger.info(f"[Context] Found symbol in chain: {symbol}")
            
            if chain_context['direction'] and not direction:
                direction = chain_context['direction']
                logger.info(f"[Context] Found direction in chain: {direction}")
            
            if chain_context['reply_to_original']:
                reply_to_msg_id = chain_context['reply_to_original']
                logger.info(f"[Context] Found original msg_id in chain: {reply_to_msg_id}")
            
            # Try matching again with enriched context
            matches = await self.match_trades(
                reply_to_msg_id=reply_to_msg_id,
                symbol=symbol,
                direction=direction,
                text=text,
                account_key=account_key
            )
            
            if matches:
                logger.info(f"[Context] ✓ Matched {len(matches)} trade(s) using reply chain context")
                return matches
        
        # No matches found
        logger.warning(f"[Context] Reply chain exhausted, no matches found")
        return []
    
    async def _walk_reply_chain(
        self,
        telegram_client,
        channel_id: int,
        starting_msg_id: int,
        max_depth: int
    ) -> dict:
        """
        Walk backwards through reply chain, extracting context.
        
        Returns:
            {
                'symbol': extracted symbol or None,
                'direction': extracted direction or None,
                'reply_to_original': original message ID or None
            }
        """
        accumulated_context = {
            'symbol': None,
            'direction': None,
            'reply_to_original': None
        }
        
        current_msg_id = starting_msg_id
        depth = 0
        
        while current_msg_id and depth < max_depth:
            try:
                # Fetch the message from Telegram
                msg = await telegram_client.get_message(channel_id, current_msg_id)
                
                if not msg:
                    logger.debug(f"[Chain] Could not fetch msg {current_msg_id}")
                    break
                
                # Extract text from message
                msg_text = self._extract_text_from_message(msg)
                
                if msg_text:
                    # Try to extract symbol if we don't have it yet
                    if not accumulated_context['symbol']:
                        from .entry import detect_symbol
                        symbol = detect_symbol(msg_text)
                        if symbol:
                            accumulated_context['symbol'] = symbol
                            logger.debug(f"[Chain] Found symbol at depth {depth}: {symbol}")
                    
                    # Try to extract direction if we don't have it yet
                    if not accumulated_context['direction']:
                        from .entry import detect_direction
                        direction = detect_direction(msg_text)
                        if direction:
                            accumulated_context['direction'] = direction
                            logger.debug(f"[Chain] Found direction at depth {depth}: {direction}")
                    
                    # Check if this message is a trade signal (has SL/TP)
                    if self._looks_like_trade_signal(msg_text):
                        accumulated_context['reply_to_original'] = current_msg_id
                        logger.info(f"[Chain] Found original trade signal at msg {current_msg_id}")
                        break
                
                # Move to parent reply
                parent_reply_id = getattr(msg, 'reply_to_message_id', None)
                
                if not parent_reply_id:
                    # Reached a message with no parent - this is the original
                    accumulated_context['reply_to_original'] = current_msg_id
                    logger.debug(f"[Chain] Reached end of chain at msg {current_msg_id}")
                    break
                
                current_msg_id = parent_reply_id
                depth += 1
                
            except Exception as e:
                logger.error(f"[Chain] Error traversing reply chain: {e}")
                break
        
        logger.info(
            f"[Chain] Traversal complete (depth={depth}): "
            f"symbol={accumulated_context['symbol']} "
            f"direction={accumulated_context['direction']} "
            f"original_msg={accumulated_context['reply_to_original']}"
        )
        
        return accumulated_context
    
    def _looks_like_trade_signal(self, text: str) -> bool:
        """Check if text looks like an entry signal (has SL or TP)."""
        text_lower = text.lower()
        has_sl = bool(re.search(
            r'\b(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss)\b',
            text_lower
        ))
        has_tp = bool(re.search(
            r'\b(?:tp|t\.p|t/p|take\s*profit|takeprofit|take-profit|target)\b',
            text_lower
        ))
        return has_sl or has_tp
    
    def _extract_text_from_message(self, message) -> str:
        """Extract text from Telegram message object."""
        text = ""
        if hasattr(message, 'content') and hasattr(message.content, 'text'):
            if hasattr(message.content.text, 'text'):
                text = message.content.text.text
            else:
                text = str(message.content.text)
        return text
    
    def _extract_prices(self, text: str) -> List[float]:
        """Extract all price-like numbers from text."""
        prices = []
        for match in PRICE_RE.finditer(text):
            try:
                price = float(match.group(1))
                # Filter reasonable prices (avoid dates, percentages, etc.)
                if 0.01 < price < 100000:
                    prices.append(price)
            except ValueError:
                continue
        return prices
    
    async def _match_by_price(
        self,
        trades: List[ActiveTrade],
        prices: List[float],
        direction: Optional[str]
    ) -> List[ActiveTrade]:
        """
        Match trades by price reference with pip tolerance.
        
        Pip tolerance:
        - Forex non-JPY: ±0.0010 (10 pips)
        - JPY pairs: ±0.10 (10 pips)
        - XAUUSD: ±2.00 (20 pips)
        """
        matches = []
        
        for trade in trades:
            # Direction validation if provided
            if direction and trade.direction != direction:
                continue
            
            # Get tolerance for this symbol
            tolerance = self._get_pip_tolerance(trade.symbol)
            
            # Check if any price matches entry, SL, or TP
            for price in prices:
                if self._price_matches(price, trade.entry_price, tolerance):
                    matches.append(trade)
                    break
                if trade.sl and self._price_matches(price, trade.sl, tolerance):
                    matches.append(trade)
                    break
                if trade.tp and self._price_matches(price, trade.tp, tolerance):
                    matches.append(trade)
                    break
        
        return matches
    
    def _get_pip_tolerance(self, symbol: str) -> float:
        """Get pip tolerance for symbol."""
        if 'JPY' in symbol:
            return 0.10  # 10 pips for JPY pairs
        elif symbol == 'XAUUSD':
            return 2.00  # 20 pips for gold
        else:
            return 0.0010  # 10 pips for other forex
    
    def _price_matches(self, price1: float, price2: float, tolerance: float) -> bool:
        """Check if two prices match within tolerance."""
        return abs(price1 - price2) <= tolerance
    
    def _has_broadcast_keyword(self, text: str) -> bool:
        """Check if text contains broadcast keyword."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in BROADCAST_KEYWORDS)
    
    async def match_trades_with_chain(
        self,
        message,
        symbol: Optional[str],
        direction: Optional[str],
        text: str,
        account_key: str,
        telegram_client = None
    ) -> List[ActiveTrade]:
        """
        Match trades with reply chain traversal.
        
        Chain logic:
        1. Check current message for context (symbol/direction)
        2. If insufficient, follow reply chain backwards
        3. Accumulate context from each message in chain
        4. Stop when sufficient context found OR reach original message
        
        Args:
            message: Telegram message object
            symbol: Extracted symbol from current message
            direction: Extracted direction from current message
            text: Message text
            account_key: Account to match trades for
            telegram_client: Telegram client for fetching messages in chain
        
        Returns:
            List of matching ActiveTrade objects
        """
        # Extract context from current message
        current_symbol = symbol
        current_direction = direction
        reply_to_msg_id = getattr(message, 'reply_to_message_id', None)
        
        # Try matching with current context
        matches = await self.match_trades(
            reply_to_msg_id=reply_to_msg_id,
            symbol=current_symbol,
            direction=current_direction,
            text=text,
            account_key=account_key
        )
        
        if matches:
            logger.info(f"[Context] Matched {len(matches)} trade(s) from current message")
            return matches
        
        # If no matches and we have a reply, walk the chain
        if reply_to_msg_id and telegram_client:
            logger.info(f"[Context] No direct match, traversing reply chain from msg {reply_to_msg_id}")
            
            chain_context = await self._walk_reply_chain(
                telegram_client=telegram_client,
                channel_id=self.channel_id,
                starting_msg_id=reply_to_msg_id,
                max_depth=10
            )
            
            # Merge context from chain
            if chain_context['symbol'] and not current_symbol:
                current_symbol = chain_context['symbol']
                logger.info(f"[Context] Found symbol in chain: {current_symbol}")
            
            if chain_context['direction'] and not current_direction:
                current_direction = chain_context['direction']
                logger.info(f"[Context] Found direction in chain: {current_direction}")
            
            if chain_context['reply_to_original']:
                reply_to_msg_id = chain_context['reply_to_original']
                logger.info(f"[Context] Found original msg_id in chain: {reply_to_msg_id}")
            
            # Try matching again with enriched context
            matches = await self.match_trades(
                reply_to_msg_id=reply_to_msg_id,
                symbol=current_symbol,
                direction=current_direction,
                text=text,
                account_key=account_key
            )
            
            if matches:
                logger.info(f"[Context] ✓ Matched {len(matches)} trade(s) using reply chain context")
                return matches
        
        # No matches found even with chain traversal
        logger.warning(f"[Context] Reply chain exhausted, no matches found")
        return []
    
    async def _walk_reply_chain(
        self,
        telegram_client,
        channel_id: int,
        starting_msg_id: int,
        max_depth: int
    ) -> dict:
        """
        Walk backwards through reply chain, extracting context.
        
        Args:
            telegram_client: Telegram client for fetching messages
            channel_id: Channel ID
            starting_msg_id: Message ID to start from
            max_depth: Maximum chain depth to prevent infinite loops
        
        Returns:
            {
                'symbol': extracted symbol or None,
                'direction': extracted direction or None,
                'reply_to_original': original message ID or None
            }
        """
        accumulated_context = {
            'symbol': None,
            'direction': None,
            'reply_to_original': None
        }
        
        current_msg_id = starting_msg_id
        depth = 0
        
        while current_msg_id and depth < max_depth:
            try:
                # Fetch the message from Telegram
                msg = await telegram_client.get_message(channel_id, current_msg_id)
                
                if not msg:
                    logger.debug(f"[Chain] Could not fetch msg {current_msg_id}")
                    break
                
                # Extract text from message
                msg_text = self._extract_text_from_message(msg)
                
                if msg_text:
                    # Try to extract symbol if we don't have it yet
                    if not accumulated_context['symbol']:
                        from .entry import detect_symbol
                        found_symbol = detect_symbol(msg_text)
                        if found_symbol:
                            accumulated_context['symbol'] = found_symbol
                            logger.debug(f"[Chain] Found symbol at depth {depth}: {found_symbol}")
                    
                    # Try to extract direction if we don't have it yet
                    if not accumulated_context['direction']:
                        from .entry import detect_direction
                        found_direction = detect_direction(msg_text)
                        if found_direction:
                            accumulated_context['direction'] = found_direction
                            logger.debug(f"[Chain] Found direction at depth {depth}: {found_direction}")
                    
                    # Check if this message is a trade signal (has SL/TP)
                    if self._looks_like_trade_signal(msg_text):
                        accumulated_context['reply_to_original'] = current_msg_id
                        logger.info(f"[Chain] Found original trade signal at msg {current_msg_id}")
                        break
                
                # Move to parent reply
                parent_reply_id = getattr(msg, 'reply_to_message_id', None)
                
                if not parent_reply_id:
                    # Reached a message with no parent - this is the original
                    accumulated_context['reply_to_original'] = current_msg_id
                    logger.debug(f"[Chain] Reached end of chain at msg {current_msg_id}")
                    break
                
                current_msg_id = parent_reply_id
                depth += 1
                
            except Exception as e:
                logger.error(f"[Chain] Error traversing reply chain: {e}")
                break
        
        logger.info(
            f"[Chain] Traversal complete (depth={depth}): "
            f"symbol={accumulated_context['symbol']} "
            f"direction={accumulated_context['direction']} "
            f"original_msg={accumulated_context['reply_to_original']}"
        )
        
        return accumulated_context
    
    def _looks_like_trade_signal(self, text: str) -> bool:
        """Check if text looks like an entry signal (has SL or TP)."""
        text_lower = text.lower()
        has_sl = bool(re.search(r'\b(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss)\b', text_lower))
        has_tp = bool(re.search(r'\b(?:tp|t\.p|t/p|take\s*profit|takeprofit|take-profit)\b', text_lower))
        return has_sl or has_tp
    
    def _extract_text_from_message(self, message) -> str:
        """Extract text from Telegram message object."""
        text = ""
        if hasattr(message, 'content') and hasattr(message.content, 'text'):
            if hasattr(message.content.text, 'text'):
                text = message.content.text.text
            else:
                text = str(message.content.text)
        return text
    
    async def validate_bare_signal_completion(
        self,
        bare_signal,
        new_signal,
        client = None
    ) -> bool:
        """
        Validate that a new signal matches a bare signal in the waiting room.
        Uses price checking with live market price to prevent false completions.
        
        Args:
            bare_signal: BareSignal from waiting room
            new_signal: ParsedSignal with SL that might complete the bare signal
            client: TradeLocker client for live price fetching
        
        Returns:
            True if new signal is valid completion, False otherwise
        """
        # Must match symbol and direction (basic check)
        if bare_signal.symbol != new_signal.symbol:
            return False
        if bare_signal.direction != new_signal.direction:
            return False
        
        # For LIMIT/STOP orders: check if entry prices match
        # For MARKET orders: skip entry price check (executes at current price)
        if bare_signal.order_type in ['LIMIT', 'STOP']:
            if bare_signal.entry_price and new_signal.entry_price:
                tolerance = self._get_pip_tolerance(bare_signal.symbol)
                if not self._price_matches(bare_signal.entry_price, new_signal.entry_price, tolerance):
                    logger.debug(
                        f"[Bare Signal Validation] Entry price mismatch for {bare_signal.order_type}: "
                        f"bare={bare_signal.entry_price:.5f} new={new_signal.entry_price:.5f}"
                    )
                    return False
        
        # Fetch current market price and validate SL placement
        if client:
            try:
                current_price = await client.get_market_price(bare_signal.symbol)
                tolerance = self._get_pip_tolerance(bare_signal.symbol)
                
                # Check if new signal's SL is reasonable relative to current price
                # For BUY: SL should be below current price
                # For SELL: SL should be above current price
                if bare_signal.direction == 'BUY':
                    if new_signal.sl >= current_price:
                        logger.debug(
                            f"[Bare Signal Validation] Invalid SL for BUY: "
                            f"SL={new_signal.sl:.5f} >= current={current_price:.5f}"
                        )
                        return False
                else:  # SELL
                    if new_signal.sl <= current_price:
                        logger.debug(
                            f"[Bare Signal Validation] Invalid SL for SELL: "
                            f"SL={new_signal.sl:.5f} <= current={current_price:.5f}"
                        )
                        return False
                
                # For LIMIT/STOP orders: check bare signal entry is still relevant
                # For MARKET orders: skip this check (always relevant at current price)
                if bare_signal.order_type in ['LIMIT', 'STOP'] and bare_signal.entry_price:
                    if not self._price_matches(bare_signal.entry_price, current_price, tolerance * 5):
                        logger.debug(
                            f"[Bare Signal Validation] Bare signal entry too far from current: "
                            f"entry={bare_signal.entry_price:.5f} current={current_price:.5f}"
                        )
                        return False
                
                logger.info(
                    f"[Bare Signal Validation] ✓ Valid completion: "
                    f"{bare_signal.symbol} {bare_signal.direction} {bare_signal.order_type} "
                    f"current={current_price:.5f} new_SL={new_signal.sl:.5f}"
                )
                
            except Exception as e:
                logger.debug(f"[Bare Signal Validation] Could not fetch price: {e}")
                # If we can't fetch price, fall back to basic validation (already passed)
        
        return True
