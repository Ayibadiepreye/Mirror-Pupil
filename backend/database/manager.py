"""
Mirror Pupil v5.1 - Database Manager
Connection pooling and query helpers for Neon PostgreSQL.
"""

import asyncio
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncpg
from loguru import logger

from .schema import SCHEMA_DDL, INITIAL_DATA, CLEANUP_QUERIES, SCHEMA_VERSION
from .models import (
    Channel, RiskProfile, Account, ChannelSubscription,
    ActiveTrade, WaitingRoom, TradeHistory, ProfitableDay
)


class DatabaseManager:
    """
    Manages Neon PostgreSQL connection pool and provides query helpers.
    
    Features:
    - Connection pooling with asyncpg
    - Automatic schema initialization
    - Migration support
    - Query helpers for all tables
    - Periodic cleanup tasks
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.pool: Optional[asyncpg.Pool] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("Initialized DatabaseManager")
    
    async def connect(self, min_size: int = 5, max_size: int = 20):
        """
        Create connection pool to Neon PostgreSQL.
        
        Args:
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        if self.pool:
            logger.warning("Database pool already exists")
            return
        
        logger.info(f"Connecting to Neon PostgreSQL (pool: {min_size}-{max_size})...")
        
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=min_size,
                max_size=max_size,
                command_timeout=60
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"✓ Connected to PostgreSQL: {version[:50]}...")
            
            # Initialize schema
            await self.initialize_schema()
            
            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("✓ Database ready")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Close connection pool."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.pool:
            await self.pool.close()
            logger.info("✓ Database disconnected")
    
    async def initialize_schema(self):
        """
        Initialize database schema and insert default data.
        """
        async with self.pool.acquire() as conn:
            # Check current schema version
            try:
                current_version = await conn.fetchval(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                )
            except asyncpg.UndefinedTableError:
                current_version = 0
            
            if current_version >= SCHEMA_VERSION:
                logger.info(f"Schema up to date (v{current_version})")
                return
            
            logger.info(f"Initializing schema (v{current_version} → v{SCHEMA_VERSION})...")
            
            # Execute schema DDL
            await conn.execute(SCHEMA_DDL)
            
            # Insert initial data
            await conn.execute(INITIAL_DATA)
            
            # Update schema version
            await conn.execute(
                "INSERT INTO schema_version (version) VALUES ($1) "
                "ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP",
                SCHEMA_VERSION
            )
            
            logger.info(f"✓ Schema initialized to v{SCHEMA_VERSION}")
    
    async def _cleanup_loop(self):
        """
        Periodic cleanup task (runs every 30 seconds per spec Section 3.8, 5.7).
        Removes expired waiting room entries and old message cache.
        """
        while True:
            try:
                await asyncio.sleep(30)  # 30 seconds (spec requirement)
                
                async with self.pool.acquire() as conn:
                    # Delete expired waiting room entries
                    deleted_waiting = await conn.execute(
                        "DELETE FROM waiting_room WHERE expires_at < NOW()"
                    )
                    
                    # Delete old message cache (entries older than 2 minutes)
                    deleted_cache = await conn.execute(
                        "DELETE FROM message_cache WHERE processed_at < NOW() - INTERVAL '2 minutes'"
                    )
                    
                    if "DELETE" in deleted_waiting or "DELETE" in deleted_cache:
                        logger.debug(f"Cleanup: {deleted_waiting}, {deleted_cache}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    # ==================== CHANNEL QUERIES ====================
    
    async def get_all_channels(self) -> List[Channel]:
        """Get all channels."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM channels ORDER BY priority")
            return [Channel(**dict(row)) for row in rows]
    
    async def get_enabled_channels(self) -> List[Channel]:
        """Get all enabled channels."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM channels WHERE enabled = TRUE ORDER BY priority"
            )
            return [Channel(**dict(row)) for row in rows]
    
    async def get_channel(self, channel_id: int) -> Optional[Channel]:
        """Get channel by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM channels WHERE channel_id = $1", channel_id
            )
            return Channel(**dict(row)) if row else None
    
    async def add_channel(self, channel: Channel) -> bool:
        """Add a new channel."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO channels (
                        channel_id, display_name, signal_prefix,
                        entry_logic_module, management_logic_module,
                        priority, enabled, notes
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    channel.channel_id, channel.display_name, channel.signal_prefix,
                    channel.entry_logic_module, channel.management_logic_module,
                    channel.priority, channel.enabled, channel.notes
                )
                logger.info(f"✓ Added channel: {channel.display_name} (ID: {channel.channel_id})")
                return True
        except Exception as e:
            logger.error(f"Failed to add channel: {e}")
            return False
    
    async def update_channel_enabled(self, channel_id: int, enabled: bool) -> bool:
        """Toggle channel enabled status."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE channels SET enabled = $1 WHERE channel_id = $2",
                    enabled, channel_id
                )
                logger.info(f"✓ Channel {channel_id} enabled={enabled}")
                return True
        except Exception as e:
            logger.error(f"Failed to update channel: {e}")
            return False
    
    # ==================== RISK PROFILE QUERIES ====================
    
    async def get_all_risk_profiles(self) -> List[RiskProfile]:
        """Get all risk profiles."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM risk_profiles ORDER BY profile_name")
            return [RiskProfile(**dict(row)) for row in rows]
    
    async def get_default_risk_profile(self) -> Optional[RiskProfile]:
        """Get the default risk profile."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM risk_profiles WHERE is_default = TRUE LIMIT 1"
            )
            return RiskProfile(**dict(row)) if row else None
    
    async def get_risk_profile(self, profile_id: int) -> Optional[RiskProfile]:
        """Get risk profile by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM risk_profiles WHERE profile_id = $1", profile_id
            )
            return RiskProfile(**dict(row)) if row else None
    
    # ==================== ACCOUNT QUERIES ====================
    
    async def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM accounts")
            return [Account(**dict(row)) for row in rows]
    
    async def get_account(self, account_key: str) -> Optional[Account]:
        """Get account by key."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM accounts WHERE account_key = $1", account_key
            )
            return Account(**dict(row)) if row else None
    
    async def add_account(self, account: Account) -> bool:
        """Add a new account."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO accounts (
                        account_key, credential_key, tl_account_id,
                        tl_email, tl_password, tl_server, display_name,
                        initial_balance, current_balance, highest_banked_balance,
                        daily_start_balance, last_synced_balance, cycle_start_date
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """,
                    account.account_key, account.credential_key, account.tl_account_id,
                    account.tl_email, account.tl_password, account.tl_server,
                    account.display_name, account.initial_balance, account.current_balance,
                    account.initial_balance,  # highest_banked_balance starts at initial
                    account.current_balance,  # daily_start_balance
                    account.current_balance,  # last_synced_balance
                    account.cycle_start_date or datetime.now().date()
                )
                logger.info(f"✓ Added account: {account.account_key}")
                return True
        except Exception as e:
            logger.error(f"Failed to add account: {e}")
            return False
    
    async def update_account_balance(
        self,
        account_key: str,
        current_balance: float,
        equity: Optional[float] = None
    ) -> bool:
        """Update account balance and equity."""
        try:
            async with self.pool.acquire() as conn:
                if equity is not None:
                    await conn.execute(
                        """
                        UPDATE accounts
                        SET current_balance = $1,
                            all_time_high_equity = GREATEST(COALESCE(all_time_high_equity, 0), $2),
                            last_synced_balance = $1
                        WHERE account_key = $3
                        """,
                        current_balance, equity, account_key
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE accounts
                        SET current_balance = $1, last_synced_balance = $1
                        WHERE account_key = $2
                        """,
                        current_balance, account_key
                    )
                return True
        except Exception as e:
            logger.error(f"Failed to update account balance: {e}")
            return False
    
    async def update_account_paused(self, account_key: str, paused: bool) -> bool:
        """Toggle account paused status."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE accounts SET paused = $1 WHERE account_key = $2",
                    paused, account_key
                )
                logger.info(f"✓ Account {account_key} paused={paused}")
                return True
        except Exception as e:
            logger.error(f"Failed to update account: {e}")
            return False
    
    # ==================== CHANNEL SUBSCRIPTION QUERIES ====================
    
    async def get_channel_subscriptions(self, account_key: str) -> List[ChannelSubscription]:
        """Get all channel subscriptions for an account."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM channel_subscriptions WHERE account_key = $1",
                account_key
            )
            return [ChannelSubscription(**dict(row)) for row in rows]
    
    async def is_channel_subscribed(self, account_key: str, channel_id: int) -> bool:
        """Check if account is subscribed to a channel."""
        async with self.pool.acquire() as conn:
            enabled = await conn.fetchval(
                """
                SELECT enabled FROM channel_subscriptions
                WHERE account_key = $1 AND channel_id = $2
                """,
                account_key, channel_id
            )
            return enabled if enabled is not None else True  # Default to True
    
    async def sync_channel_subscriptions(self):
        """
        Ensure every (account, channel) pair has a subscription row.
        Called when a new account or channel is added.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO channel_subscriptions (account_key, channel_id, enabled)
                SELECT a.account_key, c.channel_id, TRUE
                FROM accounts a
                CROSS JOIN channels c
                ON CONFLICT (account_key, channel_id) DO NOTHING
                """
            )
            logger.debug("✓ Synced channel subscriptions")
    
    # ==================== ACTIVE TRADE QUERIES ====================
    
    async def add_active_trade(self, trade: ActiveTrade) -> Optional[int]:
        """Add a new active trade. Returns trade_id."""
        try:
            async with self.pool.acquire() as conn:
                trade_id = await conn.fetchval(
                    """
                    INSERT INTO active_trades (
                        account_key, channel_id, signal_id, sub_signal_id,
                        symbol, direction, entry_price, sl, tp, lot_size,
                        tl_order_id, tl_position_id, status, risk_usd
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    RETURNING trade_id
                    """,
                    trade.account_key, trade.channel_id, trade.signal_id, trade.sub_signal_id,
                    trade.symbol, trade.direction, trade.entry_price, trade.sl, trade.tp,
                    trade.lot_size, trade.tl_order_id, trade.tl_position_id,
                    trade.status, trade.risk_usd
                )
                logger.info(f"✓ Added active trade: {trade.signal_id} on {trade.account_key}")
                return trade_id
        except Exception as e:
            logger.error(f"Failed to add active trade: {e}")
            return None
    
    async def get_active_trades(self, account_key: str) -> List[ActiveTrade]:
        """Get all active trades for an account."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM active_trades WHERE account_key = $1 AND status = 'filled'",
                account_key
            )
            return [ActiveTrade(**dict(row)) for row in rows]
    
    async def get_active_trades_with_tp1_hit(self) -> List[ActiveTrade]:
        """
        Get all active trades where TP1 has been hit (for trailing stop updates).
        Per spec Section 4.6: Trailing stops activate after TP1 hit.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM active_trades WHERE tp1_hit = TRUE AND status = 'filled'"
            )
            return [ActiveTrade(**dict(row)) for row in rows]
    
    async def get_active_trades_by_channel(self, channel_id: int) -> List[ActiveTrade]:
        """
        Get all active trades for a specific channel (for autonomous management).
        Per spec Section 4.7, 6.7: Autonomous actions apply per channel.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM active_trades WHERE channel_id = $1 AND status = 'filled'",
                channel_id
            )
            return [ActiveTrade(**dict(row)) for row in rows]
    
    async def get_active_trade_count(self, account_key: str) -> int:
        """Get count of active trades for an account."""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM active_trades WHERE account_key = $1 AND status = 'filled'",
                account_key
            )
            return count or 0
    
    async def close_active_trade(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        outcome: str,
        close_reason: str
    ) -> bool:
        """
        Close an active trade and move to history.
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Get trade details
                    trade = await conn.fetchrow(
                        "SELECT * FROM active_trades WHERE trade_id = $1", trade_id
                    )
                    
                    if not trade:
                        logger.error(f"Trade {trade_id} not found")
                        return False
                    
                    # Move to history
                    await conn.execute(
                        """
                        INSERT INTO trade_history (
                            account_key, channel_id, signal_id, sub_signal_id,
                            symbol, direction, entry_price, exit_price,
                            sl, tp, lot_size, entry_time, pnl, outcome, close_reason
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                        """,
                        trade['account_key'], trade['channel_id'], trade['signal_id'],
                        trade['sub_signal_id'], trade['symbol'], trade['direction'],
                        trade['entry_price'], exit_price, trade['sl'], trade['tp'],
                        trade['lot_size'], trade['entry_time'], pnl, outcome, close_reason
                    )
                    
                    # Delete from active trades
                    await conn.execute(
                        "DELETE FROM active_trades WHERE trade_id = $1", trade_id
                    )
                    
                    logger.info(f"✓ Closed trade {trade_id}: {outcome} ({close_reason})")
                    return True
        except Exception as e:
            logger.error(f"Failed to close trade: {e}")
            return False
    
    # ==================== WAITING ROOM QUERIES ====================
    
    async def add_to_waiting_room(self, entry: WaitingRoom) -> bool:
        """
        Add entry to waiting room, or reset expiry if duplicate.
        
        Spec requirement (Sections 3.7, 5.6):
        If a second bare signal arrives for the same symbol+direction while one
        is already waiting, reset the existing entry's expires_at instead of
        creating a duplicate.
        """
        try:
            async with self.pool.acquire() as conn:
                # Check if entry already exists for this symbol+direction
                existing = await conn.fetchrow(
                    """
                    SELECT id, expires_at FROM waiting_room
                    WHERE channel_id = $1 AND symbol = $2 AND direction = $3
                    AND expires_at > NOW()
                    """,
                    entry.channel_id, entry.symbol, entry.direction
                )
                
                if existing:
                    # Second bare signal - reset expiry instead of creating duplicate
                    await conn.execute(
                        "UPDATE waiting_room SET expires_at = $1 WHERE id = $2",
                        entry.expires_at, existing['id']
                    )
                    logger.info(
                        f"✓ Reset waiting room expiry: {entry.symbol} {entry.direction} "
                        f"(was {existing['expires_at']}, now {entry.expires_at})"
                    )
                else:
                    # New entry - insert
                    await conn.execute(
                        """
                        INSERT INTO waiting_room (
                            channel_id, symbol, direction, entry_msg_id, expires_at
                        ) VALUES ($1, $2, $3, $4, $5)
                        """,
                        entry.channel_id, entry.symbol, entry.direction,
                        entry.entry_msg_id, entry.expires_at
                    )
                    logger.debug(f"✓ Added to waiting room: {entry.symbol} {entry.direction}")
                return True
        except Exception as e:
            logger.error(f"Failed to add to waiting room: {e}")
            return False
    
    async def get_from_waiting_room(
        self,
        channel_id: int,
        symbol: str,
        direction: str
    ) -> Optional[WaitingRoom]:
        """Get entry from waiting room."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM waiting_room
                WHERE channel_id = $1 AND symbol = $2 AND direction = $3
                AND expires_at > NOW()
                LIMIT 1
                """,
                channel_id, symbol, direction
            )
            return WaitingRoom(**dict(row)) if row else None
    
    async def remove_from_waiting_room(self, entry_id: int) -> bool:
        """Remove entry from waiting room."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM waiting_room WHERE id = $1", entry_id
                )
                return True
        except Exception as e:
            logger.error(f"Failed to remove from waiting room: {e}")
            return False
    
    # ==================== MESSAGE CACHE QUERIES ====================
    
    async def is_message_processed(self, msg_id: int, channel_id: int) -> bool:
        """Check if message has been processed."""
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM message_cache
                    WHERE msg_id = $1 AND channel_id = $2
                )
                """,
                msg_id, channel_id
            )
            return exists
    
    async def mark_message_processed(self, msg_id: int, channel_id: int) -> bool:
        """Mark message as processed."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO message_cache (msg_id, channel_id)
                    VALUES ($1, $2)
                    ON CONFLICT (msg_id, channel_id) DO NOTHING
                    """,
                    msg_id, channel_id
                )
                return True
        except Exception as e:
            logger.error(f"Failed to mark message processed: {e}")
            return False
    
    # ==================== TRADE UPDATE METHODS ====================
    
    async def update_trade_sl(self, trade_id: int, new_sl: float) -> bool:
        """Update stop loss for an active trade."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE active_trades SET sl = $1 WHERE trade_id = $2",
                    new_sl, trade_id
                )
                logger.debug(f"✓ Updated SL for trade {trade_id}: {new_sl}")
                return True
        except Exception as e:
            logger.error(f"Failed to update SL for trade {trade_id}: {e}")
            return False
    
    async def update_trade_tp(self, trade_id: int, new_tp: float) -> bool:
        """Update take profit for an active trade."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE active_trades SET tp = $1 WHERE trade_id = $2",
                    new_tp, trade_id
                )
                logger.debug(f"✓ Updated TP for trade {trade_id}: {new_tp}")
                return True
        except Exception as e:
            logger.error(f"Failed to update TP for trade {trade_id}: {e}")
            return False
    
    async def update_trade_lot_size(self, trade_id: int, new_lot_size: float) -> bool:
        """Update lot size for an active trade (after partial close)."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE active_trades SET lot_size = $1 WHERE trade_id = $2",
                    new_lot_size, trade_id
                )
                logger.debug(f"✓ Updated lot size for trade {trade_id}: {new_lot_size}")
                return True
        except Exception as e:
            logger.error(f"Failed to update lot size for trade {trade_id}: {e}")
            return False
    
    async def mark_tp1_hit(self, trade_id: int) -> bool:
        """Mark TP1 as hit for trailing stop activation."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE active_trades SET tp1_hit = TRUE WHERE trade_id = $1",
                    trade_id
                )
                logger.debug(f"✓ Marked TP1 hit for trade {trade_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to mark TP1 hit for trade {trade_id}: {e}")
            return False
    
    async def move_trade_to_history(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        close_reason: str
    ) -> bool:
        """Move trade from active_trades to trade_history."""
        try:
            async with self.pool.acquire() as conn:
                # Get trade details
                trade = await conn.fetchrow(
                    "SELECT * FROM active_trades WHERE trade_id = $1",
                    trade_id
                )
                
                if not trade:
                    logger.warning(f"Trade {trade_id} not found in active_trades")
                    return False
                
                # Insert into history
                await conn.execute(
                    """
                    INSERT INTO trade_history (
                        account_key, channel_id, signal_id, sub_signal_id,
                        symbol, direction, entry_price, exit_price,
                        sl, tp, lot_size, entry_time, exit_time,
                        pnl, outcome, close_reason
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), $13, $14, $15)
                    """,
                    trade['account_key'], trade['channel_id'], trade['signal_id'],
                    trade['sub_signal_id'], trade['symbol'], trade['direction'],
                    trade['entry_price'], exit_price, trade['sl'], trade['tp'],
                    trade['lot_size'], trade['entry_time'], pnl,
                    'WIN' if pnl > 0 else ('LOSS' if pnl < 0 else 'BE'),
                    close_reason
                )
                
                # Remove from active_trades
                await conn.execute(
                    "DELETE FROM active_trades WHERE trade_id = $1",
                    trade_id
                )
                
                logger.info(f"✓ Moved trade {trade_id} to history (P&L: ${pnl:.2f})")
                return True
        except Exception as e:
            logger.error(f"Failed to move trade {trade_id} to history: {e}")
            return False
    
    async def remove_active_trade(self, trade_id: int) -> bool:
        """Remove trade from active_trades (for cancelled orders)."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM active_trades WHERE trade_id = $1",
                    trade_id
                )
                logger.debug(f"✓ Removed trade {trade_id} from active_trades")
                return True
        except Exception as e:
            logger.error(f"Failed to remove trade {trade_id}: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_db() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.connect()
    return _db_manager
