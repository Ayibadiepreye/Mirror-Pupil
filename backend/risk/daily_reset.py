"""
Mirror Pupil v5.1 - Daily Reset Handler
Handles 5pm EST daily reset logic.
"""

import asyncio
from datetime import datetime, time, date
from typing import Optional, TYPE_CHECKING
import pytz
from loguru import logger

from ..database.models import Account, ProfitableDay

if TYPE_CHECKING:
    from ..database import DatabaseManager


class DailyResetHandler:
    """
    Handles daily reset at 5pm EST.
    
    Responsibilities:
    - Set new daily_start_balance (static floor reference)
    - Update cycle_best_day_pnl if today was better
    - Record profitable day
    - Reset daily_pnl to 0
    """
    
    def __init__(self, db: "DatabaseManager"):
        self.db = db
        self.reset_task: Optional[asyncio.Task] = None
        self.timezone = pytz.timezone("America/New_York")  # EST/EDT
        
        logger.info("Initialized DailyResetHandler")
    
    async def start_daily_reset_scheduler(self):
        """Start background task that runs daily reset at 5pm EST."""
        if self.reset_task:
            logger.warning("Daily reset scheduler already running")
            return
        
        self.reset_task = asyncio.create_task(self._daily_reset_loop())
        logger.info("✓ Started daily reset scheduler (5pm EST)")
    
    async def stop_daily_reset_scheduler(self):
        """Stop daily reset scheduler."""
        if self.reset_task:
            self.reset_task.cancel()
            try:
                await self.reset_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped daily reset scheduler")
    
    async def _daily_reset_loop(self):
        """Background task that waits for 5pm EST and runs reset."""
        while True:
            try:
                # Calculate time until next 5pm EST
                now = datetime.now(self.timezone)
                target_time = time(17, 0, 0)  # 5:00 PM
                
                # Create target datetime for today at 5pm
                target = self.timezone.localize(
                    datetime.combine(now.date(), target_time)
                )
                
                # If we've passed 5pm today, target tomorrow
                if now >= target:
                    from datetime import timedelta
                    target = target + timedelta(days=1)
                
                # Calculate seconds until target
                wait_seconds = (target - now).total_seconds()
                
                logger.info(
                    f"Next daily reset scheduled for {target.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                    f"({wait_seconds/3600:.1f} hours)"
                )
                
                # Wait until 5pm
                await asyncio.sleep(wait_seconds)
                
                # Run reset for all accounts
                await self.run_daily_reset()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Daily reset loop error: {e}")
                # Wait 1 minute before retrying
                await asyncio.sleep(60)
    
    async def run_daily_reset(self):
        """
        Run daily reset for all accounts.
        
        Called at exactly 5:00 PM EST after all trades are confirmed closed.
        """
        logger.info("="*60)
        logger.info("DAILY RESET - 5:00 PM EST")
        logger.info("="*60)
        
        accounts = await self.db.get_all_accounts()
        
        for account in accounts:
            try:
                await self.reset_account(account)
            except Exception as e:
                logger.error(f"Failed to reset account {account.account_key}: {e}")
        
        logger.info(f"✓ Daily reset complete for {len(accounts)} account(s)")
    
    async def reset_account(self, account: Account):
        """
        Reset a single account for the new trading day.
        
        Steps:
        1. Update cycle_best_day_pnl if today was better
        2. Record profitable day
        3. Set new daily_start_balance (account is flat at 5pm)
        4. Reset daily_pnl to 0
        """
        today_pnl = account.daily_pnl or 0.0
        
        logger.info(f"[{account.account_key}] Daily reset: P&L = ${today_pnl:.2f}")
        
        # Step 1: Update best single-day P&L for this cycle
        if today_pnl > (account.cycle_best_day_pnl or 0.0):
            old_best = account.cycle_best_day_pnl or 0.0
            account.cycle_best_day_pnl = today_pnl
            logger.info(
                f"[{account.account_key}] New cycle best day: "
                f"${old_best:.2f} → ${today_pnl:.2f}"
            )
        
        # Step 2: Record profitable day
        is_profitable = today_pnl >= (account.initial_balance * 0.0025)  # 0.25%
        
        profitable_day = ProfitableDay(
            account_key=account.account_key,
            date=date.today(),
            pnl=today_pnl,
            is_profitable_day=is_profitable
        )
        
        # Insert into database
        try:
            async with self.db.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO profitable_days (account_key, date, pnl, is_profitable_day)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (account_key, date) DO UPDATE
                    SET pnl = $3, is_profitable_day = $4
                    """,
                    account.account_key, profitable_day.date, today_pnl, is_profitable
                )
            
            logger.info(
                f"[{account.account_key}] Recorded {'profitable' if is_profitable else 'non-profitable'} day"
            )
        except Exception as e:
            logger.error(f"Failed to record profitable day: {e}")
        
        # Step 3: Set new daily_start_balance
        # Account is flat at 5pm (all trades closed at 4:45pm), so equity = balance
        new_daily_start = account.current_balance
        
        # Step 4: Check if daily breach should be cleared
        # If account is breached, check if it's daily or overall
        clear_breach = False
        if account.breached:
            # Get risk profile for overall floor calculation
            if account.risk_profile_id:
                from ..database import get_db
                db = await get_db()
                profile = await db.get_risk_profile(account.risk_profile_id)
                if not profile:
                    profile = await db.get_default_risk_profile()
            else:
                from ..database import get_db
                db = await get_db()
                profile = await db.get_default_risk_profile()
            
            if profile:
                # Calculate overall floor
                from ..risk.calculator import get_risk_calculator
                calculator = get_risk_calculator()
                overall_floor = calculator.calculate_overall_floor(account, profile)
                
                # If current balance is ABOVE overall floor, it was a daily breach only
                if account.current_balance > overall_floor:
                    clear_breach = True
                    logger.info(
                        f"[{account.account_key}] Daily breach will be cleared - "
                        f"balance ${account.current_balance:.2f} > overall floor ${overall_floor:.2f}"
                    )
                else:
                    logger.warning(
                        f"[{account.account_key}] Overall breach active - "
                        f"balance ${account.current_balance:.2f} <= overall floor ${overall_floor:.2f} - "
                        f"trading remains disabled"
                    )
        
        # Step 5: Update account in database
        try:
            async with self.db.pool.acquire() as conn:
                if clear_breach:
                    # Clear daily breach flag
                    await conn.execute(
                        """
                        UPDATE accounts
                        SET daily_start_balance = $1,
                            daily_pnl = 0,
                            last_synced_balance = $2,
                            cycle_best_day_pnl = $3,
                            breached = FALSE,
                            paused = FALSE
                        WHERE account_key = $4
                        """,
                        new_daily_start,
                        account.current_balance,
                        account.cycle_best_day_pnl,
                        account.account_key
                    )
                    logger.info(
                        f"[{account.account_key}] ✓ Daily breach cleared - trading enabled"
                    )
                else:
                    # Normal reset without clearing breach
                    await conn.execute(
                        """
                        UPDATE accounts
                        SET daily_start_balance = $1,
                            daily_pnl = 0,
                            last_synced_balance = $2,
                            cycle_best_day_pnl = $3
                        WHERE account_key = $4
                        """,
                        new_daily_start,
                        account.current_balance,
                        account.cycle_best_day_pnl,
                        account.account_key
                    )
            
            logger.info(
                f"[{account.account_key}] ✓ Reset complete: "
                f"New daily_start_balance = ${new_daily_start:.2f}"
            )
        except Exception as e:
            logger.error(f"Failed to update account: {e}")


# Global handler instance
_handler: Optional[DailyResetHandler] = None


async def get_daily_reset_handler(db: "DatabaseManager") -> DailyResetHandler:
    """Get the global daily reset handler instance."""
    global _handler
    if _handler is None:
        _handler = DailyResetHandler(db)
        await _handler.start_daily_reset_scheduler()
    return _handler
