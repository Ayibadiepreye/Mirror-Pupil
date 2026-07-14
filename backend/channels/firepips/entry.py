"""
Firepips - Entry Signal Parser
Implements Section 5 of the spec: Entry Logic
"""

import re
from typing import Optional, List
from datetime import datetime, timedelta
from loguru import logger

from ..base import ParsedSignal, BareSignal
from .symbol_map import normalize_symbol


# Regex patterns
DIRECTION_RE = re.compile(r'\b(buy|sell|long|short)\b', re.IGNORECASE)

DIRECTION_MAP = {
    'buy': 'BUY',
    'long': 'BUY',
    'sell': 'SELL',
    'short': 'SELL'
}

SL_RE = re.compile(
    r'\b(?:sl|s\.l|s/l|s\s+l|stop\s*loss|stoploss|stop-loss|stop)\s*[:\-;.]?\s*([\d.]+)',
    re.IGNORECASE
)

TP_RE = re.compile(
    r'\b(?:tp|t\.p|t/p|t\s+p|take\s*profit|takeprofit|take-profit|target)(?:\s*\d+)?\s*[:\-;.]\s+([\d.]+)',
    re.IGNORECASE
)

OPEN_TP_RE = re.compile(
    r'leave\s*it\s*open|keep\s*it\s*open|no\s*tp|open\s*trade|run\s*it',
    re.IGNORECASE
)

LIMIT_RE = re.compile(r'\blimit\b', re.IGNORECASE)
STOP_ORDER_RE = re.compile(r'\bstop\s*order\b|\bstop\s*entry\b', re.IGNORECASE)


def detect_direction(text: str) -> Optional[str]:
    """Extract direction from text."""
    match = DIRECTION_RE.search(text)
    if match:
        raw_dir = match.group(1).lower()
        return DIRECTION_MAP.get(raw_dir)
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
    
    # Try multi-word patterns (e.g., "dow jones", "us oil")
    for i in range(len(words) - 1):
        two_word = f"{words[i]} {words[i+1]}"
        normalized = normalize_symbol(two_word)
        if normalized:
            return normalized
    
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
    - Multiple TPs: "tp 100" "tp 105"
    - Slash-separated: "tp: 100/105/110" or "tp 100/105"
    
    IMPORTANT: If colon is present, TP value must be AFTER the colon.
    Prevents false positives like "Take Profit 2:" from capturing "2" as TP value.
    """
    tps = []
    
    # First, check for slash-separated format after TP keyword
    slash_pattern = re.compile(
        r'\b(?:tp|t\.p|t/p|take\s*profit|takeprofit|take-profit|target)\s*[:\-;.]?\s*([\d.]+(?:/[\d.]+)+)',
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
            logger.info(f"[Firepips] Detected multi-TP (slash-separated): {tps}")
            return tps
    
    # Fallback: Individual TP extraction with colon validation
    for match in TP_RE.finditer(text):
        try:
            captured_value = match.group(1)
            full_match_text = match.group(0)  # Full matched text
            match_end = match.end()
            
            # Check what comes immediately after the matched text
            next_chars = text[match_end:match_end + 2] if match_end < len(text) else ''
            
            # VALIDATION 1: If there's a colon in the matched pattern
            if ':' in full_match_text:
                # If colon exists, verify the captured number comes AFTER the colon
                colon_pos = full_match_text.rfind(':')
                value_start = full_match_text.find(captured_value)
                
                # If the captured value appears BEFORE the colon, skip it
                # Example: "Take Profit 2:" - the "2" is before the colon, so skip
                if value_start < colon_pos:
                    logger.debug(f"[Firepips] Skipping TP label before colon: '{full_match_text.strip()}'")
                    continue
            
            # VALIDATION 2: If NO colon in match, but a colon comes right after, skip it
            # This catches "Take Profit 2" where ":" is on the next line or immediately after
            if ':' not in full_match_text and next_chars.strip().startswith(':'):
                logger.debug(f"[Firepips] Skipping TP label (colon follows): '{full_match_text.strip()}'")
                continue
            
            # Valid TP found
            tp = float(captured_value)
            tps.append(tp)
            
        except ValueError:
            continue
    
    return tps


def has_open_tp_keyword(text: str) -> bool:
    """Check if message indicates to leave trade open (no TP)."""
    return OPEN_TP_RE.search(text) is not None


def determine_order_type(text: str) -> str:
    """Determine order type from text."""
    if LIMIT_RE.search(text):
        return 'LIMIT'
    elif STOP_ORDER_RE.search(text):
        return 'STOP'
    else:
        return 'MARKET'


async def parse_entry_signal(
    message,
    text: str,
    channel_id: int,
    add_to_waiting_room_callback
) -> Optional[ParsedSignal]:
    """
    Parse an entry signal from Firepips.
    
    Returns:
        ParsedSignal if complete, None if should be ignored or added to waiting room
    """
    msg_id = message.id
    timestamp = datetime.fromtimestamp(message.date)
    
    # 1. Detect direction
    direction = detect_direction(text)
    if not direction:
        logger.debug(f"[Firepips] No direction found in msg {msg_id}")
        return None
    
    # 2. Detect symbol
    symbol = detect_symbol(text)
    if not symbol:
        logger.debug(f"[Firepips] No valid symbol found in msg {msg_id}")
        return None
    
    # 3. Extract prices
    sl = extract_sl(text)
    tps = extract_tps(text)
    has_open_tp = has_open_tp_keyword(text)
    
    # 4. Determine order type
    order_type = determine_order_type(text)
    
    # 5. Classification
    if sl is None:
        # BARE signal - add to waiting room
        logger.info(
            f"[Firepips] BARE signal: {symbol} {direction} "
            f"(no SL) - adding to waiting room"
        )
        
        bare_signal = BareSignal(
            channel_id=channel_id,
            msg_id=msg_id,
            symbol=symbol,
            direction=direction,
            entry_price=None,  # Firepips typically uses market orders
            order_type=order_type,
            raw_text=text,
            timestamp=timestamp,
            expires_at=timestamp + timedelta(minutes=15)
        )
        
        add_to_waiting_room_callback(bare_signal)
        return None
    
    # WELL-DEFINED signal
    
    # 6. Handle TP
    tp_list = None
    if has_open_tp:
        # Explicitly no TP - leave open
        tp_list = None
        logger.debug(f"[Firepips] Open trade (no TP) - will leave open")
    elif tps:
        # Has explicit TP(s)
        tp_list = tps
    else:
        # No TP mentioned and no "open" keyword - leave as None
        tp_list = None
    
    # 7. Create ParsedSignal
    signal = ParsedSignal(
        channel_id=channel_id,
        msg_id=msg_id,
        symbol=symbol,
        direction=direction,
        entry_price=None,  # Firepips typically uses market orders
        sl=sl,
        tp=tp_list,
        order_type=order_type,
        is_reentry=False,  # Firepips doesn't have explicit re-entry signals
        raw_text=text,
        timestamp=timestamp
    )
    
    return signal
