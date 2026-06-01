"""
Mirror Pupil v5.1 - Risk Calculator
Price delta calculation and floor/limit calculations.
"""

from typing import Optional, Dict
from loguru import logger

from ..database import Account, RiskProfile


def calculate_price_delta(
    entry_price: float,
    sl_price: float,
    lot_size: float,
    symbol: str,
    contract_size: float = 100000.0,  # Standard forex lot
    tick_size: Optional[float] = None,
    tick_value: Optional[float] = None,
    current_price: Optional[float] = None
) -> float:
    """
    Calculate risk in USD for a trade.
    
    Formula (Forex):
        Risk (quote currency) = |Entry - SL| × Contract Size × Lot Size
    
    Formula (Indices):
        Risk (USD) = (|Entry - SL| / Tick Size) × Tick Value × Lot Size
    
    Args:
        entry_price: Entry price
        sl_price: Stop loss price
        lot_size: Lot size
        symbol: Trading symbol
        contract_size: Contract size (default 100,000 for forex)
        tick_size: Tick size for indices
        tick_value: Tick value for indices
        current_price: Current market price for currency conversion
    
    Returns:
        Risk in USD
    """
    price_diff = abs(entry_price - sl_price)
    
    # Indices (e.g., US30, NAS100, SPX500)
    if tick_size and tick_value:
        risk_usd = (price_diff / tick_size) * tick_value * lot_size
        logger.debug(
            f"Price delta (index): {symbol} "
            f"|{entry_price} - {sl_price}| / {tick_size} × {tick_value} × {lot_size} = ${risk_usd:.2f}"
        )
        return risk_usd
    
    # Forex
    risk_quote = price_diff * contract_size * lot_size
    
    # Currency conversion to USD
    if symbol.endswith("USD"):
        # Quote is USD (e.g., EURUSD, GBPUSD) - no conversion needed
        risk_usd = risk_quote
    elif symbol.startswith("USD"):
        # USD is base (e.g., USDCAD, USDJPY) - divide by current price
        if current_price:
            risk_usd = risk_quote / current_price
        else:
            # Fallback: assume 1:1
            risk_usd = risk_quote
            logger.warning(f"No current price for {symbol}, assuming 1:1 conversion")
    else:
        # Cross pair (e.g., EURJPY, GBPJPY) - need cross-to-USD rate
        # For now, use approximate conversion
        # TODO: Implement proper cross-pair conversion with live rates
        risk_usd = risk_quote
        logger.warning(f"Cross pair {symbol} - using approximate conversion")
    
    logger.debug(
        f"Price delta (forex): {symbol} "
        f"|{entry_price} - {sl_price}| × {contract_size} × {lot_size} = ${risk_usd:.2f}"
    )
    
    return risk_usd


class RiskCalculator:
    """
    Calculates risk metrics for accounts based on their risk profiles.
    """
    
    def __init__(self):
        logger.info("Initialized RiskCalculator")
    
    def calculate_daily_floor(self, account: Account, profile: RiskProfile) -> float:
        """
        Calculate the daily loss floor.
        
        Formula:
            daily_floor = daily_start_balance - (initial_balance × daily_loss_pct%)
        
        The floor is STATIC for the entire trading day (set at 5pm EST reset).
        """
        if not account.daily_start_balance or not account.initial_balance:
            return 0.0
        
        floor = account.daily_start_balance - (account.initial_balance * profile.daily_loss_pct / 100)
        return floor
    
    def calculate_overall_floor(self, account: Account, profile: RiskProfile) -> float:
        """
        Calculate the overall drawdown floor.
        
        Formula (trailing from closed balance):
            overall_floor = highest_banked_balance - (initial_balance × overall_loss_pct%)
        
        Formula (static):
            overall_floor = initial_balance × (1 - overall_loss_pct%)
        
        If profit lock is active:
            overall_floor = max(calculated_floor, locked_floor)
        """
        if not account.initial_balance:
            return 0.0
        
        # Check profit lock first
        if account.profit_locked and profile.profit_lock_floor_pct is not None:
            locked_floor = account.initial_balance * (1 - profile.profit_lock_floor_pct / 100)
        else:
            locked_floor = None
        
        # Calculate base floor
        if profile.overall_trailing:
            if profile.overall_trail_from_closed_balance:
                # Trail from highest banked balance (Blue Guardian model)
                trail_ref = account.highest_banked_balance or account.initial_balance
            else:
                # Trail from all-time high equity
                trail_ref = account.all_time_high_equity or account.initial_balance
            
            floor = trail_ref - (account.initial_balance * profile.overall_loss_pct / 100)
        else:
            # Static floor
            floor = account.initial_balance * (1 - profile.overall_loss_pct / 100)
        
        # Apply profit lock if active
        if locked_floor is not None:
            floor = max(floor, locked_floor)
        
        return floor
    
    def calculate_daily_room(
        self,
        account: Account,
        profile: RiskProfile,
        current_equity: float
    ) -> float:
        """
        Calculate remaining daily room.
        
        Formula:
            daily_room = current_equity - daily_floor
        """
        daily_floor = self.calculate_daily_floor(account, profile)
        return current_equity - daily_floor
    
    def calculate_overall_room(
        self,
        account: Account,
        profile: RiskProfile,
        current_equity: float
    ) -> float:
        """
        Calculate remaining overall room.
        
        Formula:
            overall_room = current_equity - overall_floor
        """
        overall_floor = self.calculate_overall_floor(account, profile)
        return current_equity - overall_floor
    
    def calculate_withdrawable(self, account: Account, profile: RiskProfile) -> float:
        """
        Calculate maximum safe withdrawal amount.
        
        Formula:
            withdrawable = current_balance - overall_floor - payout_buffer
        
        Where:
            payout_buffer = initial_balance × payout_buffer_pct%
        """
        if not account.current_balance or not account.initial_balance:
            return 0.0
        
        overall_floor = self.calculate_overall_floor(account, profile)
        payout_buffer = account.initial_balance * (profile.payout_buffer_pct / 100)
        
        withdrawable = account.current_balance - overall_floor - payout_buffer
        return max(withdrawable, 0.0)
    
    def check_profit_lock_trigger(self, account: Account, profile: RiskProfile) -> bool:
        """
        Check if profit lock should be triggered.
        
        Triggers when:
            current_balance >= initial_balance × (1 + profit_lock_pct%)
        
        Returns:
            True if profit lock should be activated
        """
        if not profile.profit_lock_pct:
            return False
        
        if account.profit_locked:
            return False  # Already locked
        
        if not account.current_balance or not account.initial_balance:
            return False
        
        threshold = account.initial_balance * (1 + profile.profit_lock_pct / 100)
        return account.current_balance >= threshold
    
    def calculate_combined_portfolio_risk(
        self,
        account: Account,
        active_trades_risk: float
    ) -> float:
        """
        Calculate total portfolio risk (existing + new trade).
        
        Args:
            account: Account object
            active_trades_risk: Sum of risk_usd from all active trades
        
        Returns:
            Combined risk in USD
        """
        return active_trades_risk
    
    def get_risk_summary(
        self,
        account: Account,
        profile: RiskProfile,
        current_equity: float,
        active_trades_risk: float = 0.0
    ) -> Dict:
        """
        Get complete risk summary for an account.
        
        Returns:
            Dict with all risk metrics
        """
        daily_floor = self.calculate_daily_floor(account, profile)
        overall_floor = self.calculate_overall_floor(account, profile)
        daily_room = self.calculate_daily_room(account, profile, current_equity)
        overall_room = self.calculate_overall_room(account, profile, current_equity)
        withdrawable = self.calculate_withdrawable(account, profile)
        
        return {
            "current_balance": account.current_balance,
            "current_equity": current_equity,
            "initial_balance": account.initial_balance,
            "highest_banked_balance": account.highest_banked_balance,
            "daily_start_balance": account.daily_start_balance,
            "daily_pnl": account.daily_pnl,
            "daily_floor": daily_floor,
            "daily_room": daily_room,
            "overall_floor": overall_floor,
            "overall_room": overall_room,
            "profit_locked": account.profit_locked,
            "withdrawable": withdrawable,
            "active_trades_risk": active_trades_risk,
            "max_risk_per_trade": account.initial_balance * profile.max_risk_per_trade_pct / 100,
        }


# Global calculator instance
_calculator: Optional[RiskCalculator] = None


def get_risk_calculator() -> RiskCalculator:
    """Get the global risk calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = RiskCalculator()
    return _calculator
