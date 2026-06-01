"""
Mirror Pupil v5.1 - Consistency Score Calculator
Calculates the 20% rule consistency score for prop firm compliance.
"""

from typing import Optional, Dict
from datetime import datetime, timedelta, date
from loguru import logger

from ..database import DatabaseManager, Account


class ConsistencyScoreCalculator:
    """
    Calculates consistency score (20% rule).
    
    Formula:
        consistency_score = (cycle_best_day_pnl / cycle_total_pnl) × 100
    
    Status:
        < 15%: Safe (green)
        15-20%: Warning (amber)
        >= 20%: Breach risk (red)
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        logger.info("Initialized ConsistencyScoreCalculator")
    
    async def calculate_consistency_score(self, account: Account) -> Dict:
        """
        Calculate consistency score for an account.
        
        Returns:
            Dict with:
            - score: Percentage (or None if undefined)
            - best_day: Best single-day P&L
            - total: Total cycle P&L
            - status: "safe" | "warning" | "breach" | "undefined"
        """
        if not account.cycle_start_date:
            return {
                "score": None,
                "best_day": 0.0,
                "total": 0.0,
                "status": "undefined"
            }
        
        # Get all profitable days since cycle start
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT pnl FROM profitable_days
                WHERE account_key = $1 AND date >= $2
                ORDER BY date
                """,
                account.account_key,
                account.cycle_start_date
            )
        
        # Calculate total P&L
        cycle_total_pnl = sum(row['pnl'] for row in rows)
        best_day_pnl = account.cycle_best_day_pnl or 0.0
        
        # If total P&L is <= 0, score is undefined
        if cycle_total_pnl <= 0:
            return {
                "score": None,
                "best_day": best_day_pnl,
                "total": cycle_total_pnl,
                "status": "undefined"
            }
        
        # Calculate score
        score = (best_day_pnl / cycle_total_pnl) * 100
        
        # Determine status
        if score < 15:
            status = "safe"
        elif score < 20:
            status = "warning"
        else:
            status = "breach"
        
        return {
            "score": round(score, 1),
            "best_day": best_day_pnl,
            "total": cycle_total_pnl,
            "status": status
        }
    
    async def count_profitable_days(
        self,
        account_key: str,
        days: int = 30
    ) -> int:
        """
        Count profitable days in the last N days.
        
        Args:
            account_key: Account key
            days: Number of days to look back (default 30)
        
        Returns:
            Count of profitable days
        """
        cutoff = date.today() - timedelta(days=days)
        
        async with self.db.pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM profitable_days
                WHERE account_key = $1
                AND date >= $2
                AND is_profitable_day = TRUE
                """,
                account_key,
                cutoff
            )
        
        return count or 0
    
    async def get_profitable_days_summary(
        self,
        account_key: str,
        days: int = 30
    ) -> Dict:
        """
        Get summary of profitable days for an account.
        
        Returns:
            Dict with:
            - profitable_count: Number of profitable days
            - total_days: Total trading days
            - required: Required profitable days (5 for Blue Guardian)
            - remaining: Days remaining to meet requirement
            - status: "safe" | "warning" | "breach"
        """
        profitable_count = await self.count_profitable_days(account_key, days)
        
        # Count total trading days
        cutoff = date.today() - timedelta(days=days)
        
        async with self.db.pool.acquire() as conn:
            total_days = await conn.fetchval(
                """
                SELECT COUNT(*) FROM profitable_days
                WHERE account_key = $1 AND date >= $2
                """,
                account_key,
                cutoff
            )
        
        total_days = total_days or 0
        
        # Blue Guardian requires 5 profitable days in 30 days
        required = 5
        remaining = required - profitable_count
        
        # Determine status
        if remaining <= 0:
            status = "safe"
        elif remaining <= 2:
            status = "warning"
        else:
            status = "breach"
        
        return {
            "profitable_count": profitable_count,
            "total_days": total_days,
            "required": required,
            "remaining": max(remaining, 0),
            "status": status
        }


# Global calculator instance
_calculator: Optional[ConsistencyScoreCalculator] = None


async def get_consistency_calculator(db: DatabaseManager) -> ConsistencyScoreCalculator:
    """Get the global consistency score calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = ConsistencyScoreCalculator(db)
    return _calculator
