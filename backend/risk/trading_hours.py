# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - Trading Hours Validator
Validates if new trades are allowed based on market hours and EOD rules.
"""

from datetime import datetime, time
import pytz
from loguru import logger


class TradingHoursValidator:
    """
    Validates trading hours for forex markets.
    
    Rules:
    - Daily trading: 6:00 PM EST → 4:45 PM EST next day (22h 45m window)
    - Daily reset: 4:45 PM - 6:00 PM EST (1h 15m lock)
    - Weekend close: Friday 4:45 PM EST
    - Weekend open: Monday 12:00 AM EST (midnight)
    - Saturday & Sunday: Fully closed
    
    Can be overridden by database settings:
    - allow_weekend_trading: If true, bypass weekend checks
    - allow_eod_trading: If true, bypass EOD checks
    """
    
    def __init__(self, db=None):
        self.timezone = pytz.timezone("America/New_York")  # EST/EDT
        self.db = db  # Optional: for checking settings
        
        # Trading hours
        self.daily_close_time = time(16, 45)  # 4:45 PM EST - force close trades
        self.daily_reset_start = time(17, 0)  # 5:00 PM EST - daily reset begins
        self.daily_open_time = time(18, 0)    # 6:00 PM EST - trading resumes (same day!)
        self.weekend_open_time = time(0, 0)   # Monday 12:00 AM EST - weekend ends
        
        logger.info("Initialized TradingHoursValidator")
    
    async def is_trading_allowed(self) -> tuple[bool, str]:
        """
        Check if new trades are allowed right now.
        
        Returns:
            (allowed: bool, reason: str)
        """
        # Check if settings override rules
        weekend_allowed = await self._is_weekend_trading_allowed()
        eod_allowed = await self._is_eod_trading_allowed()
        
        now = datetime.now(self.timezone)
        current_time = now.time()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # RULE 1: Weekend check (can be bypassed)
        if not weekend_allowed:
            if weekday == 5:  # Saturday
                return False, "WEEKEND_SATURDAY - Market closed on Saturday. Reopens Monday 12:00 AM EST"
            
            if weekday == 6:  # Sunday - entire day is closed
                return False, f"WEEKEND_SUNDAY - Market closed on Sunday. Reopens Monday 12:00 AM EST (currently {current_time.strftime('%I:%M %p')})"
            
            # RULE 2: Friday after 4:45pm (weekend close - can be bypassed)
            if weekday == 4:  # Friday
                if current_time >= self.daily_close_time:
                    return False, f"WEEKEND_CLOSE - No new trades after 4:45 PM EST on Friday (currently {current_time.strftime('%I:%M %p')}). Market reopens Monday 12:00 AM EST"
        
        # RULE 3: Daily EOD/Reset window (can be bypassed)
        if not eod_allowed:
            # After 4:45 PM but before 6:00 PM - daily reset period
            if current_time >= self.daily_close_time and current_time < self.daily_open_time:
                return False, f"EOD_RESET - Daily reset in progress (4:45 PM - 6:00 PM EST). Market reopens at 6:00 PM EST (currently {current_time.strftime('%I:%M %p')})"
        
        # All checks passed - trading allowed
        return True, "OK"
    
    async def _is_weekend_trading_allowed(self) -> bool:
        """Check if weekend trading is enabled in settings."""
        if not self.db:
            return False
        
        try:
            setting = await self.db.get_bot_setting('allow_weekend_trading')
            return setting == 'true' if setting else False
        except:
            return False
    
    async def _is_eod_trading_allowed(self) -> bool:
        """Check if EOD trading is enabled in settings."""
        if not self.db:
            return False
        
        try:
            setting = await self.db.get_bot_setting('allow_eod_trading')
            return setting == 'true' if setting else False
        except:
            return False
    
    def get_next_trading_window(self) -> str:
        """
        Get human-readable description of when trading will be allowed next.
        
        Returns:
            String describing next trading window
        """
        now = datetime.now(self.timezone)
        current_time = now.time()
        weekday = now.weekday()
        
        if weekday == 5:  # Saturday
            return "Monday 12:00 AM EST"
        
        if weekday == 6:  # Sunday - entire day closed
            return "Monday 12:00 AM EST"
        
        if weekday == 4 and current_time >= self.daily_close_time:  # Friday after 4:45pm
            return "Monday 12:00 AM EST"
        
        if current_time >= self.daily_close_time and current_time < self.daily_open_time:  # Reset period
            return "Today 6:00 PM EST"
        
        return "Now (trading allowed)"
    
    def should_close_all_trades(self) -> tuple[bool, str]:
        """
        Check if all trades should be force-closed right now.
        SYNCHRONOUS - checked during EOD close handler execution.
        
        Returns:
            (should_close: bool, reason: str)
        """
        now = datetime.now(self.timezone)
        current_time = now.time()
        weekday = now.weekday()
        
        # Close at exactly 4:45 PM EST any weekday
        if weekday <= 4:  # Monday-Friday
            if current_time.hour == 16 and current_time.minute == 45:
                if weekday == 4:
                    return True, "WEEKEND_CLOSE"
                else:
                    return True, "EOD_CLOSE"
        
        return False, "NO_CLOSE"


# Global instance
_validator = None


def get_trading_hours_validator(db=None) -> TradingHoursValidator:
    """Get the global trading hours validator instance."""
    global _validator
    if _validator is None:
        _validator = TradingHoursValidator(db=db)
    elif db and not _validator.db:
        # Update db reference if provided later
        _validator.db = db
    return _validator
