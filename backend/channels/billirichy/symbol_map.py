"""
BillirichyFX - Symbol Normalization Map
Maps various symbol representations to normalized format.
"""

# Symbol normalization map (case-insensitive matching)
SYMBOL_MAP = {
    # Gold
    'xauusd': 'XAUUSD',
    'gold': 'XAUUSD',
    'xau': 'XAUUSD',
    'gld': 'XAUUSD',
    
    # Silver
    'xagusd': 'XAGUSD',
    'silver': 'XAGUSD',
    'xag': 'XAGUSD',
    
    # US30 (Dow Jones)
    'us30': 'US30',
    'dow': 'US30',
    'dow jones': 'US30',
    'us 30': 'US30',
    'dj30': 'US30',
    
    # EUR/USD
    'eurusd': 'EURUSD',
    'eur/usd': 'EURUSD',
    'eur usd': 'EURUSD',
    'eu': 'EURUSD',
    
    # GBP/USD
    'gbpusd': 'GBPUSD',
    'gbp/usd': 'GBPUSD',
    'gbp usd': 'GBPUSD',
    'cable': 'GBPUSD',
    'gu': 'GBPUSD',
    
    # USD/JPY
    'usdjpy': 'USDJPY',
    'usd/jpy': 'USDJPY',
    'usd jpy': 'USDJPY',
    'uj': 'USDJPY',
    
    # USD/CAD
    'usdcad': 'USDCAD',
    'usd/cad': 'USDCAD',
    'usd cad': 'USDCAD',
    
    # GBP/JPY
    'gbpjpy': 'GBPJPY',
    'gbp/jpy': 'GBPJPY',
    'gbp jpy': 'GBPJPY',
    'gj': 'GBPJPY',
    
    # EUR/JPY
    'eurjpy': 'EURJPY',
    'eur/jpy': 'EURJPY',
    'eur jpy': 'EURJPY',
    'ej': 'EURJPY',
    
    # AUD/USD
    'audusd': 'AUDUSD',
    'aud/usd': 'AUDUSD',
    'aud usd': 'AUDUSD',
    
    # NZD/USD
    'nzdusd': 'NZDUSD',
    'nzd/usd': 'NZDUSD',
    'nzd usd': 'NZDUSD',
    
    # EUR/AUD
    'euraud': 'EURAUD',
    'eur/aud': 'EURAUD',
    'eur aud': 'EURAUD',
    
    # GBP/AUD
    'gbpaud': 'GBPAUD',
    'gbp/aud': 'GBPAUD',
    'gbp aud': 'GBPAUD',
    
    # USD/CHF
    'usdchf': 'USDCHF',
    'usd/chf': 'USDCHF',
    'usd chf': 'USDCHF',
    
    # GBP/CAD
    'gbpcad': 'GBPCAD',
    'gbp/cad': 'GBPCAD',
    'gbp cad': 'GBPCAD',
    
    # AUD/CAD
    'audcad': 'AUDCAD',
    'aud/cad': 'AUDCAD',
    'aud cad': 'AUDCAD',
    
    # CAD/JPY
    'cadjpy': 'CADJPY',
    'cad/jpy': 'CADJPY',
    'cad jpy': 'CADJPY',
    
    # CHF/JPY
    'chfjpy': 'CHFJPY',
    'chf/jpy': 'CHFJPY',
    'chf jpy': 'CHFJPY',
    
    # EUR/NZD
    'eurnzd': 'EURNZD',
    'eur/nzd': 'EURNZD',
    'eur nzd': 'EURNZD',
    
    # EUR/GBP
    'eurgbp': 'EURGBP',
    'eur/gbp': 'EURGBP',
    'eur gbp': 'EURGBP',
    'eg': 'EURGBP',
    
    # GBP/CHF
    'gbpchf': 'GBPCHF',
    'gbp/chf': 'GBPCHF',
    'gbp chf': 'GBPCHF',
    
    # EUR/CAD
    'eurcad': 'EURCAD',
    'eur/cad': 'EURCAD',
    'eur cad': 'EURCAD',
    
    # AUD/JPY
    'audjpy': 'AUDJPY',
    'aud/jpy': 'AUDJPY',
    'aud jpy': 'AUDJPY',
}

# Excluded symbols (crypto, synthetics, etc.)
EXCLUDED = {
    'btc', 'bitcoin', 'eth', 'ethereum', 'bnb', 'sol', 'solana',
    'volatility', 'vix', 'step index', 'boom', 'crash',
    'crypto', 'usdt', 'usdc', 'busd'
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
