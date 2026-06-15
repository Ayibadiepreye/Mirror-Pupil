"""
Mirror Pupil v5.1 - Risk Calculator
Price delta calculation and floor/limit calculations with proper currency conversion.
"""

from typing import Optional, Dict
from loguru import logger

from ..database.models import Account, RiskProfile


def parse_symbol(symbol: str) -> tuple:
    """
    Parse symbol into base and quote currencies.
    
    Examples:
        EURUSD → ("EUR", "USD")
        USDJPY → ("USD", "JPY")
        XAUUSD → ("XAU", "USD")
        EURGBP → ("EUR", "GBP")
    
    Returns:
        (base_currency, quote_currency)
    """
    # Standard 6-letter forex pairs
    if len(symbol) == 6 and symbol.isalpha():
        return symbol[:3], symbol[3:]
    
    # Pairs ending with USD (e.g., XAUUSD, BTCUSD)
    if symbol.endswith("USD"):
        return symbol[:-3], "USD"
    
    # Pairs starting with USD (e.g., USDJPY, USDCAD)
    elif symbol.startswith("USD"):
        return "USD", symbol[3:]
    
    # Fallback: split in half
    mid = len(symbol) // 2
    return symbol[:mid], symbol[mid:]


def detect_symbol_type(symbol: str) -> str:
    """
    Detect symbol type for conversion logic.
    
    Returns:
        "quote_usd" - Quote currency is USD (EURUSD, GBPUSD, XAUUSD)
        "base_usd"  - Base currency is USD (USDJPY, USDCHF, USDCAD)
        "cross"     - Cross pair (EURGBP, EURJPY, GBPJPY)
        "index"     - Index (US30, NAS100, UK100)
    """
    # Check if it's an index
    indices = ["US30", "NAS100", "US500", "UK100", "GER40", "JP225", "USOIL"]
    if any(idx in symbol.upper() for idx in indices):
        return "index"
    
    base, quote = parse_symbol(symbol)
    
    if quote == "USD":
        return "quote_usd"  # EURUSD, GBPUSD, XAUUSD
    elif base == "USD":
        return "base_usd"   # USDJPY, USDCHF, USDCAD
    else:
        return "cross"      # EURGBP, EURJPY, GBPJPY


async def get_conversion_rate(client, base: str, quote: str, current_price: Optional[float] = None) -> float:
    """
    Fetch live conversion rate to USD for cross pairs.
    
    Logic:
    1. Try fetching {quote}USD (e.g., GBPUSD for EURGBP)
    2. If that fails, try {base}USD (e.g., EURUSD for EURGBP) and calculate
    3. If both fail, use default multiplier (0.01)
    
    Args:
        client: TradeLocker client
        base: Base currency
        quote: Quote currency
        current_price: Current price of the pair (for calculation)
    
    Returns:
        Conversion rate to USD
    """
    conversion_rate = None
    
    # Try {quote}USD first (e.g., GBPUSD for EURGBP)
    try:
        quote_usd = f"{quote}USD"
        conversion_rate = await client.get_market_price(quote_usd)
        if conversion_rate and conversion_rate > 0:
            logger.debug(f"Conversion rate from {quote_usd}: {conversion_rate:.5f}")
            return conversion_rate
    except Exception as e:
        logger.debug(f"Failed to fetch {quote}USD: {e}")
    
    # Try {base}USD as fallback (e.g., EURUSD for EURGBP)
    try:
        base_usd = f"{base}USD"
        base_rate = await client.get_market_price(base_usd)
        if base_rate and base_rate > 0 and current_price and current_price > 0:
            # Calculate quote/USD from base/USD
            # Example: EURGBP = 0.85, EURUSD = 1.08
            # GBPUSD = EURUSD / EURGBP = 1.08 / 0.85 = 1.27
            conversion_rate = base_rate / current_price
            logger.debug(f"Conversion rate calculated from {base_usd}: {conversion_rate:.5f}")
            return conversion_rate
    except Exception as e:
        logger.debug(f"Failed to fetch {base}USD: {e}")
    
    # Default fallback
    logger.warning(f"Could not fetch conversion rate for {base}/{quote}, using default 0.01")
    return 0.01


async def calculate_usd_risk(
    symbol: str,
    entry_price: float,
    stop_loss: float,
    lot_size: float,
    client,  # TradeLocker client
    current_price: Optional[float] = None,
    instrument: Optional[Dict] = None
) -> float:
    """
    Calculate USD risk for any trading pair with proper currency conversion.
    
    This is the CORRECT implementation that fetches live prices for conversions.
    
    Args:
        symbol: Trading symbol (e.g., "EURUSD", "USDJPY", "XAUUSD")
        entry_price: Entry price
        stop_loss: Stop loss price
        lot_size: Lot size
        client: TradeLocker client (for fetching live prices)
        current_price: Current market price (optional, will fetch if needed)
        instrument: Instrument data dict (optional, for contract size/tick data)
    
    Returns:
        Risk in USD
    """
    # 1. Validate inputs
    if entry_price <= 0 or stop_loss <= 0:
        logger.warning(f"Invalid prices for {symbol}: entry={entry_price}, sl={stop_loss}")
        return 0.01 * lot_size  # Minimal risk
    
    price_diff = abs(entry_price - stop_loss)
    if price_diff <= 0:
        logger.warning(f"No price difference for {symbol}")
        return 0.01 * lot_size
    
    # 2. Get contract size from instrument data
    contract_size = 100000.0  # Default for forex
    tick_size_val = None
    tick_value_val = None
    
    if instrument:
        # If instrument dict passed in, use it
        contract_size = float(instrument.get("contract_size", 100000))
        tick_size_val = instrument.get("tick_size")
        tick_value_val = instrument.get("tick_value")
    else:
        # Otherwise fetch from client
        try:
            instrument_specs = await client.get_instrument(symbol)
            contract_size = instrument_specs.get("contract_size", 100000.0)
            tick_size_val = instrument_specs.get("tick_size")
            tick_value_val = instrument_specs.get("tick_value")
        except Exception as e:
            logger.warning(f"Failed to fetch instrument specs for {symbol}: {e}, using defaults")
    
    # 3. Detect symbol type
    symbol_type = detect_symbol_type(symbol)
    base, quote = parse_symbol(symbol)
    
    logger.debug(
        f"Risk calculation for {symbol}: type={symbol_type}, "
        f"entry={entry_price}, sl={stop_loss}, diff={price_diff:.5f}, "
        f"lot={lot_size}, contract={contract_size}"
    )
    
    # 4. Calculate risk based on type
    if symbol_type == "index":
        # Indices: Use tick size and tick value
        tick_size = tick_size_val if tick_size_val else (float(instrument.get("tick_size", 1.0)) if instrument else 1.0)
        tick_value = tick_value_val if tick_value_val else (float(instrument.get("tick_value", 1.0)) if instrument else 1.0)
        
        ticks_at_risk = price_diff / tick_size
        usd_risk = ticks_at_risk * tick_value * lot_size
        
        logger.debug(
            f"Index risk: {symbol} "
            f"{price_diff:.2f} / {tick_size} × {tick_value} × {lot_size} = ${usd_risk:.2f}"
        )
        
    elif symbol_type == "quote_usd":
        # Quote = USD (EURUSD, GBPUSD, XAUUSD)
        # No conversion needed - risk is already in USD
        risk_quote = price_diff * contract_size * lot_size
        usd_risk = risk_quote
        
        logger.debug(
            f"Quote USD risk: {symbol} "
            f"{price_diff:.5f} × {contract_size} × {lot_size} = ${usd_risk:.2f}"
        )
        
    elif symbol_type == "base_usd":
        # Base = USD (USDJPY, USDCHF, USDCAD)
        # Divide by current price to convert from quote currency to USD
        risk_quote = price_diff * contract_size * lot_size
        
        # Use current_price or entry_price as fallback
        conversion_price = current_price or entry_price
        
        if conversion_price and conversion_price > 0:
            usd_risk = risk_quote / conversion_price
            logger.debug(
                f"Base USD risk: {symbol} "
                f"{risk_quote:.2f} {quote} / {conversion_price:.5f} = ${usd_risk:.2f}"
            )
        else:
            logger.warning(f"No conversion price for {symbol}, using 1:1")
            usd_risk = risk_quote
        
    elif symbol_type == "cross":
        # Cross pairs (EURGBP, EURJPY, GBPJPY)
        # Fetch conversion rate to USD
        risk_quote = price_diff * contract_size * lot_size
        
        if quote == "JPY":
            # Special handling for JPY cross pairs (EURJPY, GBPJPY)
            # Fetch USDJPY rate
            try:
                usdjpy_rate = await client.get_market_price("USDJPY")
                if not usdjpy_rate or usdjpy_rate <= 0:
                    usdjpy_rate = 150.0  # Default fallback
                
                usd_risk = risk_quote / usdjpy_rate
                logger.debug(
                    f"Cross JPY risk: {symbol} "
                    f"{risk_quote:.2f} JPY / {usdjpy_rate:.2f} = ${usd_risk:.2f}"
                )
            except Exception as e:
                logger.error(f"Failed to fetch USDJPY rate: {e}")
                usd_risk = risk_quote / 150.0  # Fallback
        else:
            # Other cross pairs (EURGBP, EURCHF, etc.)
            # Fetch conversion rate
            try:
                conversion_rate = await get_conversion_rate(client, base, quote, current_price)
                usd_risk = risk_quote * conversion_rate
                logger.debug(
                    f"Cross risk: {symbol} "
                    f"{risk_quote:.2f} {quote} × {conversion_rate:.5f} = ${usd_risk:.2f}"
                )
            except Exception as e:
                logger.error(f"Failed to get conversion rate for {symbol}: {e}")
                usd_risk = risk_quote * 0.01  # Fallback
    
    else:
        # Unknown type - use conservative estimate
        logger.warning(f"Unknown symbol type for {symbol}, using conservative estimate")
        risk_quote = price_diff * contract_size * lot_size
        usd_risk = risk_quote * 0.01
    
    # 5. Ensure minimum risk
    if usd_risk <= 0:
        usd_risk = 0.01 * lot_size
    
    logger.info(f"✓ USD risk for {symbol}: ${usd_risk:.2f}")
    return usd_risk


async def calculate_usd_pnl(
    symbol: str,
    entry_price: float,
    exit_price: float,
    lot_size: float,
    direction: str,
    client,  # TradeLocker client
    instrument: Optional[Dict] = None
) -> float:
    """
    Calculate USD P&L for a closed trade with proper currency conversion.
    
    This function mirrors calculate_usd_risk() logic but for P&L calculation.
    
    Args:
        symbol: Trading symbol (e.g., "EURUSD", "USDJPY", "XAUUSD")
        entry_price: Entry price
        exit_price: Exit price
        lot_size: Lot size
        direction: Trade direction ("BUY" or "SELL")
        client: TradeLocker client (for fetching live prices)
        instrument: Instrument data dict (optional, for contract size/tick data)
    
    Returns:
        P&L in USD (positive for profit, negative for loss)
    """
    # 1. Validate inputs
    if entry_price <= 0 or exit_price <= 0:
        logger.warning(f"Invalid prices for {symbol}: entry={entry_price}, exit={exit_price}")
        return 0.0
    
    # 2. Calculate price difference based on direction
    if direction.upper() == 'BUY':
        price_diff = exit_price - entry_price  # Positive if profit
    else:  # SELL
        price_diff = entry_price - exit_price  # Positive if profit
    
    if price_diff == 0:
        return 0.0  # Break-even
    
    # 3. Get contract size from instrument data
    contract_size = 100000.0  # Default for forex
    tick_size_val = None
    tick_value_val = None
    
    if instrument:
        # If instrument dict passed in, use it
        contract_size = float(instrument.get("contract_size", 100000))
        tick_size_val = instrument.get("tick_size")
        tick_value_val = instrument.get("tick_value")
    else:
        # Otherwise fetch from client
        try:
            instrument_specs = await client.get_instrument(symbol)
            contract_size = instrument_specs.get("contract_size", 100000.0)
            tick_size_val = instrument_specs.get("tick_size")
            tick_value_val = instrument_specs.get("tick_value")
        except Exception as e:
            logger.warning(f"Failed to fetch instrument specs for {symbol}: {e}, using defaults")
    
    # 4. Detect symbol type
    symbol_type = detect_symbol_type(symbol)
    base, quote = parse_symbol(symbol)
    
    logger.debug(
        f"P&L calculation for {symbol}: type={symbol_type}, "
        f"entry={entry_price}, exit={exit_price}, diff={price_diff:.5f}, "
        f"lot={lot_size}, contract={contract_size}, direction={direction}"
    )
    
    # 5. Calculate P&L based on type
    if symbol_type == "index":
        # Indices: Use tick size and tick value
        tick_size = tick_size_val if tick_size_val else (float(instrument.get("tick_size", 1.0)) if instrument else 1.0)
        tick_value = tick_value_val if tick_value_val else (float(instrument.get("tick_value", 1.0)) if instrument else 1.0)
        
        ticks_moved = price_diff / tick_size
        usd_pnl = ticks_moved * tick_value * lot_size
        
        logger.debug(
            f"Index P&L: {symbol} "
            f"{price_diff:.2f} / {tick_size} × {tick_value} × {lot_size} = ${usd_pnl:.2f}"
        )
        
    elif symbol_type == "quote_usd":
        # Quote = USD (EURUSD, GBPUSD, XAUUSD)
        # No conversion needed - P&L is already in USD
        pnl_quote = price_diff * contract_size * lot_size
        usd_pnl = pnl_quote
        
        logger.debug(
            f"Quote USD P&L: {symbol} "
            f"{price_diff:.5f} × {contract_size} × {lot_size} = ${usd_pnl:.2f}"
        )
        
    elif symbol_type == "base_usd":
        # Base = USD (USDJPY, USDCHF, USDCAD)
        # Divide by exit price to convert from quote currency to USD
        pnl_quote = price_diff * contract_size * lot_size
        
        if exit_price and exit_price > 0:
            usd_pnl = pnl_quote / exit_price
            logger.debug(
                f"Base USD P&L: {symbol} "
                f"{pnl_quote:.2f} {quote} / {exit_price:.5f} = ${usd_pnl:.2f}"
            )
        else:
            logger.warning(f"No exit price for {symbol}, using 1:1")
            usd_pnl = pnl_quote
        
    elif symbol_type == "cross":
        # Cross pairs (EURGBP, EURJPY, GBPJPY)
        # Fetch conversion rate to USD
        pnl_quote = price_diff * contract_size * lot_size
        
        if quote == "JPY":
            # Special handling for JPY cross pairs (EURJPY, GBPJPY)
            # Fetch USDJPY rate
            try:
                usdjpy_rate = await client.get_market_price("USDJPY")
                if not usdjpy_rate or usdjpy_rate <= 0:
                    usdjpy_rate = 150.0  # Default fallback
                
                usd_pnl = pnl_quote / usdjpy_rate
                logger.debug(
                    f"Cross JPY P&L: {symbol} "
                    f"{pnl_quote:.2f} JPY / {usdjpy_rate:.2f} = ${usd_pnl:.2f}"
                )
            except Exception as e:
                logger.error(f"Failed to fetch USDJPY rate: {e}")
                usd_pnl = pnl_quote / 150.0  # Fallback
        else:
            # Other cross pairs (EURGBP, EURCHF, etc.)
            # Fetch conversion rate
            try:
                conversion_rate = await get_conversion_rate(client, base, quote, exit_price)
                usd_pnl = pnl_quote * conversion_rate
                logger.debug(
                    f"Cross P&L: {symbol} "
                    f"{pnl_quote:.2f} {quote} × {conversion_rate:.5f} = ${usd_pnl:.2f}"
                )
            except Exception as e:
                logger.error(f"Failed to get conversion rate for {symbol}: {e}")
                usd_pnl = pnl_quote * 0.01  # Fallback
    
    else:
        # Unknown type - use conservative estimate
        logger.warning(f"Unknown symbol type for {symbol}, using conservative estimate")
        pnl_quote = price_diff * contract_size * lot_size
        usd_pnl = pnl_quote * 0.01
    
    logger.info(f"✓ USD P&L for {symbol}: ${usd_pnl:.2f}")
    return usd_pnl


# Legacy sync function for backward compatibility
def calculate_price_delta(
    entry_price: float,
    sl_price: float,
    lot_size: float,
    symbol: str,
    contract_size: float = 100000.0,
    tick_size: Optional[float] = None,
    tick_value: Optional[float] = None,
    current_price: Optional[float] = None
) -> float:
    """
    LEGACY FUNCTION - For backward compatibility only.
    
    This function does NOT fetch live prices and will give INCORRECT results
    for USD-base pairs and cross pairs.
    
    Use calculate_usd_risk() instead for accurate calculations.
    """
    logger.warning(
        f"Using legacy calculate_price_delta() for {symbol} - "
        f"results may be inaccurate. Use calculate_usd_risk() instead."
    )
    
    price_diff = abs(entry_price - sl_price)
    
    # Indices
    if tick_size and tick_value:
        risk_usd = (price_diff / tick_size) * tick_value * lot_size
        return risk_usd
    
    # Forex
    risk_quote = price_diff * contract_size * lot_size
    
    # Currency conversion (APPROXIMATE - not accurate!)
    if symbol.endswith("USD"):
        risk_usd = risk_quote
    elif symbol.startswith("USD"):
        if current_price:
            risk_usd = risk_quote / current_price
        else:
            risk_usd = risk_quote
            logger.warning(f"No current price for {symbol}, assuming 1:1 conversion")
    else:
        risk_usd = risk_quote
        logger.warning(f"Cross pair {symbol} - using approximate conversion")
    
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
