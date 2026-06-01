"""
Firepips - Management Action Parser
Implements Section 6 of the spec: Management Logic
"""

import re
from typing import Optional
from datetime import datetime
from loguru import logger

from ..base import ParsedManagement
from .symbol_map import normalize_symbol


# Management action patterns
CLOSE_PROFIT_RE = re.compile(
    r'\bCLOSE IN MASSIVE PROFIT\b|\bCLOSE IN PROFIT\b|'
    r'\bEXIT IN MASSIVE PROFIT\b|\bTAKE PROFIT\b|'
    r'\bCLOSE .* NOW\b|\bEXIT YOUR TRADES\b|'
    r'\bCLOSE RIGHT NOW\b|\bCLOSE NOW\b|\bEXIT NOW\b',
    re.IGNORECASE
)

CLOSE_LOSS_RE = re.compile(
    r'\bCLOSE IN LOSS\b|\bEXIT THIS TRADE IN A LOSS\b|'
    r'\bCUT YOUR LOSSES\b|\bEXIT IN LOSS\b',
    re.IGNORECASE
)

SL_HIT_RE = re.compile(
    r'\bSTOP LOSS HIT\b|\bSL HIT\b|\bSTOP LOSS TAKEN\b|'
    r'\bHIT SL\b|\bSTOPPED OUT\b',
    re.IGNORECASE
)

MODIFY_SL_RE = re.compile(
    r'\bTIGHTEN STOP LOSS TO\s+([\d.]+)\b|'
    r'\bADJUST STOP LOSS TO\s+([\d.]+)\b|'
    r'\bNEW SL:\s*([\d.]+)\b|'
    r'\bMOVE SL TO\s+([\d.]+)\b',
    re.IGNORECASE
)

MODIFY_TP_RE = re.compile(
    r'\bTP:\s*([\d.]+)\b|'
    r'\bTAKE PROFIT:\s*([\d.]+)\b|'
    r'\bNEW TP:\s*([\d.]+)\b|'
    r'\bMOVE TP TO\s+([\d.]+)\b',
    re.IGNORECASE
)

BREAKEVEN_RE = re.compile(
    r'\bBREAKEVEN\b|\bBREAK EVEN\b|\bBE\b|'
    r'\bMOVE TO BE\b|\bSET BE\b',
    re.IGNORECASE
)

CANCEL_ORDER_RE = re.compile(
    r'\bCANCEL ORDER\b|\bDELETE ORDER\b|'
    r'\bCANCEL PENDING\b|\bREMOVE ORDER\b',
    re.IGNORECASE
)

# IMPLIED CLOSE patterns (profit announcements)
IMPLIED_CLOSE_RE = re.compile(
    r'\bTAG ME WITH YOUR PROFIT\b|\bENJOY YOUR PROFITS\b|'
    r'\bMASSIVE PROFIT\b|\bMONEY PRINTED\b|'
    r'\bWE\'?RE IN PROFIT GUYS\b|\bPROFIT TIME\b|'
    r'\bCASH OUT\b',
    re.IGNORECASE
)


def detect_symbol_in_management(text: str) -> Optional[str]:
    """Extract symbol from management message."""
    words = text.split()
    for word in words:
        normalized = normalize_symbol(word)
        if normalized:
            return normalized
    
    # Try multi-word
    for i in range(len(words) - 1):
        two_word = f"{words[i]} {words[i+1]}"
        normalized = normalize_symbol(two_word)
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
    Parse a management action from Firepips.
    
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
    
    # 1. CLOSE IN PROFIT
    if CLOSE_PROFIT_RE.search(text):
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
    
    # 2. CLOSE IN LOSS
    if CLOSE_LOSS_RE.search(text):
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
    
    # 3. SL HIT
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
    
    # 4. MODIFY SL
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
    
    # 5. MODIFY TP
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
    
    # 6. BREAKEVEN
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
    
    # 7. CANCEL ORDER
    if CANCEL_ORDER_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='CANCEL_PENDING',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    # 8. IMPLIED CLOSE (profit announcement)
    if IMPLIED_CLOSE_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='IMPLIED_CLOSE',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    # No recognized action
    return None
