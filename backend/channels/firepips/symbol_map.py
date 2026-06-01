"""
Firepips - Symbol Normalization Map
Maps various symbol representations to normalized format.
"""

# Symbol normalization map (case-insensitive matching)
SYMBOL_MAP = {
    # Gold
    'xauusd': 'XAUUSD',
    'gold': 'XAUUSD',
    'xau': 'XAUUSD',
    
    # Silver
    'xagusd': 'XAGUSD',
    'silver': 'XAGUSD',
    
    # US30 (Dow Jones)
    'us30': 'US30',
    'dow': 'US30',
    'dow jones': 'US30',
    
    # GBP/USD
    'gbpusd': 'GBPUSD',
    'gu': 'GBPUSD',
    'cable': 'GBPUSD',
    
    # GBP/JPY
    'gbpjpy': 'GBPJPY',
    'gj': 'GBPJPY',
    
    # USD/JPY
    'usdjpy': 'USDJPY',
    'uj': 'USDJPY',
    
    # USD/CAD
    'usdcad': 'USDCAD',
    
    # CHF/JPY
    'chfjpy': 'CHFJPY',
    
    # AUD/JPY
    'audjpy': 'AUDJPY',
    
    # EUR/JPY
    'eurjpy': 'EURJPY',
    'ej': 'EURJPY',
    
    # EUR/USD
    'eurusd': 'EURUSD',
    'eu': 'EURUSD',
    
    # EUR/GBP
    'eurgbp': 'EURGBP',
    'eg': 'EURGBP',
    
    # GBP/NZD
    'gbpnzd': 'GBPNZD',
    
    # US Oil
    'usoil': 'USOIL',
    'oil': 'USOIL',
    'wti': 'USOIL',
}

# Excluded symbols (crypto, synthetics, etc.)
EXCLUDED = {
    'btcusd', 'btc', 'bitcoin',
    'ethusd', 'eth', 'ethereum',
    'vix25', 'vix75', 'vix100',
    'step index', 'boom', 'crash',
    'volatility', 'synthetic'
}


def normalize_symbol(raw: str) -> str:
    """
    Normalize a raw symbol string.
    
    Args:
        raw: Raw symbol from message
    
    Returns:
        Normalized symbol or None if excluded
    """
    if not raw:
        return None
    
    # Clean and lowercase
    clean = raw.lower().strip()
    
    # Check if excluded
    if any(excl in clean for excl in EXCLUDED):
        return None
    
    # Try direct lookup
    if clean in SYMBOL_MAP:
        return SYMBOL_MAP[clean]
    
    # Try without spaces/slashes
    clean_no_sep = clean.replace('/', '').replace(' ', '')
    if clean_no_sep in SYMBOL_MAP:
        return SYMBOL_MAP[clean_no_sep]
    
    return None
