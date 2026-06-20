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
    r'\bclose\s+(?:the\s+)?(\w+)\b|\bexit\s+(?:the\s+)?(\w+)\b|\bclose\s+out\s+(\w+)\b',
    re.IGNORECASE
)

CLOSE_CONTEXT_RE = re.compile(
    r'\bclose\s+it\b|^\s*close\s*$',
    re.IGNORECASE
)

BREAKEVEN_RE = re.compile(
    r'\bset\s+be\b|'
    r'\bbreakeven\b|'
    r'\bbreak\s*-?\s*even\b|'
    r'\bmove\s+(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss|stop)\s+to\s+(?:entry|be|breakeven|break\s*-?\s*even)\b|'
    r'\bmoving\s+(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss|stop)\s+to\s+(?:entry|be|breakeven|break\s*-?\s*even)\b|'
    r'\bmove\s+to\s+be\b|'
    r'\block\b|'
    r'\block\s+profit\b|'
    r'\bsl\s+to\s+entry\b|'
    r'\bstop\s+to\s+entry\b|'
    r'\bsl\s*=\s*entry\b|'
    r'\bstop\s*=\s*entry\b|'
    r'\bsl\s+at\s+entry\b|'
    r'\bstop\s+at\s+entry\b|'
    r'\badjust\s+(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss|stop)\s+to\s+entry\b|'
    r'\bprotect\b|'
    r'\bsecure\s+profits?\b|'
    r'\bsecure\s+the\s+profits?\b|'
    r'\bsecure\s+gains?\b|'
    r'\brisk\s+free\b|'
    r'\bno\s+risk\b',
    re.IGNORECASE
)

PARTIAL_CLOSE_50_RE = re.compile(
    r'\bclose\s+half\b|'
    r'\bclose\s+50%\b|'
    r'\btake\s+(?:some\s+)?profit\b|'
    r'\btake\s+partials?\b|'
    r'\bhalf\s+out\b|'
    r'\b50%\s+out\b|'
    r'\breduce\s+half\b|'
    r'\bexit\s+half\b|'
    r'\bpartial\s+exit\b|'
    r'\bclose\s+some\b|'
    r'\bexit\s+some\b',
    re.IGNORECASE
)

PARTIAL_CLOSE_75_RE = re.compile(
    r'\bclose\s+75%\b|'
    r'\bclose\s+three\s+quarters\b|'
    r'\b3/4\s+out\b|'
    r'\bexit\s+75%\b',
    re.IGNORECASE
)

PARTIAL_CLOSE_70_RE = re.compile(
    r'\bclose\s+70%\b|'
    r'\bclose\s+most\b|'
    r'\bexit\s+most\b|'
    r'\bclose\s+majority\b|'
    r'\b70%\s+out\b|'
    r'\bexit\s+70%\b',
    re.IGNORECASE
)

PARTIAL_CLOSE_33_RE = re.compile(
    r'\bclose\s+33%\b|'
    r'\bclose\s+one\s+third\b|'
    r'\bclose\s+third\b|'
    r'\bclose\s+1/3\b|'
    r'\bexit\s+third\b',
    re.IGNORECASE
)

CLOSE_ALL_RE = re.compile(
    r'\bclose\s+all\s+positions\b|'
    r'\bclose\s+all\s+trades\b|'
    r'\bclose\s+all\b|'
    r'\bexit\s+all\s+positions\b|'
    r'\bexit\s+all\s+trades\b|'
    r'\bexit\s+all\b|'
    r'\bclose\s+everything\b|'
    r'\bexit\s+everything\b|'
    r'\bclose\s+out\b|'
    r'\bfull\s+exit\b|'
    r'\bclose\s+100%\b|'
    r'\bexit\s+100%\b|'
    r'\bclose\s+full\b',
    re.IGNORECASE
)

TP1_HIT_RE = re.compile(
    r'\btp1\s+hit\b|'
    r'\btp\s+1\s+hit\b|'
    r'\bfirst\s+tp\s+hit\b|'
    r'\bfirst\s+target\b|'
    r'\btp1\s+reached\b',
    re.IGNORECASE
)

TP2_HIT_RE = re.compile(r'\btp2\s+hit\b|\btp\s+2\s+hit\b', re.IGNORECASE)
TP3_HIT_RE = re.compile(r'\btp3\s+hit\b|\btp\s+3\s+hit\b', re.IGNORECASE)

SL_HIT_RE = re.compile(
    r'\bsl\s+hit\b|'
    r'\bstopped\s+out\b|'
    r'\bstop\s+hit\b|'
    r'\bsl\s+reached\b|'
    r'\bstop\s+reached\b',
    re.IGNORECASE
)

MODIFY_SL_RE = re.compile(
    r'\bmove\s+(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss|stop)\s+to\s+([\d.]+)\b|'
    r'\bmoving\s+(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss|stop)\s+to\s+([\d.]+)\b|'
    r'\bnew\s+(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss|stop)\s*:?\s*([\d.]+)\b|'
    r'\b(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss|stop)\s+now\s*:?\s*([\d.]+)\b|'
    r'\badjust\s+(?:sl|s\.l|s/l|stop\s*loss|stoploss|stop-loss|stop)\s+to\s+([\d.]+)\b|'
    r'\b(?:sl|s\.l|s/l|stop)\s*[=:]\s*([\d.]+)\b',
    re.IGNORECASE
)

MODIFY_TP_RE = re.compile(
    r'\bmove\s+(?:tp|t\.p|t/p|take\s*profit|takeprofit|take-profit|target)\s+to\s+([\d.]+)\b|'
    r'\bnew\s+(?:tp|t\.p|t/p|take\s*profit|takeprofit|take-profit|target)\s*:?\s*([\d.]+)\b|'
    r'\b(?:tp|t\.p|t/p|take\s*profit|takeprofit|take-profit|target)\s+now\s*:?\s*([\d.]+)\b|'
    r'\badjust\s+(?:tp|t\.p|t/p|take\s*profit|takeprofit|take-profit|target)\s+to\s+([\d.]+)\b|'
    r'\b(?:tp|t\.p|t/p|target)\s*[=:]\s*([\d.]+)\b',
    re.IGNORECASE
)

COMPOUND_RE = re.compile(
    r'\bclose\s+(?:some|half|50%|partials?)\s+and\s+(?:set\s+)?be\b|'
    r'\bclose\s+(?:some|half|50%|partials?)\s+and\s+breakeven\b|'
    r'\bclose\s+(?:some|half|50%|partials?)\s+and\s+break\s*-?\s*even\b|'
    r'\b(?:set\s+)?be\s+and\s+close\s+(?:some|half|50%|partials?)\b|'
    r'\bbreakeven\s+and\s+close\s+(?:some|half|50%|partials?)\b|'
    r'\bbreak\s*-?\s*even\s+and\s+close\s+(?:some|half|50%|partials?)\b|'
    r'\btake\s+(?:some|half|partials?)\s+(?:profit\s+)?and\s+(?:set\s+)?be\b|'
    r'\btake\s+(?:some|half|partials?)\s+(?:profit\s+)?and\s+breakeven\b|'
    r'\bpartial\s+close\s+and\s+(?:set\s+)?be\b|'
    r'\bpartial\s+and\s+(?:set\s+)?be\b|'
    r'\btp\d*\s+hit.*close\s+(?:some|half|partials?).*be\b|'
    r'\bfirst\s+target.*close\s+(?:some|half|partials?).*be\b',
    re.IGNORECASE | re.DOTALL
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
    
    Priority Order:
    1. CLOSE_ALL (broadcast)
    2. CLOSE_SYMBOL (symbol-specific)
    3. CLOSE (context-only, reply-dependent)
    4. PARTIAL_CLOSE_X%
    5. COMPOUND
    6. BREAKEVEN
    7. MODIFY_SL
    8. MODIFY_TP
    9. TP_HIT, SL_HIT (informational)
    
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
    
    # 1. CLOSE_ALL (broadcast)
    if CLOSE_ALL_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='CLOSE_ALL',
            symbol=None,  # Applies to all
            direction=None,
            new_sl=None,
            new_tp=None,
            close_pct=None,
            raw_text=text,
            timestamp=timestamp
        )
    
    # 2. CLOSE_SYMBOL (symbol-specific)
    match = CLOSE_SYMBOL_RE.search(text)
    if match:
        symbol_from_close = None
        for group in match.groups():
            if group:
                normalized = normalize_symbol(group)
                if normalized:
                    symbol_from_close = normalized
                    break
        
        if symbol_from_close:
            return ParsedManagement(
                channel_id=channel_id,
                msg_id=msg_id,
                reply_to_msg_id=reply_to,
                action='CLOSE_ALL',
                symbol=symbol_from_close,
                direction=direction,
                new_sl=None,
                new_tp=None,
                close_pct=None,
                raw_text=text,
                timestamp=timestamp
            )
    
    # 3. CLOSE (context-only, MUST be a reply)
    if reply_to and CLOSE_CONTEXT_RE.search(text):
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
    
    # 4. PARTIAL CLOSE (in order of specificity)
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
    
    if PARTIAL_CLOSE_70_RE.search(text):
        return ParsedManagement(
            channel_id=channel_id,
            msg_id=msg_id,
            reply_to_msg_id=reply_to,
            action='PARTIAL_CLOSE_70',
            symbol=symbol,
            direction=direction,
            new_sl=None,
            new_tp=None,
            close_pct=0.70,
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
    
    # 5. COMPOUND (close 50% + set BE)
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
            close_pct=0.50,
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
    
    # 7. MODIFY SL
    match = MODIFY_SL_RE.search(text)
    if match:
        new_sl = None
        for group in match.groups():
            if group:
                try:
                    # If contains slash, take first value
                    sl_val = group
                    if '/' in sl_val:
                        sl_val = sl_val.split('/')[0].strip()
                    new_sl = float(sl_val)
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
                    # If contains slash, take first value
                    tp_val = group
                    if '/' in tp_val:
                        tp_val = tp_val.split('/')[0].strip()
                    new_tp = float(tp_val)
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
    
    # 9. TP HIT (informational)
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
    
    # 10. SL HIT (informational)
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
    
    # No recognized action
    return None
