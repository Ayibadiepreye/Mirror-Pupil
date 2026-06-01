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
        account_key: str
    ) -> List[ActiveTrade]:
        """
        Match management message to active trades using 8-level algorithm.
        
        Args:
            reply_to_msg_id: Telegram reply-to message ID
            symbol: Extracted symbol from text
            direction: Extracted direction from text
            text: Full message text
            account_key: Account to match trades for
        
        Returns:
            List of matching ActiveTrade objects
        """
        # Get all active trades for this account and channel
        all_trades = await self.db.get_active_trades_by_channel(
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
