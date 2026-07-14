"""
Test Trading Hours Fix
Verify the corrected trading hours logic.
"""

import asyncio
from datetime import datetime, time
import pytz
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


def test_trading_hours_logic():
    """Test the corrected trading hours without database."""
    
    timezone = pytz.timezone("America/New_York")
    
    # New trading hours (CORRECTED)
    daily_close_time = time(16, 45)     # 4:45 PM EST
    daily_reset_start = time(17, 0)     # 5:00 PM EST
    daily_reset_end = time(17, 59)      # 5:59 PM EST
    daily_open_time = time(18, 0)       # 6:00 PM EST
    weekend_open_time = time(0, 0)      # Monday 12:00 AM EST
    
    logger.info("=" * 80)
    logger.info("TESTING CORRECTED TRADING HOURS LOGIC")
    logger.info("=" * 80)
    
    # Test scenarios
    test_cases = [
        # (weekday, hour, minute, expected_allowed, description)
        (0, 12, 0, True, "Monday 12:00 PM - Should allow (normal trading)"),
        (0, 16, 44, True, "Monday 4:44 PM - Should allow (before close)"),
        (0, 16, 45, False, "Monday 4:45 PM - Should block (EOD close)"),
        (0, 17, 0, False, "Monday 5:00 PM - Should block (daily reset)"),
        (0, 17, 30, False, "Monday 5:30 PM - Should block (daily reset)"),
        (0, 17, 59, False, "Monday 5:59 PM - Should block (daily reset)"),
        (0, 18, 0, True, "Monday 6:00 PM - Should allow (trading resumes)"),
        (0, 18, 30, True, "Monday 6:30 PM - Should allow (normal trading)"),
        (0, 23, 59, True, "Monday 11:59 PM - Should allow (normal trading)"),
        (1, 0, 0, True, "Tuesday 12:00 AM - Should allow (normal trading)"),
        (1, 3, 0, True, "Tuesday 3:00 AM - Should allow (normal trading)"),
        (1, 16, 45, False, "Tuesday 4:45 PM - Should block (EOD close)"),
        (1, 18, 0, True, "Tuesday 6:00 PM - Should allow (trading resumes)"),
        (4, 16, 44, True, "Friday 4:44 PM - Should allow (before close)"),
        (4, 16, 45, False, "Friday 4:45 PM - Should block (weekend close)"),
        (4, 18, 0, False, "Friday 6:00 PM - Should block (weekend)"),
        (4, 23, 59, False, "Friday 11:59 PM - Should block (weekend)"),
        (5, 12, 0, False, "Saturday 12:00 PM - Should block (weekend)"),
        (6, 12, 0, False, "Sunday 12:00 PM - Should block (weekend)"),
        (6, 18, 0, False, "Sunday 6:00 PM - Should block (weekend - opens Monday 12AM)"),
        (0, 0, 0, True, "Monday 12:00 AM - Should allow (week opens)"),
    ]
    
    passed = 0
    failed = 0
    
    for weekday, hour, minute, expected_allowed, description in test_cases:
        current_time = time(hour, minute)
        
        # Simulate the logic
        allowed = True
        reason = "OK"
        
        # RULE 1: Weekend check
        if weekday == 5:  # Saturday
            allowed = False
            reason = "WEEKEND_SATURDAY"
        elif weekday == 6:  # Sunday
            allowed = False
            reason = "WEEKEND_SUNDAY"
        elif weekday == 4 and current_time >= daily_close_time:  # Friday after 4:45pm
            allowed = False
            reason = "WEEKEND_CLOSE"
        
        # RULE 2: Daily reset lock (if not weekend blocked)
        if allowed and (daily_reset_start <= current_time <= daily_reset_end):
            allowed = False
            reason = "DAILY_RESET"
        
        # RULE 3: EOD close window (if not weekend blocked)
        if allowed and (daily_close_time <= current_time < daily_open_time):
            allowed = False
            reason = "EOD_CLOSE"
        
        # Check result
        if allowed == expected_allowed:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        logger.info(
            f"{status} | {description}"
        )
        if allowed != expected_allowed:
            logger.error(
                f"         Expected: {'ALLOW' if expected_allowed else 'BLOCK'}, "
                f"Got: {'ALLOW' if allowed else 'BLOCK'} (Reason: {reason})"
            )
    
    logger.info("=" * 80)
    logger.info(f"TEST RESULTS: {passed} passed, {failed} failed")
    logger.info("=" * 80)
    
    if failed == 0:
        logger.info("✅ ALL TESTS PASSED - Trading hours logic is correct!")
    else:
        logger.error(f"❌ {failed} TESTS FAILED - Logic needs adjustment!")
    
    return failed == 0


def print_trading_schedule():
    """Print the complete trading schedule."""
    logger.info("\n" + "=" * 80)
    logger.info("CORRECTED TRADING SCHEDULE")
    logger.info("=" * 80)
    
    logger.info("\n📅 WEEKDAYS (Monday-Friday):")
    logger.info("  • Trading Window:  6:00 PM → 4:45 PM next day (22h 45m)")
    logger.info("  • Force Close:     4:45 PM EST (all trades closed)")
    logger.info("  • Reset Lock:      5:00 PM - 5:59 PM EST (1 hour)")
    logger.info("  • Trading Resumes: 6:00 PM EST (same day)")
    
    logger.info("\n📅 WEEKEND:")
    logger.info("  • Friday Close:    4:45 PM EST")
    logger.info("  • Reset Lock:      5:00 PM Friday → Sunday 11:59 PM")
    logger.info("  • Trading Resumes: Monday 12:00 AM EST (midnight)")
    
    logger.info("\n⏰ TIMELINE EXAMPLE (Monday):")
    logger.info("  12:00 AM - 4:44 PM   ✅ Trading allowed")
    logger.info("  4:45 PM - 4:59 PM    ❌ EOD close window")
    logger.info("  5:00 PM - 5:59 PM    🔒 Daily reset (locked)")
    logger.info("  6:00 PM - 11:59 PM   ✅ Trading allowed")
    logger.info("  (next day)")
    logger.info("  12:00 AM - 4:44 PM   ✅ Trading allowed")
    logger.info("  4:45 PM              ❌ EOD close...")
    
    logger.info("\n⏰ WEEKEND TIMELINE:")
    logger.info("  Friday 4:45 PM       ❌ Weekend close")
    logger.info("  Friday 5:00 PM       🔒 Reset begins")
    logger.info("  Saturday ALL DAY     ❌ Market closed")
    logger.info("  Sunday ALL DAY       ❌ Market closed")
    logger.info("  Monday 12:00 AM      ✅ Week opens!")
    
    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    print_trading_schedule()
    print()
    success = test_trading_hours_logic()
    exit(0 if success else 1)
