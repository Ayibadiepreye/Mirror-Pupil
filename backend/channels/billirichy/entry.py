"""
BillirichyFX - Entry Signal Parser
Implements Section 3 of the spec: Entry Logic
"""

import re
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from loguru import logger

from ..base import ParsedSignal, BareSignal
from .symbol_map import normalize_symbol


# Regex patterns
DIRECTION_RE = re.compile(r'\b(buy|sell)\b', re.IGNORECASE)

ENTRY_RE = re.compile(
    r'(?:entry|enter)(?:\s+price)?\s*:?\s*([\d.]+)|'
    r'(?:at|@)\s*:?\s*([\d.]+)|'
    r'\blimit\s*:?\s*([\d.]+)|'
    r'\bstop\s*:?\s*([\d.]+)',
    re.IGNORECASE
)

SL_RE = re.compile(
    r'\b(?:sl|s\.l|s/l|s\s+l|stop\s*loss|stoploss|stop-loss|stop)\s*[:\-.]?\s*([\d.]+)',
    re.IGNORECASE
)

TP_RE = re.compile(
    r'\b(?:tp\d*|t\.p\d*|t/p\d*|t\s+p\d*|take\s*profit|takeprofit|take-profit|target\d*)\s*[:\-.]?\s*([\d.]+)',
    re.IGNORECASE
)

LIMIT_RE = re.compile(r'\blimit\b', re.IGNORECASE)
STOP_ORDER_RE = re.compile(r'\bstop\s*order\b|\bstop\s*entry\b', re.IGNORECASE)

# Re-entry keywords
REENTRY_KEYWORDS = [
    'add more', 'second entry', 're-enter', 'reenter',
    'stack', 'add', 'another entry', 'more buys', 'more sells',
    'another', 'more entries'
]


def detect_direction(text: str) -> Optional[str]:
    """Extract direction from text."""
    match = DIRECTION_RE.search(text)
    if match:
        return match.group(1).upper()
    return None


def detect_symbol(text: str) -> Optional[str]:
    """
    Extract and normalize symbol from text.
    Tries to find any known symbol pattern.
    """
    # Try common patterns first
    words = text.split()
    for word in words:
        normalized = normalize_symbol(word)
        if normalized:
            return normalized
    
    # Try multi-word patterns (e.g., "dow jones", "us 30")
    for i in range(len(words) - 1):
        two_word = f"{words[i]} {words[i+1]}"
        normalized = normalize_symbol(two_word)
        if normalized:
            return normalized
    
    return None


def is_reentry(text: str) -> bool:
    """Check if message indicates a re-entry."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in REENTRY_KEYWORDS)


def extract_entry_price(text: str) -> Optional[float]:
    """
    Extract entry price from text.
    If slash-separated (e.g., "entry: 2650/2660"), pick FIRST value only.
    """
    match = ENTRY_RE.search(text)
    if match:
        # Try each capture group
        for group in match.groups():
            if group:
                # If contains slash, take first value
                if '/' in group:
                    first_val = group.split('/')[0].strip()
                    try:
                        return float(first_val)
                    except ValueError:
                        continue
                else:
                    try:
                        return float(group)
                    except ValueError:
                        continue
    return None


def extract_sl(text: str) -> Optional[float]:
    """
    Extract stop loss from text.
    If slash-separated (e.g., "sl: 2640/2638"), pick FIRST value only.
    """
    match = SL_RE.search(text)
    if match:
        try:
            sl_val = match.group(1)
            # If contains slash, take first value
            if '/' in sl_val:
                sl_val = sl_val.split('/')[0].strip()
            return float(sl_val)
        except ValueError:
            pass
    return None


def extract_tps(text: str) -> List[float]:
    """
    Extract all take profit levels from text.
    Handles:
    - Multiple TPs: "tp 2680" "tp2 2690"
    - Slash-separated: "tp: 4584/4583.4" or "tp 2650/2660/2670"
    """
    tps = []
    
    # First, check for slash-separated format after TP keyword
    slash_pattern = re.compile(
        r'\b(?:tp\d*|t\.p\d*|t/p\d*|take\s*profit|takeprofit|take-profit|target\d*)\s*[:\-.]?\s*([\d.]+(?:/[\d.]+)+)',
        re.IGNORECASE
    )
    
    match = slash_pattern.search(text)
    if match:
        # Split by slash and extract all TPs
        tp_string = match.group(1)
        for tp_val in tp_string.split('/'):
            try:
                tp = float(tp_val.strip())
                tps.append(tp)
            except ValueError:
                continue
        
        if tps:
            logger.info(f"[Entry] Detected multi-TP (slash-separated): {tps}")
            return tps
    
    # Fallback: Original individual TP extraction
    for match in TP_RE.finditer(text):
        try:
            tp = float(match.group(1))
            tps.append(tp)
        except ValueError:
            continue
    
    return tps


def determine_order_type(text: str, has_entry_price: bool) -> str:
    """
    Determine order type from text.
    Only LIMIT/STOP if explicitly stated, otherwise MARKET.
    """
    if LIMIT_RE.search(text):
        return 'LIMIT'
    elif STOP_ORDER_RE.search(text):
        return 'STOP'
    else:
        # Default to MARKET unless explicitly stated otherwise
        return 'MARKET'


def calculate_auto_tp(entry: float, sl: float, direction: str) -> float:
    """
    Calculate automatic TP when none provided.
    TP = entry ± 2× SL distance
    """
    sl_distance = abs(entry - sl)
    if direction == 'BUY':
        return entry + (2 * sl_distance)
    else:  # SELL
        return entry - (2 * sl_distance)


async def parse_entry_signal(
    message,
    text: str,
    channel_id: int,
    add_to_waiting_room_callback
) -> Optional[ParsedSignal]:
    """
    Parse an entry signal from BillirichyFX.
    
    Returns:
        ParsedSignal if complete, None if should be ignored or added to waiting room
    """
    msg_id = message.id
    timestamp = datetime.fromtimestamp(message.date)
    
    # 1. Detect direction
    direction = detect_direction(text)
    if not direction:
        logger.debug(f"[BillirichyFX] No direction found in msg {msg_id}")
        return None
    
    # 2. Detect symbol
    symbol = detect_symbol(text)
    if not symbol:
        logger.debug(f"[BillirichyFX] No valid symbol found in msg {msg_id}")
        return None
    
    # 3. Check if re-entry
    is_re = is_reentry(text)
    
    # 4. Extract prices
    entry_price = extract_entry_price(text)
    sl = extract_sl(text)
    tps = extract_tps(text)
    
    # 5. Determine order type
    order_type = determine_order_type(text, entry_price is not None)
    
    # 6. Classification: WELL-DEFINED vs BARE
    if sl is None:
        # BARE signal - add to waiting room
        logger.info(
            f"[BillirichyFX] BARE signal: {symbol} {direction} "
            f"(no SL) - adding to waiting room"
        )
        
        bare_signal = BareSignal(
            channel_id=channel_id,
            msg_id=msg_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price if order_type in ['LIMIT', 'STOP'] else None,
            order_type=order_type,
            raw_text=text,
            timestamp=timestamp,
            expires_at=timestamp + timedelta(minutes=15)
        )
        
        add_to_waiting_room_callback(bare_signal)
        return None
    
    # WELL-DEFINED signal
    
    # 7. Handle entry price for market orders
    if order_type == 'MARKET':
        # Market orders execute at current price, ignore any mentioned price
        entry_price = None
    
    # 8. Handle TP
    if not tps:
        # Auto-assign TP if we have entry and SL
        if entry_price and sl:
            auto_tp = calculate_auto_tp(entry_price, sl, direction)
            tps = [auto_tp]
            logger.debug(
                f"[BillirichyFX] Auto-assigned TP: {auto_tp} "
                f"(2x SL distance from entry)"
            )
    
    # 9. Create ParsedSignal
    signal = ParsedSignal(
        channel_id=channel_id,
        msg_id=msg_id,
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        sl=sl,
        tp=tps if tps else None,
        order_type=order_type,
        is_reentry=is_re,
        raw_text=text,
        timestamp=timestamp
    )
    
    return signal
