"""
Mirror Pupil v5.1 - Trailing Stop Updater
Updates trailing stops every 60 seconds for trades with TP1 hit.
Implements Section 4.6 of the spec.
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime
from loguru import logger

from ..database import DatabaseManager, ActiveTrade
from .account_manager import get_account_manager


# Trail distances per symbol (Section 4.6)
TRAIL_DISTANCE = {
    # Forex non-JPY
    'EURUSD': 0.0008,
    'GBPUSD': 0.0008,
    'USDCAD': 0.0008,
    'AUDUSD': 0.0008,
    'NZDUSD': 0.0008,
    'EURAUD': 0.0008,
    'GBPAUD': 0.0008,
    'USDCHF': 0.0008,
    'GBPCAD': 0.0008,
    'AUDCAD': 0.0008,
    'EURNZD': 0.0008,
    'EURGBP': 0.0008,
    'GBPCHF': 0.0008,
    'EURCAD': 0.0008,
    
    # Forex JPY pairs
    'USDJPY': 0.08,
    'GBPJPY': 0.08,
    'EURJPY': 0.08,
    'AUDJPY': 0.08,
    'CADJPY': 0.08,
    'CHFJPY': 0.08,
    
    # Metals
    'XAUUSD': 0.15,  # 15 pips for gold
    'XAGUSD': 0.08,  # 8 pips for silver
    
    # Indices
    'US30': 15.0,    # 15 points
    
    # Commodities
    'USOIL': 0.10,   # 10 pips
}


class TrailingStopUpdater:
    """
    Updates trailing stops every 60 seconds for trades with TP1 hit.
    
    Features:
    - Runs every 60 seconds (per spec Section 4.6)
    - Only updates trades where tp1_hit = True
    - Trail distances vary by symbol
    - Only moves SL in favorable direction (never worse)
    - Logs all trailing stop updates
    
    Per spec Section 4.6:
    - Activated when TP1 is hit on multi-TP trade
    - Trails market price by fixed distance
    - BUY: new_sl = market_price - trail_distance (only if > current_sl)
    - SELL: new_sl = market_price + trail_distance (only if < current_sl)
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.account_manager = get_account_manager()
        self.updater_task: Optional[asyncio.Task] = None
        
        # Configuration (per spec Section 4.6)
        self.update_interval = 60  # 60 seconds
        
        logger.info("Initialized TrailingStopUpdater")
    
    async def start_updating(self):
        """Start background update task."""
        if self.updater_task:
            logger.warning("Trailing stop updater already running")
            return
        
        self.updater_task = asyncio.create_task(self._update_loop())
        logger.info(f"✓ Started trailing stop updates (every {self.update_interval}s)")
    
    async def stop_updating(self):
        """Stop background update task."""
        if self.updater_task:
            self.updater_task.cancel()
            try:
                await self.updater_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped trailing stop updates")
    
    async def _update_loop(self):
        """Main update loop - runs every 60 seconds."""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                await self._update_all_trailing_stops()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trailing stop update error: {e}")
    
    async def _update_all_trailing_stops(self):
        """Update trailing stops for all eligible trades."""
        # Get all active trades with tp1_hit = True
        trades = await self.db.get_active_trades_with_tp1_hit()
        
        if not trades:
            return  # No trades to update
        
        logger.debug(f"Updating trailing stops for {len(trades)} trade(s)")
        
        for trade in trades:
            try:
                await self._update_trailing_stop(trade)
            except Exception as e:
                logger.error(
                    f"Failed to update trailing stop for {trade.signal_id}: {e}"
                )
    
    async def _update_trailing_stop(self, trade: ActiveTrade):
        """
        Update trailing stop for a single trade.
        
        Logic (Section 4.6):
        1. Get current market price
        2. Calculate new SL = market_price ± trail_distance
        3. Only update if new SL is better than current SL
        4. Call TradeLocker API to modify order
        5. Update database
        """
        # Get trail distance for this symbol
        trail = TRAIL_DISTANCE.get(trade.symbol)
        if trail is None:
            logger.warning(
                f"No trail distance defined for {trade.symbol} - skipping"
            )
            return
        
        # Get TradeLocker client
        tl_client = self.account_manager.get_client_for_account(trade.account_key)
        if not tl_client:
            logger.warning(
                f"No TradeLocker client for {trade.account_key}"
            )
            return
        
        try:
            # Get current market price
            market_price = await self._get_market_price(tl_client, trade.symbol)
            if market_price is None:
                return
            
            # Calculate new trailing SL
            if trade.direction == 'BUY':
                new_sl = market_price - trail
                # Only move SL up (never down)
                if new_sl <= trade.sl:
                    return  # No update needed
            
            elif trade.direction == 'SELL':
                new_sl = market_price + trail
                # Only move SL down (never up)
                if new_sl >= trade.sl:
                    return  # No update needed
            
            else:
                logger.error(f"Invalid direction: {trade.direction}")
                return
            
            # Update SL via TradeLocker API
            await tl_client.modify_position(
                position_id=trade.tl_position_id,
                stop_loss=new_sl
            )
            
            # Update database
            await self.db.update_trade(
                trade.trade_id,
                sl=new_sl
            )
            
            logger.info(
                f"[TRAIL] {trade.signal_id} ({trade.symbol} {trade.direction}): "
                f"SL {trade.sl:.5f} → {new_sl:.5f} "
                f"(market: {market_price:.5f}, trail: {trail})"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to update trailing stop for {trade.signal_id}: {e}"
            )
    
    async def _get_market_price(self, tl_client, symbol: str) -> Optional[float]:
        """Get current market price for symbol."""
        try:
            # Get current bid/ask
            quote = await tl_client.get_quote(symbol)
            
            # Use mid-price
            bid = float(quote.get('bid', 0))
            ask = float(quote.get('ask', 0))
            
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get market price for {symbol}: {e}")
            return None


# Singleton instance
_updater: Optional[TrailingStopUpdater] = None


def get_trailing_stop_updater(db: Optional[DatabaseManager] = None) -> TrailingStopUpdater:
    """Get or create singleton trailing stop updater."""
    global _updater
    if _updater is None:
        if db is None:
            raise ValueError("DatabaseManager required for first initialization")
        _updater = TrailingStopUpdater(db)
    return _updater
