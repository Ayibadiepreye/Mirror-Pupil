"""
Test TP Extraction Fix - Colon Validation
Verify that "Take Profit 2:" doesn't capture "2" as TP value.
"""

import re
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<level>{message}</level>",
    level="DEBUG"
)

# Regex pattern (from the parsers - UPDATED v2)
TP_RE = re.compile(
    r'\b(?:tp|t\.p|t/p|t\s+p|take\s*profit|takeprofit|take-profit|target)(?:\s*\d+)?\s*[:\-.]?\s+([\d.]+)',
    re.IGNORECASE
)


def extract_tps_fixed(text: str):
    """Fixed version with colon validation."""
    tps = []
    
    # Slash-separated check (priority)
    slash_pattern = re.compile(
        r'\b(?:tp|t\.p|t/p|take\s*profit|takeprofit|take-profit|target)(?:\s*\d+)?\s*[:\-.]?\s+([\d.]+(?:/[\d.]+)+)',
        re.IGNORECASE
    )
    
    match = slash_pattern.search(text)
    if match:
        tp_string = match.group(1)
        for tp_val in tp_string.split('/'):
            try:
                tp = float(tp_val.strip())
                tps.append(tp)
            except ValueError:
                continue
        if tps:
            return tps
    
    # Individual TP extraction with colon validation
    for match in TP_RE.finditer(text):
        try:
            captured_value = match.group(1)
            full_match_text = match.group(0)
            match_end = match.end()
            
            # Check what comes immediately after the matched text
            next_chars = text[match_end:match_end + 2] if match_end < len(text) else ''
            
            # VALIDATION 1: If there's a colon in the matched pattern
            if ':' in full_match_text:
                # Verify the captured number comes AFTER the colon
                colon_pos = full_match_text.rfind(':')
                value_start = full_match_text.find(captured_value)
                
                # If captured value appears BEFORE the colon, skip it
                if value_start < colon_pos:
                    logger.debug(f"✓ Skipping TP label before colon: '{full_match_text.strip()}'")
                    continue
            
            # VALIDATION 2: If NO colon in match, but a colon comes right after, skip it
            # This catches "Take Profit 2" where ":" is on the next line or immediately after
            if ':' not in full_match_text and next_chars.strip().startswith(':'):
                logger.debug(f"✓ Skipping TP label (colon follows): '{full_match_text.strip()}'")
                continue
            
            # Valid TP found
            tp = float(captured_value)
            tps.append(tp)
            
        except ValueError:
            continue
    
    return tps


def test_tp_extraction():
    """Test various TP formats."""
    
    test_cases = [
        # (text, expected_tps, description)
        (
            "XAUUSD SELL NOW\nEntry: 4000.02\nSL: 4020.355\nTake Profit: 3981.7185\nTake Profit 2:",
            [3981.7185],
            "TP with value + TP label without value"
        ),
        (
            "BUY EURUSD\nTP: 1.0850\nTP2:",
            [1.0850],
            "TP with colon + TP2 label without value"
        ),
        (
            "SELL GBPUSD\nTake Profit 1: 1.2500\nTake Profit 2: 1.2450",
            [1.2500, 1.2450],
            "Two valid TPs with colons"
        ),
        (
            "BUY GOLD\nTP 2600\nTP2 2610",
            [2600, 2610],
            "Two TPs without colons"
        ),
        (
            "SELL EURUSD\nTP: 1.0800/1.0750/1.0700",
            [1.0800, 1.0750, 1.0700],
            "Slash-separated TPs"
        ),
        (
            "BUY BTCUSD\nTake Profit: 45000",
            [45000],
            "Single TP with colon"
        ),
        (
            "SELL USDJPY\nTP 140.50",
            [140.50],
            "Single TP without colon"
        ),
        (
            "BUY XAUUSD\nTake Profit 2:",
            [],
            "Only label without value (should return empty)"
        ),
    ]
    
    print("=" * 80)
    print("TESTING TP EXTRACTION WITH COLON VALIDATION FIX")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for text, expected, description in test_cases:
        result = extract_tps_fixed(text)
        
        if result == expected:
            print(f"✅ PASS: {description}")
            print(f"   Input: {repr(text[:60])}...")
            print(f"   Expected: {expected}")
            print(f"   Got:      {result}")
            passed += 1
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Input: {repr(text[:60])}...")
            print(f"   Expected: {expected}")
            print(f"   Got:      {result}")
            failed += 1
        print()
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = test_tp_extraction()
    exit(0 if success else 1)
