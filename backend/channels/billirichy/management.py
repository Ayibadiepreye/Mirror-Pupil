"""
BillirichyFX - Management Action Parser
Implements Section 4 of the spec: Management Logic
"""

import re
from typing import Optional
from datetime import datetime
from loguru import logger

from ..base import ParsedManagement
from .symbol_map import normalize_symbol


# Management action patterns
CLOSE_SYMBOL_RE = re.compile(
    r'\bclose\s+(?:the\s+)?(\w+)\b|\bexit\s+(?:the\s+)?(\w+)\b',
    re.IGNORECASE
)

BREAKEVEN_RE = re.compile(
    r'\bset be\b|\bbreakeven\b|\bmove sl to entry\b|'
    r'\bmove to be\b|\block\b|\block profit\b',
    re.IGNORECASE
)

PARTIAL_CLOSE_50_RE = re.compile(
    r'\bclose half\b|\bclose 50%\b|\btake some profit\b|\btake partials\b',
    re.IGNORECASE
)

PARTIAL_CLOSE_75_RE = re.compile(
    r'\bclose most\b|\bclose 75%\b',
    re.IGNORECASE
)

PARTIAL_CLOSE_33_RE = re.compile(
    r'\bclose 33%\b|\bclose one third\b|\bclose third\b',
    re.IGNORECASE
)

CLOSE_ALL_RE = re.compile(
    r'\bclose alll?\b|\bexit\b|\bexit all\b|\bclose trades\b|\bclose everything\b',
    re.IGNORECASE
)

TP1_HIT_RE = re.compile(
    r'\btp1 hit\b|\btp 1 hit\b|\bfirst tp hit\b',
    re.IGNORECASE
)

TP2_HIT_RE = re.compile(r'\btp2 hit\b', re.IGNORECASE)
TP3_HIT_RE = re.compile(r'\btp3 hit\b', re.IGNORECASE)

SL_HIT_RE = re.compile(
    r'\bsl hit\b|\bstopped out\b|\bstop hit\b',
    re.IGNORECASE
)

MODIFY_SL_RE = re.compile(
    r'\bmove sl to\s+([\d.]+)\b|\bnew sl\s*:?\s*([\d.]+)\b|'
    r'\bsl now\s*:?\s*([\d.]+)\b|\badjust sl to\s+([\d.]+)',
    re.IGNORECASE
)

MODIFY_TP_RE = re.compile(
    r'\bmove tp to\s+([\d.]+)\b|\bnew tp\s*:?\s*([\d.]+)\b|'
    r'\btp now\s*:?\s*([\d.]+)',
    re.IGNORECASE
)

COMPOUND_RE = re.compile(
    r'\bclose some and set be\b|\bpartial and be\b',
    re.IGNORECASE
)


def detect_symbol_in_management(text: str) -> Optional[str]:
    """Extract symbol from management message."""
    # Try close/exit patterns first
    match = CLOSE_SYMBOL_RE.search(text)
    if match:
        for group in match.groups():
            if group:
                normalized = normalize_symbol(group)
                if normalized:
                    return normalized
    
    # Try general symbol detection
    words = text.split()
    for word in words:
        normalized = normalize_symbol(word)
        if normalized:
            return normalized
    
    return None


def detect_direction_in_management(text: str) -> Optional[str]:
    """Extract direction from management message."""
    if re.search(r'\bbuy\b|\bbuys\b|\blong\b', text, re.IGNORECASE):
        return 'BUY'
    elif re.search(r'\bsell\b|\bsells\b|\bshort\b', text, re.IGNORECASE):
        return 'SELL'
    return None


async def parse_management_action(
    message,
    text: str,
    channel_id: int
) -> Optional[ParsedManagement]:
    """
    Parse a management action from BillirichyFX.
    
    Returns:
        ParsedManagement if recognized action, None otherwise
    """
    msg_id = message.id
    reply_to = getattr(message, 'reply_to_message_id', None)
    timestamp = datetime.fromtimestamp(message.date)
    
    # Extract context
    symbol = detect_symbol_in_management(text)
    direction = detect_direction_in_management(text)
    
    # Check each action pattern in priority order
    
    # 1. COMPOUND (close some and set BE)
    if COMPOUND_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='COMPOUND',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=0.33,  # Close 33%, then BE
            raw_text=text,
            timestamp=timestamp
        )
    
    # 2. BREAKEVEN
    if BREAKEVEN_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='BREAKEVEN',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    # 3. PARTIAL CLOSE
    if PARTIAL_CLOSE_75_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='PARTIAL_CLOSE_75',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=0.75,
            raw_text=text,
            timestamp=timestamp
        )
    
    if PARTIAL_CLOSE_50_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='PARTIAL_CLOSE_50',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=0.50,
            raw_text=text,
            timestamp=timestamp
        )
    
    if PARTIAL_CLOSE_33_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='PARTIAL_CLOSE_33',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=0.33,
            raw_text=text,
            timestamp=timestamp
        )
    
    # 4. CLOSE ALL
    if CLOSE_ALL_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='CLOSE_ALL',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    # 5. TP HIT (informational)
    if TP1_HIT_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='TP1_HIT',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    if TP2_HIT_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='TP2_HIT',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    if TP3_HIT_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='TP3_HIT',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    # 6. SL HIT
    if SL_HIT_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='SL_HIT',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    # 7. MODIFY SL
    match = MODIFY_SL_RE.search(text)
    if match:
        new_sl = None
        for group in match.groups():
            if group:
                try:
                    new_sl = float(group)
                    break
                except ValueError:
                    continue
        
        if new_sl:
            return ParsedManagement(
                channel_id=channel_id,
                msg_id=msg_id,
                reply_to_msg_id=reply_to,
                action='MODIFY_SL',
                symbol=symbol,
                direction=direction,
                new_sl=new_sl,
                new_tp=None,
                close_pct=None,
                raw_text=text,
                timestamp=timestamp
            )
    
    # 8. MODIFY TP
    match = MODIFY_TP_RE.search(text)
    if match:
        new_tp = None
        for group in match.groups():
            if group:
                try:
                    new_tp = float(group)
                    break
                except ValueError:
                    continue
        
        if new_tp:
            return ParsedManagement(
                channel_id=channel_id,
                msg_id=msg_id,
                reply_to_msg_id=reply_to,
                action='MODIFY_TP',
                symbol=symbol,
                direction=direction,
                new_sl=None,
                new_tp=new_tp,
                close_pct=None,
                raw_text=text,
                timestamp=timestamp
            )
    
    # No recognized action
    return None
