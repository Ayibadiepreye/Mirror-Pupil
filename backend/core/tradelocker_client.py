"""
Mirror Pupil v5.1 - TradeLocker Client
Rate-limited wrapper around the official TradeLocker Python SDK (TLAPI).

Features:
- Rate limiting (5 req/s)
- Circuit breaker (3 failures → 120s cooldown)
- Retry logic (3 attempts with exponential backoff)
- Instrument caching (5-minute TTL)
- Lot size rounding
- Route validation
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import time
from loguru import logger

# TradeLocker SDK
from tradelocker import TLAPI
import pandas as pd


async def _to_thread_with_timeout(func, *args, timeout: float = 10.0, **kwargs):
    """Run a sync function in asyncio's thread pool with a hard timeout."""
    return await asyncio.wait_for(
        asyncio.to_thread(func, *args, **kwargs),
        timeout=timeout
    )


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class TradeLockerClient:
    """
    Rate-limited TradeLocker client with circuit breaker and retry logic.
    
    Based on v5.1 spec - uses official TLAPI class from tradelocker SDK.
    """
    
    def __init__(
        self,
        email: str,
        password: str,
        server: str,  # Prop firm server name (e.g., "Blue Guardian")
        environment: str = "live",  # "live" or "demo" - for URL construction
        max_rps: int = 5,
        circuit_failure_threshold: int = 3,
        circuit_timeout: int = 120,
        retry_attempts: int = 3,
        instrument_cache_ttl: int = 300  # 5 minutes
    ):
        self.email = email
        self.password = password
        self.server = server  # Prop firm name for auth payload
        self.environment = environment  # live/demo for URL
        self.credential_key = email
        
        # Rate limiting
        self.max_rps = max_rps
        self.semaphore = asyncio.Semaphore(max_rps)
        self.min_interval = 1.0 / max_rps  # 0.2s for 5 req/s
        self.last_request_time = 0
        
        # Circuit breaker
        self.circuit_state = CircuitState.CLOSED
        self.circuit_failure_count = 0
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_timeout = circuit_timeout
        self.circuit_opened_at = None
        
        # Retry logic
        self.retry_attempts = retry_attempts
        self.retry_delays = [1, 2, 4]  # Exponential backoff
        
        # Instrument cache
        self.instrument_cache: Dict[str, Any] = {}
        self.instrument_cache_time: Optional[datetime] = None
        self.instrument_cache_ttl = timedelta(seconds=instrument_cache_ttl)
        
        # Instrument ID cache (symbol -> instrument_id)
        self.instrument_id_cache: Dict[str, int] = {}
        
        # TLAPI client
        self.client: Optional[TLAPI] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.last_auth_time: Optional[datetime] = None
        
        # Base URL - constructed from environment (live/demo), NOT server (prop firm name)
        # Store both: base_url for our auth, environment_url for TLAPI SDK
        if environment == "demo":
            self.environment_url = "https://demo.tradelocker.com"
            self.base_url = f"{self.environment_url}/backend-api"
        else:  # live
            self.environment_url = "https://live.tradelocker.com"
            self.base_url = f"{self.environment_url}/backend-api"
        
        logger.info(
            f"Initialized TradeLockerClient for {email} on {server} ({environment}) "
            f"(rate: {max_rps} req/s, circuit: {circuit_failure_threshold} failures)"
        )
    
    async def _rate_limit(self):
        """Enforce rate limiting with semaphore + minimum interval."""
        async with self.semaphore:
            # Ensure minimum interval between requests
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                await asyncio.sleep(self.min_interval - time_since_last)
            self.last_request_time = time.time()
    
    def _check_circuit(self):
        """Check circuit breaker state."""
        if self.circuit_state == CircuitState.OPEN:
            # Check if timeout has passed
            if datetime.now() - self.circuit_opened_at > timedelta(seconds=self.circuit_timeout):
                logger.info(f"[{self.credential_key}] Circuit breaker: OPEN → HALF_OPEN (testing)")
                self.circuit_state = CircuitState.HALF_OPEN
                self.circuit_failure_count = 0
            else:
                raise Exception(
                    f"Circuit breaker OPEN for {self.credential_key}. "
                    f"Retry after {self.circuit_timeout}s."
                )
    
    def _record_success(self):
        """Record successful request."""
        if self.circuit_state == CircuitState.HALF_OPEN:
            logger.info(f"[{self.credential_key}] Circuit breaker: HALF_OPEN → CLOSED (recovered)")
            self.circuit_state = CircuitState.CLOSED
        self.circuit_failure_count = 0
    
    def _record_failure(self):
        """Record failed request."""
        self.circuit_failure_count += 1
        
        if self.circuit_failure_count >= self.circuit_failure_threshold:
            logger.error(
                f"[{self.credential_key}] Circuit breaker: CLOSED → OPEN "
                f"({self.circuit_failure_count} failures)"
            )
            self.circuit_state = CircuitState.OPEN
            self.circuit_opened_at = datetime.now()
    
    async def _ensure_authenticated(self):
        """
        Check token age and refresh if needed BEFORE every API call.
        Prevents 401 errors by proactively refreshing tokens.
        """
        if not self.access_token or not self.token_expires_at:
            await self.authenticate()
            return
        
        # Refresh if token will expire in next 10 minutes (safety margin)
        time_until_expiry = (self.token_expires_at - datetime.now()).total_seconds()
        if time_until_expiry < 600:  # 10 minutes
            logger.info(f"[{self.credential_key}] Token expiring soon, refreshing...")
            await self.authenticate()
    
    async def _with_auth_retry(self, func):
        """
        Wrap API calls with automatic 401 error recovery.
        Catches authentication errors, re-authenticates, and retries once.
        """
        try:
            return await func()
        except Exception as e:
            error_str = str(e).lower()
            # Detect 401/auth errors
            if "unauthorized" in error_str or "401" in error_str or "authentication" in error_str:
                logger.warning(f"[{self.credential_key}] Auth error detected, re-authenticating...")
                await self.authenticate()
                # Retry the original operation once
                return await func()
            raise  # Re-raise if not auth error
    
    async def authenticate(self):
        """
        Authenticate with TradeLocker.
        Uses direct HTTP POST (not SDK) as per v5.1 spec.
        """
        logger.info(f"[{self.credential_key}] Authenticating...")
        
        auth_url = f"{self.base_url}/auth/jwt/token"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    auth_url,
                    json={
                        "email": self.email,
                        "password": self.password,
                        "server": self.server
                    }
                ) as response:
                    # Accept both 200 OK and 201 Created
                    if response.status in [200, 201]:
                        data = await response.json()
                        self.access_token = data.get("accessToken")
                        self.refresh_token = data.get("refreshToken")
                        
                        # Token expires in 24 hours, refresh at 23 hours
                        self.token_expires_at = datetime.now() + timedelta(hours=23)
                        self.last_auth_time = datetime.now()
                        
                        # Initialize TLAPI client with token
                        # Use full environment URL (e.g., "https://demo.tradelocker.com")
                        self.client = TLAPI(
                            environment=self.environment_url,
                            access_token=self.access_token,
                            refresh_token=self.refresh_token
                        )
                        
                        logger.info(f"[{self.credential_key}] ✓ Authenticated successfully")
                        self._record_success()
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"[{self.credential_key}] Authentication failed: "
                            f"{response.status} - {error_text}"
                        )
                        self._record_failure()
                        return False
                        
            except Exception as e:
                logger.error(f"[{self.credential_key}] Authentication error: {e}")
                self._record_failure()
                raise
    
    async def _retry_call(self, func, *args, **kwargs):
        """
        Retry a function call with exponential backoff.
        3 attempts: 1s → 2s → 4s delays.
        
        Note: TLAPI methods are synchronous, so we run them in a thread pool
        to avoid blocking the event loop.
        """
        for attempt in range(self.retry_attempts):
            try:
                # ✅ Run sync TLAPI method in thread pool
                result = await _to_thread_with_timeout(
                    func, *args, timeout=10.0, **kwargs
                )
                self._record_success()
                return result
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delays[attempt]
                    logger.warning(
                        f"[{self.credential_key}] Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"[{self.credential_key}] All {self.retry_attempts} attempts failed: {e}"
                    )
                    self._record_failure()
                    raise
    
    async def _call_api(self, method_name: str, *args, **kwargs):
        """
        Call TLAPI method with rate limiting, circuit breaker, and retry logic.
        Now includes proactive token refresh and 401 auto-recovery.
        """
        # 1. Check token age and refresh if needed (proactive)
        await self._ensure_authenticated()
        
        # 2. Check circuit breaker
        self._check_circuit()
        
        # 3. Rate limit
        await self._rate_limit()
        
        # 4. Get method
        if not self.client:
            raise Exception("Client not authenticated. Call authenticate() first.")
        
        method = getattr(self.client, method_name)
        
        # 5. Call with retry AND auth recovery wrapper
        async def api_call():
            return await self._retry_call(method, *args, **kwargs)
        
        return await self._with_auth_retry(api_call)
    
    def _is_instrument_cache_valid(self) -> bool:
        """Check if instrument cache is still valid."""
        if not self.instrument_cache_time:
            return False
        return datetime.now() - self.instrument_cache_time < self.instrument_cache_ttl
    
    async def get_all_accounts(self) -> List[Dict]:
        """
        Get all sub-accounts for this credential.
        Returns DataFrame → converted to list of dicts.
        """
        logger.debug(f"[{self.credential_key}] Fetching all accounts...")
        
        df = await self._call_api("get_all_accounts")
        
        if isinstance(df, pd.DataFrame):
            accounts = df.to_dict('records')
            logger.info(f"[{self.credential_key}] Found {len(accounts)} account(s)")
            return accounts
        
        return []
    
    async def get_account_state(self, account_id: int) -> Dict:
        """
        Get account state (balance, equity, margin, etc.).
        """
        logger.debug(f"[{self.credential_key}] Fetching account state for {account_id}...")
        
        state = await self._call_api("get_account_state", account_id)
        return state
    
    async def get_all_instruments(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get all tradable instruments with caching (5-minute TTL).
        """
        if not force_refresh and self._is_instrument_cache_valid():
            logger.debug(f"[{self.credential_key}] Using cached instruments")
            return list(self.instrument_cache.values())
        
        logger.debug(f"[{self.credential_key}] Fetching all instruments...")
        
        df = await self._call_api("get_all_instruments")
        
        if isinstance(df, pd.DataFrame):
            instruments = df.to_dict('records')
            
            # Update cache
            self.instrument_cache = {inst['tradableInstrumentId']: inst for inst in instruments}
            self.instrument_cache_time = datetime.now()
            
            logger.info(f"[{self.credential_key}] Cached {len(instruments)} instrument(s)")
            return instruments
        
        return []
    
    async def get_instrument_id_from_symbol_name(self, symbol: str) -> Optional[int]:
        """
        Resolve symbol name to instrument ID.
        Uses cache to avoid repeated lookups.
        """
        # Check cache first
        if symbol in self.instrument_id_cache:
            return self.instrument_id_cache[symbol]
        
        logger.debug(f"[{self.credential_key}] Resolving symbol: {symbol}")
        
        try:
            instrument_id = await self._call_api("get_instrument_id_from_symbol_name", symbol)
            
            if instrument_id:
                # Cache it
                self.instrument_id_cache[symbol] = instrument_id
                logger.debug(f"[{self.credential_key}] {symbol} → instrument_id={instrument_id}")
                return instrument_id
            else:
                logger.warning(f"[{self.credential_key}] Symbol not found: {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"[{self.credential_key}] Error resolving symbol {symbol}: {e}")
            return None
    
    async def validate_instrument_routes(self, instrument_id: int) -> Dict[str, bool]:
        """
        Validate instrument has required routes (INFO and TRADE).
        """
        logger.debug(f"[{self.credential_key}] Validating routes for instrument {instrument_id}")
        
        has_info = False
        has_trade = False
        
        try:
            # Check INFO route
            info_route_id = await self._call_api("get_info_route_id", instrument_id)
            has_info = info_route_id is not None
            
            # Check TRADE route (internal SDK method)
            trade_route_ids = await self._call_api("_get_route_ids", instrument_id, "TRADE")
            has_trade = trade_route_ids is not None and len(trade_route_ids) > 0
            
            logger.debug(
                f"[{self.credential_key}] Instrument {instrument_id}: "
                f"INFO={has_info}, TRADE={has_trade}"
            )
            
            return {"info": has_info, "trade": has_trade}
            
        except Exception as e:
            logger.error(f"[{self.credential_key}] Route validation error: {e}")
            return {"info": False, "trade": False}
    
    def round_lot_size(self, lot_size: float, lot_step: float) -> float:
        """
        Round lot size to instrument's lot step.
        Ensures lot sizes are valid multiples.
        """
        if lot_step == 0:
            return lot_size
        
        rounded = round(lot_size / lot_step) * lot_step
        return round(rounded, 2)  # Round to 2 decimals
    
    async def create_order(
        self,
        instrument_id: int,
        quantity: float,
        side: str,  # "buy" or "sell" (lowercase!)
        type_: str = "market",  # "market", "limit", "stop" (lowercase!)
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        validity: str = "GTC",  # "GTC" or "IOC"
        position_netting: bool = True
    ) -> Dict:
        """
        Create an order.
        
        Args:
            instrument_id: Instrument ID (resolved from symbol)
            quantity: Lot size (already rounded)
            side: "buy" or "sell" (lowercase)
            type_: "market", "limit", or "stop" (lowercase)
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            stop_loss: SL price
            take_profit: TP price
            validity: "GTC" (Good Till Cancel) or "IOC" (Immediate or Cancel)
            position_netting: True for netting, False for hedging
        
        Returns:
            Order response dict
        """
        logger.info(
            f"[{self.credential_key}] Creating {type_.upper()} order: "
            f"{side.upper()} {quantity} lots of instrument {instrument_id}"
        )
        
        # Prepare SL/TP types (absolute prices)
        stop_loss_type = "absolute" if stop_loss else None
        take_profit_type = "absolute" if take_profit else None
        
        order = await self._call_api(
            "create_order",
            instrument_id=instrument_id,
            quantity=quantity,
            side=side.lower(),
            price=price,
            type_=type_.lower(),
            validity=validity,
            position_netting=position_netting,
            take_profit=take_profit,
            take_profit_type=take_profit_type,
            stop_loss=stop_loss,
            stop_loss_type=stop_loss_type,
            stop_price=stop_price
        )
        
        logger.info(f"[{self.credential_key}] ✓ Order created: {order}")
        return order
    
    async def modify_position(
        self,
        position_id: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        """
        Modify position SL/TP.
        Supports both stop_loss/take_profit and stopLoss/takeProfit kwargs.
        """
        logger.info(
            f"[{self.credential_key}] Modifying position {position_id}: "
            f"SL={stop_loss}, TP={take_profit}"
        )
        
        result = await self._call_api(
            "modify_position",
            position_id=position_id,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        logger.info(f"[{self.credential_key}] ✓ Position modified")
        return result
    
    async def close_position(
        self,
        position_id: int,
        quantity: Optional[float] = None
    ) -> Dict:
        """
        Close position (full or partial).
        
        Args:
            position_id: Position ID
            quantity: Lot size to close (None = close all)
        """
        if quantity:
            logger.info(
                f"[{self.credential_key}] Closing {quantity} lots of position {position_id}"
            )
        else:
            logger.info(f"[{self.credential_key}] Closing full position {position_id}")
        
        result = await self._call_api(
            "close_position",
            position_id=position_id,
            qty=quantity
        )
        
        logger.info(f"[{self.credential_key}] ✓ Position closed")
        return result
    
    async def delete_order(self, order_id: int) -> Dict:
        """
        Cancel/delete a pending order.
        """
        logger.info(f"[{self.credential_key}] Cancelling order {order_id}")
        
        result = await self._call_api("delete_order", order_id)
        
        logger.info(f"[{self.credential_key}] ✓ Order cancelled")
        return result
    
    async def get_order_status(self, order_id: int) -> Optional[Dict]:
        """
        Get status of a pending order.
        
        Args:
            order_id: TradeLocker order ID
        
        Returns:
            Dict with order details including status, filledQuantity, fillPrice, etc.
            None if order not found
        """
        try:
            logger.debug(f"[{self.credential_key}] Fetching order status for {order_id}")
            
            # Get all orders
            orders_df = await self._call_api("get_all_orders")
            
            if isinstance(orders_df, pd.DataFrame) and not orders_df.empty:
                # Find the specific order
                order_row = orders_df[orders_df['id'] == order_id]
                
                if not order_row.empty:
                    order_dict = order_row.iloc[0].to_dict()
                    logger.debug(f"[{self.credential_key}] Order {order_id} status: {order_dict.get('status')}")
                    return order_dict
            
            logger.warning(f"[{self.credential_key}] Order {order_id} not found")
            return None
            
        except Exception as e:
            logger.error(f"[{self.credential_key}] Failed to get order status for {order_id}: {e}")
            return None
    
    async def get_all_positions(self) -> List[Dict]:
        """
        Get all open positions.
        Returns DataFrame → converted to list of dicts.
        """
        logger.debug(f"[{self.credential_key}] Fetching all positions...")
        
        df = await self._call_api("get_all_positions")
        
        if isinstance(df, pd.DataFrame):
            positions = df.to_dict('records')
            logger.debug(f"[{self.credential_key}] Found {len(positions)} position(s)")
            return positions
        
        return []
    
    async def get_market_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price (mid price) for a symbol.
        Used for currency conversion in risk calculations.
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD", "USDJPY")
        
        Returns:
            Mid price (average of bid/ask) or None if not available
        """
        try:
            # Get instrument ID
            instrument_id = await self.get_instrument_id_from_symbol_name(symbol)
            if not instrument_id:
                logger.warning(f"[{self.credential_key}] Cannot get price for unknown symbol: {symbol}")
                return None
            
            # Get all instruments to find current price
            instruments = await self.get_all_instruments()
            
            # Find the instrument
            instrument = next(
                (inst for inst in instruments if inst.get('tradableInstrumentId') == instrument_id),
                None
            )
            
            if not instrument:
                logger.warning(f"[{self.credential_key}] Instrument not found: {symbol}")
                return None
            
            # Try to get bid/ask prices
            bid = instrument.get('bid')
            ask = instrument.get('ask')
            
            if bid and ask:
                mid_price = (float(bid) + float(ask)) / 2.0
                logger.debug(f"[{self.credential_key}] {symbol} price: {mid_price:.5f}")
                return mid_price
            
            # Fallback: try to get last price
            last_price = instrument.get('lastPrice') or instrument.get('price')
            if last_price:
                price = float(last_price)
                logger.debug(f"[{self.credential_key}] {symbol} last price: {price:.5f}")
                return price
            
            logger.warning(f"[{self.credential_key}] No price data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"[{self.credential_key}] Error fetching price for {symbol}: {e}")
            return None


# Token refresh background task
async def token_refresh_loop(client: TradeLockerClient):
    """
    Background task to refresh tokens every 50 minutes.
    Updated from 23 hours to 50 minutes for better resilience.
    """
    while True:
        await asyncio.sleep(50 * 60)  # 50 minutes
        
        try:
            logger.info(f"[{client.credential_key}] Refreshing token (scheduled)...")
            await client.authenticate()
            logger.info(f"[{client.credential_key}] ✓ Token refreshed")
        except Exception as e:
            logger.error(f"[{client.credential_key}] Token refresh FAILED: {e}")
            # TODO: Send CRITICAL notification to GUI
