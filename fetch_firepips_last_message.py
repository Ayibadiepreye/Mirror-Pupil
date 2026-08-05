# -*- coding: utf-8 -*-
"""
fetch_firepips_last_message.py
──────────────────────────────
Fetches the last N messages from the Firepips Telegram channel and shows:
  - Full message structure (text / caption / photo / video / etc.)
  - Whether the bot's parser would recognise it as a signal or management action
  - Why it was silently ignored if the parser returned None

Run once, reads the existing TDLib session (no new auth needed if already logged in).

Usage:
    python fetch_firepips_last_message.py          # last 5 messages
    python fetch_firepips_last_message.py 20       # last 20 messages
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
FIREPIPS_CHANNEL_ID = -1001182913499
FETCH_COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 5

# ──────────────────────────────────────────────────────────────────────────────
# Minimal TDLib helpers (no pytdbot monkey-patches needed for fetch-only use)
# ──────────────────────────────────────────────────────────────────────────────
from pytdbot import Client
from pytdbot.types import LogStreamFile, Update

# Apply the same patches used in the main client so pytdbot doesn't crash
import pytdbot.utils.obj_encoder as obj_encoder
import pytdbot.utils as pytdbot_utils
import pytdbot.client as pytdbot_client

_orig = obj_encoder.dict_to_obj

def _safe_dict_to_obj(d, client=None):
    try:
        return _orig(d, client)
    except (AttributeError, KeyError):
        return None

obj_encoder.dict_to_obj = _safe_dict_to_obj
pytdbot_utils.dict_to_obj = _safe_dict_to_obj
pytdbot_client.dict_to_obj = _safe_dict_to_obj


# ──────────────────────────────────────────────────────────────────────────────
# Parser imports (re-use the actual bot logic)
# ──────────────────────────────────────────────────────────────────────────────
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(backend_path))

from backend.channels.firepips.entry import parse_entry_signal
from backend.channels.firepips.management import parse_management_action
from backend.channels.base import ChannelPlugin  # for _extract_text / _clean_text


class _Extractor(ChannelPlugin):
    """Thin shim just to access the base class helpers."""
    @property
    def signal_prefix(self): return 'F'
    def normalize_symbol(self, raw): return None
    async def parse_entry(self, m, t): return None
    async def parse_management(self, m, t): return None

_extractor = _Extractor(FIREPIPS_CHANNEL_ID, "Firepips")


# ──────────────────────────────────────────────────────────────────────────────
# Waiting-room stub (parse_entry_signal needs a callback)
# ──────────────────────────────────────────────────────────────────────────────
_bare_signals_captured = []

def _waiting_room_cb(bare_signal):
    _bare_signals_captured.append(bare_signal)


# ──────────────────────────────────────────────────────────────────────────────
# Message inspector
# ──────────────────────────────────────────────────────────────────────────────
def _describe_content(message) -> dict:
    """Return a human-readable summary of message content type and text."""
    info = {
        "msg_id": message.id,
        "date": datetime.fromtimestamp(message.date).strftime("%Y-%m-%d %H:%M:%S"),
        "content_type": "unknown",
        "text": None,
        "caption": None,
        "media_type": None,
        "has_photo": False,
        "has_video": False,
        "has_document": False,
        "reply_to_msg_id": getattr(message, "reply_to_message_id", None),
        "edit_date": getattr(message, "edit_date", None),
    }

    if not hasattr(message, "content"):
        info["content_type"] = "no_content_attr"
        return info

    content = message.content
    ctype = type(content).__name__

    info["content_type"] = ctype

    # Text message
    if hasattr(content, "text"):
        t = content.text
        info["text"] = t.text if hasattr(t, "text") else str(t)

    # Photo with caption
    if hasattr(content, "photo"):
        info["has_photo"] = True
        info["media_type"] = "photo"

    # Video with caption
    if hasattr(content, "video"):
        info["has_video"] = True
        info["media_type"] = "video"

    # Document
    if hasattr(content, "document"):
        info["has_document"] = True
        info["media_type"] = "document"

    # Caption (on photos, videos, documents)
    if hasattr(content, "caption"):
        cap = content.caption
        info["caption"] = cap.text if hasattr(cap, "text") else str(cap)

    return info


async def _analyse_message(message) -> dict:
    """Run the message through the actual bot parsers and report."""
    raw_text = _extractor._extract_text(message)
    clean_text = _extractor._clean_text(raw_text) if raw_text else ""

    result = {
        "raw_text": raw_text,
        "clean_text": clean_text,
        "parser_result": None,
        "parser_type": None,
        "ignored_reason": None,
        "bare_signal": None,
    }

    if not raw_text:
        result["ignored_reason"] = (
            "NO TEXT — message has no text and no caption. "
            "This is the most common reason the bot stays silent on photo/sticker messages."
        )
        return result

    # Try entry parser
    _bare_signals_captured.clear()
    entry = await parse_entry_signal(message, clean_text, FIREPIPS_CHANNEL_ID, _waiting_room_cb)

    if _bare_signals_captured:
        bs = _bare_signals_captured[0]
        result["parser_type"] = "entry (BARE — added to waiting room)"
        result["bare_signal"] = {
            "symbol": bs.symbol,
            "direction": bs.direction,
            "expires_at": str(bs.expires_at),
        }
        return result

    if entry:
        result["parser_type"] = "entry (COMPLETE)"
        result["parser_result"] = str(entry)
        return result

    # Try management parser
    mgmt = await parse_management_action(message, clean_text, FIREPIPS_CHANNEL_ID)
    if mgmt:
        result["parser_type"] = "management"
        result["parser_result"] = str(mgmt)
        return result

    # Nothing matched — diagnose why
    from backend.channels.firepips.entry import detect_direction, detect_symbol, extract_sl
    direction = detect_direction(clean_text)
    symbol = detect_symbol(clean_text)
    sl = extract_sl(clean_text)

    reasons = []
    if not direction:
        reasons.append("no direction keyword (buy/sell/long/short)")
    if not symbol:
        reasons.append("no recognisable symbol")
    if direction and symbol and sl is None:
        reasons.append("has direction+symbol but no SL — would go to waiting room, but parse_entry returned None (check for edge-case in parser)")

    result["ignored_reason"] = "; ".join(reasons) if reasons else "passed direction+symbol+SL checks but entry parser returned None (check logs)"
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
async def main():
    api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    phone = os.getenv("TELEGRAM_PHONE", "")
    encryption_key = os.getenv("TDLIB_ENCRYPTION_KEY", "")
    files_dir = os.getenv("TDLIB_FILES_DIR", "./tdlib_data")

    if not all([api_id, api_hash, phone, encryption_key]):
        print("❌ Missing env vars: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, TDLIB_ENCRYPTION_KEY")
        return

    print(f"Connecting to Telegram (reusing session in {files_dir})...")

    client = Client(
        api_id=api_id,
        api_hash=api_hash,
        database_encryption_key=encryption_key,
        files_directory=str(files_dir),
        td_verbosity=0,
        td_log=LogStreamFile(str(Path(files_dir) / "tdlib_fetch.log")),
        user_bot=True,
    )

    auth_done = asyncio.Event()

    @client.on_updateAuthorizationState()
    async def on_auth(c: Client, update: Update):
        state = update.authorization_state.getType()
        print(f"  Auth state: {state}")
        if state == "authorizationStateReady":
            auth_done.set()
        elif state == "authorizationStateWaitPhoneNumber":
            await c.setAuthenticationPhoneNumber(phone_number=phone)
        elif state == "authorizationStateWaitCode":
            code = input("Enter Telegram auth code: ").strip()
            await c.checkAuthenticationCode(code=code)
        elif state == "authorizationStateWaitPassword":
            pw = input("Enter 2FA password: ").strip()
            await c.checkAuthenticationPassword(password=pw)
        elif state in ("authorizationStateLoggingOut", "authorizationStateClosed",
                       "authorizationStateClosing"):
            print(f"  ⚠️  Session state: {state}")

    await client.start()

    # Give TDLib a moment to emit the cached auth state
    print("Waiting for authorization state (up to 30s)...")
    try:
        await asyncio.wait_for(auth_done.wait(), timeout=30)
    except asyncio.TimeoutError:
        # If already authorized, TDLib may emit authorizationStateReady very quickly
        # but sometimes the event fires before our handler registers.
        # Try calling getMe() directly to check.
        print("  Auth event timed out — trying getMe() directly...")
        try:
            me = await asyncio.wait_for(client.getMe(), timeout=10)
            if me and hasattr(me, 'id'):
                print(f"  ✓ Already authenticated as user ID {me.id}")
            else:
                print("❌ Not authenticated and auth timed out. Run the main bot first to establish a session.")
                await client.stop()
                return
        except Exception as e:
            print(f"❌ Auth timed out and getMe() failed: {e}")
            await client.stop()
            return

    print(f"✓ Connected. Fetching last {FETCH_COUNT} messages from Firepips ({FIREPIPS_CHANNEL_ID})...\n")

    # getChatHistory returns messages newest-first
    history = await client.getChatHistory(
        chat_id=FIREPIPS_CHANNEL_ID,
        limit=FETCH_COUNT,
        offset=0,
        from_message_id=0,
        only_local=False,
    )

    messages = getattr(history, "messages", []) or []

    if not messages:
        print("⚠️  No messages returned. Possible reasons:")
        print("   1. The bot account is not a member of the Firepips channel")
        print("   2. The channel ID is wrong")
        print("   3. TDLib hasn't synced this chat yet (try running the main bot first)")
        await client.stop()
        return

    print(f"{'─'*70}")
    for msg in messages:
        content_info = _describe_content(msg)
        analysis = await _analyse_message(msg)

        print(f"MSG ID   : {content_info['msg_id']}")
        print(f"DATE     : {content_info['date']}")
        print(f"TYPE     : {content_info['content_type']}")
        if content_info["media_type"]:
            print(f"MEDIA    : {content_info['media_type']}")
        if content_info["text"]:
            print(f"TEXT     : {content_info['text'][:300]}")
        if content_info["caption"]:
            print(f"CAPTION  : {content_info['caption'][:300]}")
        if content_info["reply_to_msg_id"]:
            print(f"REPLY_TO : {content_info['reply_to_msg_id']}")
        print()
        print(f"  RAW TEXT  : {analysis['raw_text'][:200] if analysis['raw_text'] else '(none)'}")
        print(f"  CLEAN TEXT: {analysis['clean_text'][:200] if analysis['clean_text'] else '(none)'}")
        if analysis["parser_type"]:
            print(f"  ✅ PARSED AS : {analysis['parser_type']}")
            if analysis["parser_result"]:
                print(f"  RESULT      : {analysis['parser_result']}")
            if analysis["bare_signal"]:
                print(f"  BARE SIGNAL : {analysis['bare_signal']}")
        else:
            print(f"  ❌ IGNORED — {analysis['ignored_reason']}")
        print(f"{'─'*70}")

    await client.stop()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
