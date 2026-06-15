#!/usr/bin/env python3
"""
Add account via API endpoint.
"""

import requests
import json

# API endpoint
API_URL = "http://127.0.0.1:8000"

# ===== FILL IN YOUR CREDENTIALS HERE =====
TL_EMAIL = "bonnieprincewill6@gmail.com"
TL_PASSWORD = "your_password_here"  # ← PUT YOUR ACTUAL PASSWORD HERE
TL_SERVER = "demo"  # "demo" or "live"
TL_PROP_FIRM = "HEROFX"
TL_ACCOUNT_ID = 2135871

# Account settings
DISPLAY_NAME = "Test"
INITIAL_BALANCE = 99711.54
RISK_PROFILE_ID = 1
# =========================================

if TL_PASSWORD == "your_password_here":
    print("❌ Please edit the script and add your password!")
    print("   Find the line: TL_PASSWORD = \"your_password_here\"")
    print("   And replace it with your actual password")
    exit(1)

# Account data
account_data = {
    "tl_email": TL_EMAIL,
    "tl_password": TL_PASSWORD,
    "tl_server": TL_SERVER,
    "tl_prop_firm": TL_PROP_FIRM,
    "tl_account_id": TL_ACCOUNT_ID,
    "display_name": DISPLAY_NAME,
    "initial_balance": INITIAL_BALANCE,
    "risk_profile_id": RISK_PROFILE_ID
}

print("=" * 60)
print("Adding Account via API")
print("=" * 60)
print()
print(f"📝 Account Details:")
print(f"   Email: {TL_EMAIL}")
print(f"   Server: {TL_SERVER}")
print(f"   Prop Firm: {TL_PROP_FIRM}")
print(f"   Account ID: {TL_ACCOUNT_ID}")
print()

try:
    # Make API request
    print(f"🔄 Sending request to {API_URL}/accounts...")
    response = requests.post(
        f"{API_URL}/accounts",
        json=account_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200 or response.status_code == 201:
        print("✅ Account added successfully!")
        print()
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Failed to add account")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ Could not connect to the API")
    print("   Make sure the backend is running on http://127.0.0.1:8000")
    print("   Start it with: py -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("Done!")
print("=" * 60)
print()
print("⚠️  SECURITY TIP: Delete or clear your password from this script file!")
