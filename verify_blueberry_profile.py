"""
Verify Blueberry Funded risk profile
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from backend.database.manager import DatabaseManager

async def verify_profile():
    db = DatabaseManager()
    
    print("\n" + "="*70)
    print("BLUEBERRY FUNDED PROFILE VERIFICATION")
    print("="*70)
    
    # Get the profile
    profile = await db.get_default_risk_profile()
    
    if not profile:
        print("\n❌ NO DEFAULT PROFILE FOUND!")
        return
    
    print(f"\n✓ Default Profile: {profile.profile_name}")
    print(f"  Profile ID: {profile.profile_id}")
    print("\n" + "-"*70)
    print("SETTINGS:")
    print("-"*70)
    print(f"  Max Risk Per Trade:        {profile.max_risk_per_trade_pct}%")
    print(f"  Daily Loss Limit:          {profile.daily_loss_pct}%")
    print(f"  Daily Trailing:            {profile.daily_trailing}")
    print(f"  Overall Loss Limit:        {profile.overall_loss_pct}%")
    print(f"  Overall Trailing:          {profile.overall_trailing}")
    print(f"  Trail From Closed Balance: {profile.overall_trail_from_closed_balance}")
    print(f"  Profit Lock:               {profile.profit_lock_pct}")
    print(f"  Profit Lock Floor:         {profile.profit_lock_floor_pct}")
    print(f"  Payout Buffer:             {profile.payout_buffer_pct}%")
    print(f"  Max Concurrent Trades:     {profile.max_concurrent_trades}")
    print(f"  Commission Per Lot:        ${profile.commission_per_lot}")
    print(f"  Safety Buffer:             {profile.safety_buffer_pct}%")
    
    print("\n" + "-"*70)
    print("VERIFICATION:")
    print("-"*70)
    
    checks = [
        (profile.profile_name == "Blueberry Funded", "Profile name = 'Blueberry Funded'"),
        (profile.max_risk_per_trade_pct == 1.0, "Max risk = 1%"),
        (profile.daily_loss_pct == 4.0, "Daily loss = 4%"),
        (profile.daily_trailing == False, "Daily NOT trailing (static)"),
        (profile.overall_loss_pct == 6.0, "Overall loss = 6%"),
        (profile.overall_trailing == False, "Overall NOT trailing (static)"),
        (profile.overall_trail_from_closed_balance == False, "NOT from closed balance"),
        (profile.profit_lock_pct is None, "NO profit lock"),
        (profile.profit_lock_floor_pct is None, "NO profit lock floor"),
        (profile.payout_buffer_pct == 0.0, "NO payout buffer (0%)"),
        (profile.max_concurrent_trades == 3, "Max 3 concurrent trades"),
        (profile.commission_per_lot == 7.0, "Commission = $7"),
        (profile.safety_buffer_pct == 0.5, "Safety buffer = 0.5%"),
    ]
    
    all_passed = True
    for passed, check in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL CHECKS PASSED - BLUEBERRY FUNDED CONFIGURED CORRECTLY")
    else:
        print("❌ SOME CHECKS FAILED - REVIEW SETTINGS ABOVE")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(verify_profile())
