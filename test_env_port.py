#!/usr/bin/env python
"""Test script to verify API_PORT is loaded correctly from .env"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).parent / ".env"
print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

load_dotenv(env_path)

api_port = os.getenv("API_PORT")
print(f"\nAPI_PORT value: {api_port}")
print(f"API_PORT type: {type(api_port)}")

if api_port:
    print(f"API_PORT as int: {int(api_port)}")
else:
    print("API_PORT not set in environment!")

# Check all env vars starting with API_
print("\nAll API_* environment variables:")
for key, value in os.environ.items():
    if key.startswith("API_"):
        print(f"  {key} = {value}")
