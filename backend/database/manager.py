# -*- coding: utf-8 -*-
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
from ..core.secret_vault import get_vault


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
    
    async def execute_raw(self, query: str, *args):
        """
        Execute a raw SQL query.
        
        Args:
            query: SQL query string
            *args: Query parameters
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)
    
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
            
            # Migration: Add tl_prop_firm column if it doesn't exist
            try:
                column_exists = await conn.fetchval("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='accounts' 
                    AND column_name='tl_prop_firm'
                """)
                
                if not column_exists:
                    await conn.execute("""
                        ALTER TABLE accounts 
                        ADD COLUMN tl_prop_firm TEXT NOT NULL DEFAULT ''
                    """)
                    logger.info("✓ Added tl_prop_firm column to accounts table")
            except Exception as e:
                logger.debug(f"Migration check: {e}")
            
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
    
    async def get_risk_profiles_by_user(self, user_id: str, is_super_admin: bool = False) -> List[RiskProfile]:
        """Get risk profiles for user. Returns default + user's custom profiles."""
        async with self.pool.acquire() as conn:
            if is_super_admin:
                rows = await conn.fetch("SELECT * FROM risk_profiles ORDER BY profile_name")
            else:
                # Get default profile + user's custom profiles
                rows = await conn.fetch(
                    """
                    SELECT * FROM risk_profiles 
                    WHERE is_default = TRUE OR user_id = $1
                    ORDER BY profile_name
                    """,
                    user_id
                )
            return [RiskProfile(**dict(row)) for row in rows]
    
    async def verify_risk_profile_access(
        self, profile_id: int, user_id: str, is_super_admin: bool = False
    ) -> bool:
        """Verify user can access risk profile (default or owned by user or is admin)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT is_default, user_id FROM risk_profiles WHERE profile_id = $1",
                profile_id
            )
            if not row:
                return False
            if is_super_admin or row['is_default']:
                return True
            return row['user_id'] == user_id
    
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
    
    # ==================== USER QUERIES ====================
    
    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by Firebase UID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )
            return dict(row) if row else None
    
    async def create_user(
        self,
        user_id: str,
        email: str,
        is_super_admin: bool = False,
        is_approved: bool = False
    ) -> bool:
        """Create a new user."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (user_id, email, is_super_admin, is_approved)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    user_id, email, is_super_admin, is_approved
                )
                logger.info(f"✓ Created user: {email} (admin={is_super_admin}, approved={is_approved})")
                return True
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    async def approve_user(self, user_id: str) -> bool:
        """Approve a user."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET is_approved = TRUE WHERE user_id = $1",
                    user_id
                )
                logger.info(f"✓ Approved user: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to approve user: {e}")
            return False
    
    async def get_all_users(self) -> List[dict]:
        """Get all users (admin only)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
            return [dict(row) for row in rows]
    
    async def get_pending_users(self) -> List[dict]:
        """Get all pending approval users."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM users WHERE is_approved = FALSE ORDER BY created_at"
            )
            return [dict(row) for row in rows]
    
    async def update_user_fcm_token(self, user_id: str, fcm_token: str) -> bool:
        """Update user's FCM token for push notifications."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET fcm_token = $1 WHERE user_id = $2",
                    fcm_token, user_id
                )
                logger.debug(f"✓ Updated FCM token for user: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update FCM token: {e}")
            return False
    
    async def get_users_by_account(self, account_key: str) -> List[dict]:
        """Get all users who own a specific account."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM accounts WHERE account_key = $1",
                    account_key
                )
                if not rows:
                    return []
                user_ids = [dict(row)['user_id'] for row in rows if dict(row).get('user_id')]
                if not user_ids:
                    return []
                users = await conn.fetch(
                    "SELECT * FROM users WHERE user_id = ANY($1::text[])",
                    user_ids
                )
                return [dict(row) for row in users]
        except Exception as e:
            logger.error(f"Failed to get users by account: {e}")
            return []
    
    async def get_all_users_with_fcm(self) -> List[dict]:
        """Get all users who have FCM tokens registered."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM users WHERE fcm_token IS NOT NULL"
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get users with FCM tokens: {e}")
            return []
    
    # ==================== ACCOUNT QUERIES ====================
    
    async def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        vault = get_vault()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM accounts")
            accounts = []
            for row in rows:
                account_dict = dict(row)
                # Decrypt password
                try:
                    account_dict['tl_password'] = vault.decrypt(account_dict['tl_password'])
                except Exception as e:
                    logger.warning(f"Failed to decrypt password for {account_dict['account_key']}: {e}")
                accounts.append(Account(**account_dict))
            return accounts
    
    async def get_accounts_by_user(self, user_id: str, is_super_admin: bool = False) -> List[Account]:
        """Get accounts filtered by user_id. Super admin sees all."""
        vault = get_vault()
        async with self.pool.acquire() as conn:
            if is_super_admin:
                rows = await conn.fetch("SELECT * FROM accounts")
            else:
                rows = await conn.fetch(
                    "SELECT * FROM accounts WHERE user_id = $1", user_id
                )
            accounts = []
            for row in rows:
                account_dict = dict(row)
                # Decrypt password
                try:
                    account_dict['tl_password'] = vault.decrypt(account_dict['tl_password'])
                except Exception as e:
                    logger.warning(f"Failed to decrypt password for {account_dict['account_key']}: {e}")
                accounts.append(Account(**account_dict))
            return accounts
    
    async def get_account(self, account_key: str) -> Optional[Account]:
        """Get account by key."""
        vault = get_vault()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM accounts WHERE account_key = $1", account_key
            )
            if not row:
                return None
            account_dict = dict(row)
            # Decrypt password
            try:
                account_dict['tl_password'] = vault.decrypt(account_dict['tl_password'])
            except Exception as e:
                logger.warning(f"Failed to decrypt password for {account_key}: {e}")
            return Account(**account_dict)
    
    async def verify_account_ownership(
        self, account_key: str, user_id: str, is_super_admin: bool = False
    ) -> bool:
        """Verify that user owns account or is super admin."""
        if is_super_admin:
            return True
        async with self.pool.acquire() as conn:
            owner_id = await conn.fetchval(
                "SELECT user_id FROM accounts WHERE account_key = $1", account_key
            )
            return owner_id == user_id if owner_id else False
    
    async def add_account(self, account: Account, user_id: Optional[str] = None) -> bool:
        """Add a new account."""
        try:
            # Encrypt password before storing
            vault = get_vault()
            encrypted_password = vault.encrypt(account.tl_password)
            
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO accounts (
                        account_key, credential_key, tl_account_id,
                        tl_email, tl_password, tl_server, tl_prop_firm, display_name,
                        initial_balance, current_balance, highest_banked_balance,
                        daily_start_balance, last_synced_balance, cycle_start_date,
                        user_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    """,
                    account.account_key, account.credential_key, account.tl_account_id,
                    account.tl_email, encrypted_password, account.tl_server,
                    account.tl_prop_firm, account.display_name, account.initial_balance, account.current_balance,
                    account.initial_balance,  # highest_banked_balance starts at initial
                    account.current_balance,  # daily_start_balance
                    account.current_balance,  # last_synced_balance
                    account.cycle_start_date or datetime.now().date(),
                    user_id
                )
                
                # Auto-subscribe to all enabled channels
                await conn.execute(
                    """
                    INSERT INTO channel_subscriptions (account_key, channel_id, enabled)
                    SELECT $1, channel_id, TRUE
                    FROM channels
                    WHERE enabled = TRUE
                    ON CONFLICT (account_key, channel_id) DO NOTHING
                    """,
                    account.account_key
                )
                
                logger.info(f"✓ Added account: {account.account_key} (user: {user_id})")
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
    
    async def update_account_profit_locked(self, account_key: str, locked: bool) -> bool:
        """Update account profit_locked status."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE accounts SET profit_locked = $1 WHERE account_key = $2",
                    locked, account_key
                )
                logger.info(f"✓ Account {account_key} profit_locked={locked}")
                return True
        except Exception as e:
            logger.error(f"Failed to update account profit_locked: {e}")
            return False
    
    async def update_account(self, account_key: str, **kwargs) -> bool:
        """
        Update account with flexible field updates.
        
        Args:
            account_key: Account identifier
            **kwargs: Fields to update (e.g., current_balance=100.0, last_synced_balance=100.0)
        
        Returns:
            True if successful, False otherwise
        """
        if not kwargs:
            logger.warning("update_account called with no fields to update")
            return False
        
        try:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            param_num = 1
            
            for field, value in kwargs.items():
                set_clauses.append(f"{field} = ${param_num}")
                values.append(value)
                param_num += 1
            
            # Add account_key as final parameter
            values.append(account_key)
            
            query = f"""
                UPDATE accounts
                SET {', '.join(set_clauses)}
                WHERE account_key = ${param_num}
            """
            
            async with self.pool.acquire() as conn:
                await conn.execute(query, *values)
                logger.debug(f"✓ Updated account {account_key}: {', '.join(kwargs.keys())}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update account {account_key}: {e}")
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
    
    async def get_active_trades_by_account_and_channel(
        self, account_key: str, channel_id: int
    ) -> List[ActiveTrade]:
        """
        Get all active trades for a specific account and channel (for context matching).
        Used by management action context matchers to find trades for specific account.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM active_trades WHERE account_key = $1 AND channel_id = $2 AND status = 'filled'",
                account_key, channel_id
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
    
    # ==================== TRADE HISTORY QUERIES ====================
    
    async def get_trade_history(
        self,
        account_key: Optional[str] = None,
        user_id: Optional[str] = None,
        is_super_admin: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get trade history with optional filtering.
        
        Args:
            account_key: Optional account filter
            user_id: User ID for filtering (regular users only see their trades)
            is_super_admin: If True, sees all trades
            limit: Maximum number of records to return
            offset: Offset for pagination
        
        Returns:
            List of trade history records
        """
        try:
            async with self.pool.acquire() as conn:
                if is_super_admin:
                    # Super admin sees all
                    if account_key:
                        rows = await conn.fetch(
                            """
                            SELECT * FROM trade_history
                            WHERE account_key = $1
                            ORDER BY exit_time DESC
                            LIMIT $2 OFFSET $3
                            """,
                            account_key, limit, offset
                        )
                    else:
                        rows = await conn.fetch(
                            """
                            SELECT * FROM trade_history
                            ORDER BY exit_time DESC
                            LIMIT $1 OFFSET $2
                            """,
                            limit, offset
                        )
                else:
                    # Regular user - filter by their accounts
                    if account_key:
                        rows = await conn.fetch(
                            """
                            SELECT th.* FROM trade_history th
                            JOIN accounts a ON th.account_key = a.account_key
                            WHERE th.account_key = $1 AND a.user_id = $2
                            ORDER BY th.exit_time DESC
                            LIMIT $3 OFFSET $4
                            """,
                            account_key, user_id, limit, offset
                        )
                    else:
                        rows = await conn.fetch(
                            """
                            SELECT th.* FROM trade_history th
                            JOIN accounts a ON th.account_key = a.account_key
                            WHERE a.user_id = $1
                            ORDER BY th.exit_time DESC
                            LIMIT $2 OFFSET $3
                            """,
                            user_id, limit, offset
                        )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            return []
    
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
    
    async def update_trade_position_id(self, trade_id: int, position_id: str) -> bool:
        """Update TradeLocker position_id for an active trade."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE active_trades SET tl_position_id = $1 WHERE trade_id = $2",
                    position_id, trade_id
                )
                logger.debug(f"✓ Updated position_id for trade {trade_id}: {position_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update position_id for trade {trade_id}: {e}")
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
    
    async def update_trade_current_pnl(self, trade_id: int, current_pnl: float) -> bool:
        """
        Update current unrealized PnL for an active trade.
        Called by LivePnLUpdater background service.
        
        Args:
            trade_id: Trade ID
            current_pnl: Current unrealized P&L from TradeLocker
        
        Returns:
            True if successful
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE active_trades SET current_pnl = $1 WHERE trade_id = $2",
                    current_pnl, trade_id
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update current PnL for trade {trade_id}: {e}")
            return False
    
    async def move_trade_to_history(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        close_reason: str,
        outcome: Optional[str] = None,
        manual_action_type: Optional[str] = None
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
                
                # Calculate outcome if not provided
                if outcome is None:
                    outcome = 'WIN' if pnl > 0 else ('LOSS' if pnl < 0 else 'BE')
                
                # Insert into history
                await conn.execute(
                    """
                    INSERT INTO trade_history (
                        account_key, channel_id, signal_id, sub_signal_id,
                        symbol, direction, entry_price, exit_price,
                        sl, tp, lot_size, entry_time, exit_time,
                        pnl, outcome, close_reason, manual_action_type
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), $13, $14, $15, $16)
                    """,
                    trade['account_key'], trade['channel_id'], trade['signal_id'],
                    trade['sub_signal_id'], trade['symbol'], trade['direction'],
                    trade['entry_price'], exit_price, trade['sl'], trade['tp'],
                    trade['lot_size'], trade['entry_time'], pnl,
                    outcome,
                    close_reason,
                    manual_action_type
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
    
    # ==================== ADDITIONAL ACCOUNT METHODS ====================
    
    async def update_account_display_name(self, account_key: str, display_name: str) -> bool:
        """Update account display name."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE accounts SET display_name = $1 WHERE account_key = $2",
                    display_name, account_key
                )
                logger.info(f"✓ Updated display name for {account_key}")
                return True
        except Exception as e:
            logger.error(f"Failed to update display name for {account_key}: {e}")
            return False
    
    async def update_account_risk_profile(self, account_key: str, risk_profile_id: int) -> bool:
        """Update account risk profile."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE accounts SET risk_profile_id = $1 WHERE account_key = $2",
                    risk_profile_id, account_key
                )
                logger.info(f"✓ Updated risk profile for {account_key} to {risk_profile_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update risk profile for {account_key}: {e}")
            return False
    
    async def update_account_max_concurrent(self, account_key: str, max_concurrent: Optional[int]) -> bool:
        """Update account max concurrent trades override."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE accounts SET max_concurrent_trades_override = $1 WHERE account_key = $2",
                    max_concurrent, account_key
                )
                logger.info(f"✓ Updated max concurrent for {account_key} to {max_concurrent}")
                return True
        except Exception as e:
            logger.error(f"Failed to update max concurrent for {account_key}: {e}")
            return False
    
    async def delete_account(self, account_key: str) -> bool:
        """Delete an account and all related data."""
        try:
            async with self.pool.acquire() as conn:
                # Delete in order (foreign key constraints)
                await conn.execute("DELETE FROM channel_subscriptions WHERE account_key = $1", account_key)
                await conn.execute("DELETE FROM active_trades WHERE account_key = $1", account_key)
                await conn.execute("DELETE FROM trade_history WHERE account_key = $1", account_key)
                await conn.execute("DELETE FROM profitable_days WHERE account_key = $1", account_key)
                await conn.execute("DELETE FROM accounts WHERE account_key = $1", account_key)
                
                logger.info(f"✓ Deleted account {account_key} and all related data")
                return True
        except Exception as e:
            logger.error(f"Failed to delete account {account_key}: {e}")
            return False
    
    async def reset_payout_after_withdrawal(
        self,
        account_key: str,
        new_balance: float
    ) -> bool:
        """
        Reset account after payout withdrawal.
        
        This is called after a trader withdraws profits and wants to reset
        the account to start fresh with the new balance.
        
        Updates:
        - initial_balance = new_balance
        - current_balance = new_balance
        - highest_banked_balance = new_balance
        - daily_start_balance = new_balance
        - last_synced_balance = new_balance
        - profit_locked = False
        - cycle_start_date = today
        - cycle_best_day_pnl = 0.0
        """
        try:
            async with self.pool.acquire() as conn:
                today = datetime.now().date().isoformat()
                
                await conn.execute(
                    """
                    UPDATE accounts SET
                        initial_balance = $1,
                        current_balance = $1,
                        highest_banked_balance = $1,
                        daily_start_balance = $1,
                        last_synced_balance = $1,
                        profit_locked = FALSE,
                        cycle_start_date = $2,
                        cycle_best_day_pnl = 0.0
                    WHERE account_key = $3
                    """,
                    new_balance, today, account_key
                )
                
                logger.info(
                    f"✓ Reset payout for {account_key}: "
                    f"new balance ${new_balance:.2f}, cycle start {today}"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to reset payout for {account_key}: {e}")
            return False
    
    # ==================== RISK PROFILE CRUD METHODS ====================
    
    async def add_risk_profile(self, profile: RiskProfile, user_id: Optional[str] = None) -> Optional[int]:
        """Add a new risk profile. Returns profile_id."""
        try:
            async with self.pool.acquire() as conn:
                profile_id = await conn.fetchval(
                    """
                    INSERT INTO risk_profiles (
                        profile_name, is_default,
                        max_risk_per_trade_pct, daily_loss_pct, daily_trailing,
                        overall_loss_pct, overall_trailing, overall_trail_from_closed_balance,
                        profit_lock_pct, profit_lock_floor_pct, payout_buffer_pct,
                        max_concurrent_trades, commission_per_lot, safety_buffer_pct, notes,
                        user_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    RETURNING profile_id
                    """,
                    profile.profile_name, profile.is_default,
                    profile.max_risk_per_trade_pct, profile.daily_loss_pct, profile.daily_trailing,
                    profile.overall_loss_pct, profile.overall_trailing, profile.overall_trail_from_closed_balance,
                    profile.profit_lock_pct, profile.profit_lock_floor_pct, profile.payout_buffer_pct,
                    profile.max_concurrent_trades, profile.commission_per_lot, profile.safety_buffer_pct,
                    profile.notes,
                    user_id
                )
                
                logger.info(f"✓ Created risk profile: {profile.profile_name} (ID: {profile_id}, user: {user_id})")
                return profile_id
        except Exception as e:
            logger.error(f"Failed to create risk profile: {e}")
            return None
    
    async def update_risk_profile(self, profile_id: int, profile: RiskProfile) -> bool:
        """Update an existing risk profile."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE risk_profiles SET
                        profile_name = $1,
                        is_default = $2,
                        max_risk_per_trade_pct = $3,
                        daily_loss_pct = $4,
                        daily_trailing = $5,
                        overall_loss_pct = $6,
                        overall_trailing = $7,
                        overall_trail_from_closed_balance = $8,
                        profit_lock_pct = $9,
                        profit_lock_floor_pct = $10,
                        payout_buffer_pct = $11,
                        max_concurrent_trades = $12,
                        commission_per_lot = $13,
                        safety_buffer_pct = $14,
                        notes = $15
                    WHERE profile_id = $16
                    """,
                    profile.profile_name, profile.is_default,
                    profile.max_risk_per_trade_pct, profile.daily_loss_pct, profile.daily_trailing,
                    profile.overall_loss_pct, profile.overall_trailing, profile.overall_trail_from_closed_balance,
                    profile.profit_lock_pct, profile.profit_lock_floor_pct, profile.payout_buffer_pct,
                    profile.max_concurrent_trades, profile.commission_per_lot, profile.safety_buffer_pct,
                    profile.notes, profile_id
                )
                
                logger.info(f"✓ Updated risk profile ID {profile_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update risk profile {profile_id}: {e}")
            return False
    
    async def delete_risk_profile(self, profile_id: int) -> bool:
        """Delete a risk profile (only if not in use and not default)."""
        try:
            async with self.pool.acquire() as conn:
                # Check if it's the default profile
                is_default = await conn.fetchval(
                    "SELECT is_default FROM risk_profiles WHERE profile_id = $1",
                    profile_id
                )
                
                if is_default:
                    logger.warning(f"Cannot delete default risk profile {profile_id}")
                    return False
                
                # Check if any accounts are using it
                account_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM accounts WHERE risk_profile_id = $1",
                    profile_id
                )
                
                if account_count > 0:
                    logger.warning(
                        f"Cannot delete risk profile {profile_id}: "
                        f"{account_count} account(s) are using it"
                    )
                    return False
                
                # Safe to delete
                await conn.execute(
                    "DELETE FROM risk_profiles WHERE profile_id = $1",
                    profile_id
                )
                
                logger.info(f"✓ Deleted risk profile ID {profile_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete risk profile {profile_id}: {e}")
            return False
    
    # ==================== CHANNEL UPDATE METHODS ====================
    
    async def update_channel(self, channel_id: int, channel: Channel) -> bool:
        """Update an existing channel."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE channels SET
                        display_name = $1,
                        signal_prefix = $2,
                        entry_logic_module = $3,
                        management_logic_module = $4,
                        priority = $5,
                        enabled = $6,
                        notes = $7
                    WHERE channel_id = $8
                    """,
                    channel.display_name, channel.signal_prefix,
                    channel.entry_logic_module, channel.management_logic_module,
                    channel.priority, channel.enabled, channel.notes,
                    channel_id
                )
                
                logger.info(f"✓ Updated channel {channel_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update channel {channel_id}: {e}")
            return False
    
    async def delete_channel(self, channel_id: int) -> bool:
        """Delete a channel and all related data."""
        try:
            async with self.pool.acquire() as conn:
                # Delete in order (foreign key constraints)
                await conn.execute("DELETE FROM channel_subscriptions WHERE channel_id = $1", channel_id)
                await conn.execute("DELETE FROM active_trades WHERE channel_id = $1", channel_id)
                await conn.execute("DELETE FROM trade_history WHERE channel_id = $1", channel_id)
                await conn.execute("DELETE FROM waiting_room WHERE channel_id = $1", channel_id)
                await conn.execute("DELETE FROM message_cache WHERE channel_id = $1", channel_id)
                await conn.execute("DELETE FROM channels WHERE channel_id = $1", channel_id)
                
                logger.info(f"✓ Deleted channel {channel_id} and all related data")
                return True
        except Exception as e:
            logger.error(f"Failed to delete channel {channel_id}: {e}")
            return False
    
    # ==================== BOT SETTINGS METHODS ====================
    
    async def get_bot_setting(self, setting_key: str) -> Optional[str]:
        """
        Get a bot setting value.
        
        Args:
            setting_key: Setting key (e.g., 'allow_weekend_trading')
        
        Returns:
            Setting value as string, or None if not found
        """
        try:
            async with self.pool.acquire() as conn:
                value = await conn.fetchval(
                    "SELECT setting_value FROM bot_settings WHERE setting_key = $1",
                    setting_key
                )
                return value
        except Exception as e:
            logger.error(f"Failed to get bot setting {setting_key}: {e}")
            return None
    
    async def set_bot_setting(self, setting_key: str, setting_value: str) -> bool:
        """
        Set a bot setting value.
        
        Args:
            setting_key: Setting key
            setting_value: Setting value as string
        
        Returns:
            True if successful
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO bot_settings (setting_key, setting_value)
                    VALUES ($1, $2)
                    ON CONFLICT (setting_key)
                    DO UPDATE SET setting_value = $2, updated_at = CURRENT_TIMESTAMP
                    """,
                    setting_key, setting_value
                )
                logger.info(f"✓ Set bot setting: {setting_key} = {setting_value}")
                return True
        except Exception as e:
            logger.error(f"Failed to set bot setting {setting_key}: {e}")
            return False
    
    async def get_all_bot_settings(self) -> Dict[str, str]:
        """
        Get all bot settings.
        
        Returns:
            Dictionary of setting_key → setting_value
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT setting_key, setting_value FROM bot_settings")
                return {row['setting_key']: row['setting_value'] for row in rows}
        except Exception as e:
            logger.error(f"Failed to get bot settings: {e}")
            return {}
    
    # ==================== NOTIFICATION QUERIES ====================
    
    async def add_notification(
        self,
        account_key: Optional[str],
        category: str,
        severity: str,
        title: str,
        message: str,
        metadata: Optional[Dict] = None
    ) -> Optional[int]:
        """Add a new notification. Returns notification_id."""
        try:
            # Convert metadata dict to JSON string if provided
            import json
            metadata_json = json.dumps(metadata) if metadata else None
            
            async with self.pool.acquire() as conn:
                notification_id = await conn.fetchval(
                    """
                    INSERT INTO notifications (
                        account_key, category, severity, title, message, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING notification_id
                    """,
                    account_key, category, severity, title, message, metadata_json
                )
                logger.debug(f"✓ Added notification: {title}")
                return notification_id
        except Exception as e:
            logger.error(f"Failed to add notification: {e}")
            return None
    
    async def get_notifications(
        self,
        account_key: Optional[str] = None,
        user_id: Optional[str] = None,
        is_super_admin: bool = False,
        unread_only: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get notifications with optional filtering and user isolation.
        Regular users only see notifications for their accounts.
        Super admin sees all notifications.
        """
        try:
            async with self.pool.acquire() as conn:
                # Super admin sees all notifications
                if is_super_admin:
                    if account_key:
                        if unread_only:
                            rows = await conn.fetch(
                                """
                                SELECT * FROM notifications
                                WHERE account_key = $1 AND read = FALSE
                                ORDER BY created_at DESC
                                LIMIT $2
                                """,
                                account_key, limit
                            )
                        else:
                            rows = await conn.fetch(
                                """
                                SELECT * FROM notifications
                                WHERE account_key = $1
                                ORDER BY created_at DESC
                                LIMIT $2
                                """,
                                account_key, limit
                            )
                    else:
                        if unread_only:
                            rows = await conn.fetch(
                                """
                                SELECT * FROM notifications
                                WHERE read = FALSE
                                ORDER BY created_at DESC
                                LIMIT $1
                                """,
                                limit
                            )
                        else:
                            rows = await conn.fetch(
                                """
                                SELECT * FROM notifications
                                ORDER BY created_at DESC
                                LIMIT $1
                                """,
                                limit
                            )
                # Regular users - filter by their accounts only
                else:
                    # Get user's account keys
                    user_accounts = await conn.fetch(
                        "SELECT account_key FROM accounts WHERE user_id = $1",
                        user_id
                    )
                    account_keys = [row['account_key'] for row in user_accounts]
                    
                    if not account_keys:
                        return []  # User has no accounts
                    
                    if account_key:
                        # Specific account requested - verify it belongs to user
                        if account_key not in account_keys:
                            return []  # Access denied
                        
                        if unread_only:
                            rows = await conn.fetch(
                                """
                                SELECT * FROM notifications
                                WHERE account_key = $1 AND read = FALSE
                                ORDER BY created_at DESC
                                LIMIT $2
                                """,
                                account_key, limit
                            )
                        else:
                            rows = await conn.fetch(
                                """
                                SELECT * FROM notifications
                                WHERE account_key = $1
                                ORDER BY created_at DESC
                                LIMIT $2
                                """,
                                account_key, limit
                            )
                    else:
                        # All notifications for user's accounts
                        if unread_only:
                            rows = await conn.fetch(
                                """
                                SELECT * FROM notifications
                                WHERE (account_key = ANY($1) OR account_key IS NULL) AND read = FALSE
                                ORDER BY created_at DESC
                                LIMIT $2
                                """,
                                account_keys, limit
                            )
                        else:
                            rows = await conn.fetch(
                                """
                                SELECT * FROM notifications
                                WHERE account_key = ANY($1) OR account_key IS NULL
                                ORDER BY created_at DESC
                                LIMIT $2
                                """,
                                account_keys, limit
                            )
                
                # Parse metadata JSON strings back to dicts
                import json
                result = []
                for row in rows:
                    row_dict = dict(row)
                    if row_dict.get('metadata') and isinstance(row_dict['metadata'], str):
                        try:
                            row_dict['metadata'] = json.loads(row_dict['metadata'])
                        except:
                            row_dict['metadata'] = {}
                    result.append(row_dict)
                
                return result
        except Exception as e:
            logger.error(f"Failed to get notifications: {e}")
            return []
    
    async def get_notification(self, notification_id: int) -> Optional[Dict]:
        """Get a single notification by ID."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM notifications WHERE notification_id = $1",
                    notification_id
                )
                if not row:
                    return None
                
                # Parse metadata JSON string back to dict
                import json
                row_dict = dict(row)
                if row_dict.get('metadata') and isinstance(row_dict['metadata'], str):
                    try:
                        row_dict['metadata'] = json.loads(row_dict['metadata'])
                    except:
                        row_dict['metadata'] = {}
                
                return row_dict
        except Exception as e:
            logger.error(f"Failed to get notification {notification_id}: {e}")
            return None
    
    async def mark_notification_read(self, notification_id: int, read: bool) -> bool:
        """Mark a notification as read or unread."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE notifications SET read = $1 WHERE notification_id = $2",
                    read, notification_id
                )
                return True
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return False
    
    async def mark_all_notifications_read(
        self,
        account_key: Optional[str] = None,
        user_id: Optional[str] = None,
        is_super_admin: bool = False
    ) -> int:
        """
        Mark all notifications as read with user isolation.
        Regular users can only mark their own account notifications as read.
        Super admin can mark all as read.
        """
        try:
            async with self.pool.acquire() as conn:
                # Super admin can mark all as read
                if is_super_admin:
                    if account_key:
                        result = await conn.execute(
                            "UPDATE notifications SET read = TRUE WHERE account_key = $1 AND read = FALSE",
                            account_key
                        )
                    else:
                        result = await conn.execute(
                            "UPDATE notifications SET read = TRUE WHERE read = FALSE"
                        )
                # Regular users - filter by their accounts only
                else:
                    # Get user's account keys
                    user_accounts = await conn.fetch(
                        "SELECT account_key FROM accounts WHERE user_id = $1",
                        user_id
                    )
                    account_keys = [row['account_key'] for row in user_accounts]
                    
                    if not account_keys:
                        return 0  # User has no accounts
                    
                    if account_key:
                        # Specific account - verify ownership
                        if account_key not in account_keys:
                            return 0  # Access denied
                        
                        result = await conn.execute(
                            "UPDATE notifications SET read = TRUE WHERE account_key = $1 AND read = FALSE",
                            account_key
                        )
                    else:
                        # All notifications for user's accounts
                        result = await conn.execute(
                            """
                            UPDATE notifications SET read = TRUE 
                            WHERE (account_key = ANY($1) OR account_key IS NULL) AND read = FALSE
                            """,
                            account_keys
                        )
                
                # Extract count from result string like "UPDATE 5"
                count = int(result.split()[-1]) if result else 0
                logger.info(f"✓ Marked {count} notification(s) as read")
                return count
        except Exception as e:
            logger.error(f"Failed to mark all notifications as read: {e}")
            return 0
    
    async def delete_notification(self, notification_id: int) -> bool:
        """Delete a notification."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM notifications WHERE notification_id = $1",
                    notification_id
                )
                return True
        except Exception as e:
            logger.error(f"Failed to delete notification: {e}")
            return False
    
    async def cleanup_old_notifications(self) -> int:
        """Delete notifications older than 48 hours. Returns count of deleted notifications."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM notifications WHERE created_at < NOW() - INTERVAL '48 hours'"
                )
                count = int(result.split()[-1]) if result else 0
                if count > 0:
                    logger.info(f"✓ Cleaned up {count} old notification(s)")
                return count
        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {e}")
            return 0
    
    # ==================== MANUAL ACTION QUERIES ====================
    
    async def add_manual_action(
        self,
        account_key: str,
        trade_id: Optional[int],
        action_type: str,
        action_data: Optional[Dict] = None
    ) -> Optional[int]:
        """Add a manual action audit record. Returns action_id."""
        try:
            # Convert action_data dict to JSON string for PostgreSQL
            import json
            action_data_json = json.dumps(action_data) if action_data else None
            
            async with self.pool.acquire() as conn:
                action_id = await conn.fetchval(
                    """
                    INSERT INTO manual_actions (
                        account_key, trade_id, action_type, action_data
                    ) VALUES ($1, $2, $3, $4)
                    RETURNING action_id
                    """,
                    account_key, trade_id, action_type, action_data_json
                )
                logger.debug(f"✓ Logged manual action: {action_type}")
                return action_id
        except Exception as e:
            logger.error(f"Failed to add manual action: {e}")
            return None
    
    async def get_manual_actions(
        self,
        account_key: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get manual action history."""
        try:
            import json
            async with self.pool.acquire() as conn:
                if account_key:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM manual_actions
                        WHERE account_key = $1
                        ORDER BY performed_at DESC
                        LIMIT $2
                        """,
                        account_key, limit
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM manual_actions
                        ORDER BY performed_at DESC
                        LIMIT $1
                        """,
                        limit
                    )
                
                # Parse action_data JSON string back to dict
                result = []
                for row in rows:
                    row_dict = dict(row)
                    if row_dict.get('action_data'):
                        try:
                            row_dict['action_data'] = json.loads(row_dict['action_data'])
                        except:
                            row_dict['action_data'] = {}
                    result.append(row_dict)
                
                return result
        except Exception as e:
            logger.error(f"Failed to get manual actions: {e}")
            return []
    
    # ==================== HELPER METHODS FOR NEW FEATURES ====================
    
    async def get_active_trade_by_id(self, trade_id: int) -> Optional[ActiveTrade]:
        """Get a single active trade by ID."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM active_trades WHERE trade_id = $1",
                    trade_id
                )
                return ActiveTrade(**dict(row)) if row else None
        except Exception as e:
            logger.error(f"Failed to get active trade {trade_id}: {e}")
            return None
    
    async def update_channel(self, channel_id: int, **kwargs) -> bool:
        """Update channel with flexible field updates."""
        if not kwargs:
            return False
        
        try:
            set_clauses = []
            values = []
            param_num = 1
            
            for field, value in kwargs.items():
                set_clauses.append(f"{field} = ${param_num}")
                values.append(value)
                param_num += 1
            
            values.append(channel_id)
            query = f"""
                UPDATE channels
                SET {', '.join(set_clauses)}
                WHERE channel_id = ${param_num}
            """
            
            async with self.pool.acquire() as conn:
                await conn.execute(query, *values)
                logger.debug(f"✓ Updated channel {channel_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update channel: {e}")
            return False
    
    async def update_risk_profile(self, profile_id: int, **kwargs) -> bool:
        """Update risk profile with flexible field updates."""
        if not kwargs:
            return False
        
        try:
            set_clauses = []
            values = []
            param_num = 1
            
            for field, value in kwargs.items():
                set_clauses.append(f"{field} = ${param_num}")
                values.append(value)
                param_num += 1
            
            values.append(profile_id)
            query = f"""
                UPDATE risk_profiles
                SET {', '.join(set_clauses)}
                WHERE profile_id = ${param_num}
            """
            
            async with self.pool.acquire() as conn:
                await conn.execute(query, *values)
                logger.debug(f"✓ Updated risk profile {profile_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update risk profile: {e}")
            return False
    
    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE user_id = $1",
                    user_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def create_user(
        self,
        user_id: str,
        email: str,
        display_name: Optional[str] = None,
        is_super_admin: bool = False
    ) -> Optional[dict]:
        """Create new user (pending approval by default)."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (user_id, email, display_name, is_super_admin, is_approved)
                    VALUES ($1, $2, $3, $4, FALSE)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET email = $2, display_name = $3
                    RETURNING *
                    """,
                    user_id, email, display_name, is_super_admin
                )
                logger.info(f"✓ Created/updated user: {email}")
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
    
    async def approve_user(self, user_id: str) -> bool:
        """Approve user (super admin only)."""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE users SET is_approved = TRUE WHERE user_id = $1",
                    user_id
                )
                success = result == "UPDATE 1"
                if success:
                    logger.info(f"✓ Approved user: {user_id}")
                return success
        except Exception as e:
            logger.error(f"Failed to approve user: {e}")
            return False
    
    async def get_all_users(self) -> List[dict]:
        """Get all users (super admin only)."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get users: {e}")
            return []
    
    async def get_pending_users(self) -> List[dict]:
        """Get users pending approval."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM users WHERE is_approved = FALSE ORDER BY created_at DESC"
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get pending users: {e}")
            return []


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.connect()
    return _db_manager
