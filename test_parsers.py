"""
Mirror Pupil v5.1 - Parser Test Script
Test signal parsers with sample messages without needing Telegram connection.
"""

import asyncio
from datetime import datetime
from dataclasses import dataclass

# Mock message object
@dataclass
class MockMessage:
    id: int
    chat_id: int
    date: float
    reply_to_message_id: int = None


async def test_billirichy_parser():
    """Test BillirichyFX parser with sample messages."""
    from backend.channels.billirichy.plugin import BillirichyPlugin
    
    print("=" * 80)
    print("Testing BillirichyFX Parser")
    print("=" * 80)
    
    plugin = BillirichyPlugin(
        channel_id=-1001859598768,
        display_name='BillirichyFX'
    )
    
    # Test cases
    test_cases = [
        {
            "name": "Complete GOLD BUY signal",
            "text": "GOLD BUY @ 2650 SL 2640 TP 2680",
            "expected": "ParsedSignal with entry, SL, TP"
        },
        {
            "name": "XAUUSD SELL with multiple TPs",
            "text": "XAUUSD SELL entry 2650 sl 2660 tp1 2640 tp2 2630 tp3 2620",
            "expected": "ParsedSignal with 3 TPs"
        },
        {
            "name": "Bare signal (no SL)",
            "text": "US30 BUY @ 38500",
            "expected": "Added to waiting room"
        },
        {
            "name": "LIMIT order",
            "text": "EURUSD BUY limit 1.0850 sl 1.0800 tp 1.0950",
            "expected": "ParsedSignal with order_type=LIMIT"
        },
        {
            "name": "Re-entry signal",
            "text": "GOLD add more buys @ 2645 sl 2640 tp 2680",
            "expected": "ParsedSignal with is_reentry=True"
        },
        {
            "name": "Breakeven management",
            "text": "GOLD set BE",
            "expected": "ParsedManagement action=BREAKEVEN"
        },
        {
            "name": "Close half",
            "text": "XAUUSD close half",
            "expected": "ParsedManagement action=PARTIAL_CLOSE_50"
        },
        {
            "name": "Modify SL",
            "text": "GOLD move sl to 2655",
            "expected": "ParsedManagement action=MODIFY_SL"
        },
        {
            "name": "TP1 hit",
            "text": "GOLD TP1 hit",
            "expected": "ParsedManagement action=TP1_HIT"
        },
        {
            "name": "Close all",
            "text": "close all trades",
            "expected": "ParsedManagement action=CLOSE_ALL"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   Input: {test['text']}")
        print(f"   Expected: {test['expected']}")
        
        # Create mock message
        msg = MockMessage(
            id=1000 + i,
            chat_id=-1001859598768,
            date=datetime.now().timestamp()
        )
        
        # Try entry parsing
        signal = await plugin.parse_entry(msg, test['text'].lower())
        if signal:
            print(f"   ✓ Result: {signal}")
            continue
        
        # Try management parsing
        mgmt = await plugin.parse_management(msg, test['text'].lower())
        if mgmt:
            print(f"   ✓ Result: {mgmt}")
            continue
        
        # Check waiting room
        if plugin._waiting_room:
            print(f"   ✓ Result: Added to waiting room ({len(plugin._waiting_room)} entries)")
        else:
            print(f"   ✗ Result: No match")


async def test_firepips_parser():
    """Test Firepips parser with sample messages."""
    from backend.channels.firepips.plugin import FirepipsPlugin
    
    print("\n\n" + "=" * 80)
    print("Testing Firepips Parser")
    print("=" * 80)
    
    plugin = FirepipsPlugin(
        channel_id=-1001182913499,
        display_name='Firepips'
    )
    
    # Test cases
    test_cases = [
        {
            "name": "Complete GBPUSD LONG signal",
            "text": "GBPUSD LONG SL 1.2500 TP 1.2650",
            "expected": "ParsedSignal with SL and TP"
        },
        {
            "name": "SHORT signal with open TP",
            "text": "GOLD SHORT SL 2660 leave it open",
            "expected": "ParsedSignal with no TP (open trade)"
        },
        {
            "name": "Bare signal (no SL)",
            "text": "US30 BUY",
            "expected": "Added to waiting room"
        },
        {
            "name": "LIMIT order",
            "text": "EURUSD BUY limit SL 1.0800 TP 1.0950",
            "expected": "ParsedSignal with order_type=LIMIT"
        },
        {
            "name": "Close in profit",
            "text": "CLOSE GBPUSD IN MASSIVE PROFIT",
            "expected": "ParsedManagement action=CLOSE_ALL"
        },
        {
            "name": "SL hit",
            "text": "GOLD STOP LOSS HIT",
            "expected": "ParsedManagement action=SL_HIT"
        },
        {
            "name": "Tighten SL",
            "text": "TIGHTEN STOP LOSS TO 2655",
            "expected": "ParsedManagement action=MODIFY_SL"
        },
        {
            "name": "Breakeven",
            "text": "MOVE TO BE",
            "expected": "ParsedManagement action=BREAKEVEN"
        },
        {
            "name": "Cancel order",
            "text": "CANCEL PENDING ORDER",
            "expected": "ParsedManagement action=CANCEL_PENDING"
        },
        {
            "name": "Implied close (profit announcement)",
            "text": "MASSIVE PROFIT GUYS! TAG ME WITH YOUR PROFIT",
            "expected": "ParsedManagement action=IMPLIED_CLOSE"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   Input: {test['text']}")
        print(f"   Expected: {test['expected']}")
        
        # Create mock message
        msg = MockMessage(
            id=2000 + i,
            chat_id=-1001182913499,
            date=datetime.now().timestamp()
        )
        
        # Try entry parsing
        signal = await plugin.parse_entry(msg, test['text'].lower())
        if signal:
            print(f"   ✓ Result: {signal}")
            continue
        
        # Try management parsing
        mgmt = await plugin.parse_management(msg, test['text'].lower())
        if mgmt:
            print(f"   ✓ Result: {mgmt}")
            continue
        
        # Check waiting room
        if plugin._waiting_room:
            print(f"   ✓ Result: Added to waiting room ({len(plugin._waiting_room)} entries)")
        else:
            print(f"   ✗ Result: No match")


async def main():
    """Run all parser tests."""
    print("\n🧪 Mirror Pupil v5.1 - Parser Test Suite\n")
    
    await test_billirichy_parser()
    await test_firepips_parser()
    
    print("\n\n" + "=" * 80)
    print("✓ All tests complete!")
    print("=" * 80)
    print("\nNext: Run 'python telegram_client.py' to test with real Telegram messages")
    print()


if __name__ == "__main__":
    asyncio.run(main())
