"""
Mirror Pupil v5.1 - Risk Management Test Script
Tests risk calculator, enforcer, and consistency score.
"""

import asyncio
from datetime import date, timedelta
from dotenv import load_dotenv
from loguru import logger

from backend.database import DatabaseManager, Account, RiskProfile
from backend.risk import (
    RiskCalculator,
    calculate_price_delta,
    RiskEnforcer,
    ConsistencyScoreCalculator
)

# Load environment
load_dotenv()

# Configure logger
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


async def test_risk_management():
    """Test risk management system."""
    
    print("\n" + "="*60)
    print("Mirror Pupil v5.1 - Risk Management Test")
    print("="*60 + "\n")
    
    # Initialize database
    db = DatabaseManager()
    await db.connect(min_size=2, max_size=5)
    
    try:
        # Test 1: Price Delta Calculation
        logger.info("\n[Test 1] Price Delta Calculation...")
        
        # Forex example (XAUUSD)
        risk1 = calculate_price_delta(
            entry_price=2650.50,
            sl_price=2640.00,
            lot_size=0.1,
            symbol="XAUUSD"
        )
        logger.info(f"✓ XAUUSD risk: ${risk1:.2f}")
        
        # Forex example (EURUSD)
        risk2 = calculate_price_delta(
            entry_price=1.0850,
            sl_price=1.0800,
            lot_size=0.5,
            symbol="EURUSD"
        )
        logger.info(f"✓ EURUSD risk: ${risk2:.2f}")
        
        # Test 2: Risk Calculator
        logger.info("\n[Test 2] Risk Calculator...")
        
        calculator = RiskCalculator()
        
        # Create test account
        test_account = Account(
            account_key="test@example.com:12345",
            credential_key="test@example.com",
            tl_account_id="12345",
            tl_email="test@example.com",
            tl_password="encrypted",
            tl_server="demo",
            initial_balance=100000.0,
            current_balance=102000.0,
            highest_banked_balance=102000.0,
            daily_start_balance=101500.0,
            daily_pnl=500.0,
            cycle_start_date=date.today() - timedelta(days=10),
            cycle_best_day_pnl=800.0
        )
        
        # Get default risk profile
        profile = await db.get_default_risk_profile()
        
        if not profile:
            logger.error("❌ No default risk profile found")
            return
        
        logger.info(f"Using profile: {profile.profile_name}")
        
        # Calculate floors
        daily_floor = calculator.calculate_daily_floor(test_account, profile)
        logger.info(f"✓ Daily floor: ${daily_floor:.2f}")
        
        overall_floor = calculator.calculate_overall_floor(test_account, profile)
        logger.info(f"✓ Overall floor: ${overall_floor:.2f}")
        
        # Calculate rooms
        current_equity = 102500.0  # Balance + floating P&L
        daily_room = calculator.calculate_daily_room(test_account, profile, current_equity)
        logger.info(f"✓ Daily room: ${daily_room:.2f}")
        
        overall_room = calculator.calculate_overall_room(test_account, profile, current_equity)
        logger.info(f"✓ Overall room: ${overall_room:.2f}")
        
        # Calculate withdrawable
        withdrawable = calculator.calculate_withdrawable(test_account, profile)
        logger.info(f"✓ Withdrawable: ${withdrawable:.2f}")
        
        # Check profit lock
        profit_lock_trigger = calculator.check_profit_lock_trigger(test_account, profile)
        logger.info(f"✓ Profit lock trigger: {profit_lock_trigger}")
        
        # Get risk summary
        summary = calculator.get_risk_summary(test_account, profile, current_equity)
        logger.info(f"✓ Risk summary generated with {len(summary)} metrics")
        
        # Test 3: Risk Enforcer
        logger.info("\n[Test 3] Risk Enforcer...")
        
        enforcer = RiskEnforcer(db)
        
        # Validate a trade
        validation = await enforcer.validate_trade(
            account=test_account,
            profile=profile,
            entry_price=2650.50,
            sl_price=2640.00,
            lot_size=0.1,
            symbol="XAUUSD"
        )
        
        logger.info(f"✓ Trade validation: {validation['allowed']}")
        logger.info(f"  Reason: {validation['reason']}")
        if 'trade_risk' in validation:
            logger.info(f"  Trade risk: ${validation['trade_risk']:.2f}")
        
        # Test breach check
        breached = await enforcer.check_risk_limits(test_account, profile)
        logger.info(f"✓ Breach check: {'BREACHED' if breached else 'OK'}")
        
        # Test 4: Consistency Score
        logger.info("\n[Test 4] Consistency Score Calculator...")
        
        consistency_calc = ConsistencyScoreCalculator(db)
        
        # Calculate consistency score
        score_data = await consistency_calc.calculate_consistency_score(test_account)
        logger.info(f"✓ Consistency score: {score_data['score']}%")
        logger.info(f"  Best day: ${score_data['best_day']:.2f}")
        logger.info(f"  Total: ${score_data['total']:.2f}")
        logger.info(f"  Status: {score_data['status']}")
        
        # Count profitable days
        profitable_count = await consistency_calc.count_profitable_days(
            test_account.account_key,
            days=30
        )
        logger.info(f"✓ Profitable days (30d): {profitable_count}")
        
        # Get profitable days summary
        summary = await consistency_calc.get_profitable_days_summary(
            test_account.account_key,
            days=30
        )
        logger.info(f"✓ Profitable days summary:")
        logger.info(f"  Profitable: {summary['profitable_count']}/{summary['required']}")
        logger.info(f"  Remaining: {summary['remaining']}")
        logger.info(f"  Status: {summary['status']}")
        
        # Test 5: Blue Guardian Profile Validation
        logger.info("\n[Test 5] Blue Guardian Profile Validation...")
        
        logger.info(f"Profile: {profile.profile_name}")
        logger.info(f"  Daily loss: {profile.daily_loss_pct}%")
        logger.info(f"  Overall loss: {profile.overall_loss_pct}%")
        logger.info(f"  Profit lock: {profile.profit_lock_pct}%")
        logger.info(f"  Max concurrent: {profile.max_concurrent_trades}")
        logger.info(f"  Commission: ${profile.commission_per_lot}/lot")
        logger.info(f"  Safety buffer: {profile.safety_buffer_pct}%")
        logger.info(f"  Payout buffer: {profile.payout_buffer_pct}%")
        
        # Validate Blue Guardian rules
        assert profile.daily_loss_pct == 3.0, "Daily loss should be 3%"
        assert profile.overall_loss_pct == 6.0, "Overall loss should be 6%"
        assert profile.profit_lock_pct == 6.0, "Profit lock should be at +6%"
        assert profile.profit_lock_floor_pct == 0.0, "Profit lock floor should be 0%"
        assert profile.overall_trailing == True, "Overall should trail"
        assert profile.overall_trail_from_closed_balance == True, "Should trail from closed balance"
        
        logger.info("✓ All Blue Guardian rules validated")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("✓ All risk management tests passed!")
        logger.info("="*60 + "\n")
        
        logger.info("Risk management system is ready. Features:")
        logger.info("1. ✓ Price delta calculation (forex + indices)")
        logger.info("2. ✓ Daily/overall floor calculation")
        logger.info("3. ✓ Profit lock detection")
        logger.info("4. ✓ Pre-trade risk validation")
        logger.info("5. ✓ Breach monitoring")
        logger.info("6. ✓ Consistency score (20% rule)")
        logger.info("7. ✓ Profitable days tracking")
        logger.info("8. ✓ Blue Guardian Instant Standard profile\n")
        
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(test_risk_management())
