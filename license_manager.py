"""
ZOQIRA License Manager — Key Generation & Validation System
Copyright (c) 2026 Zoqira. All Rights Reserved.

Allows admin to generate license keys for sale.
Customers activate their bot with a valid key via /activate command.
"""
import os
import json
import hmac
import hashlib
import base64
import time
import secrets
from datetime import datetime
from typing import Optional, Tuple

# ---- CONFIG ----
LICENSE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "license_data")

# Master secret — CHANGE THIS to your own secret key
# Keep this PRIVATE. Only you (the seller) should know it.
# The bot only needs LICENSE_PUBLIC_SALT for basic validation.
MASTER_SECRET = os.getenv("ZOQIRA_MASTER_SECRET", "zoqira-master-secret-change-me-2026")

# Public salt embedded in bot — used to verify keys without exposing master secret
LICENSE_PUBLIC_SALT = "ZQRA-OMEGA-v2.0-KHMER-BOT"


def _ensure_dir():
    os.makedirs(LICENSE_DIR, exist_ok=True)


def _derive_key(secret: str, salt: str) -> bytes:
    """Derive a signing key from secret + salt."""
    return hashlib.pbkdf2_hmac("sha256", secret.encode(), salt.encode(), 100000, dklen=32)


def generate_key(duration_days: int = 30, customer_id: str = "", price: float = 0.0) -> str:
    """
    Generate a cryptographically signed license key.

    Args:
        duration_days: How many days the key is valid for
        customer_id: Optional customer identifier
        price: Price charged (for admin records)

    Returns:
        License key string: ZOQIRA-XXXX-XXXX-XXXX
    """
    expiry_ts = int(time.time()) + (duration_days * 86400)
    unique_id = secrets.token_hex(4)  # Make each key unique

    # Payload: expiry timestamp + customer hash + unique ID
    payload = f"{expiry_ts}:{customer_id}:{int(price * 100)}:{unique_id}"
    payload_b64 = base64.b32encode(payload.encode()).decode().rstrip("=")

    # Sign with master secret
    signing_key = _derive_key(MASTER_SECRET, LICENSE_PUBLIC_SALT)
    signature = hmac.new(signing_key, payload.encode(), hashlib.sha256).hexdigest()[:12]

    # Format: ZOQIRA-PPPPPP-SSSSSS (payload + signature)
    combined = f"{payload_b64}{signature}"

    # Split into readable groups
    key_body = combined.upper()
    group_size = len(key_body) // 3
    part1 = key_body[:group_size]
    part2 = key_body[group_size:group_size * 2]
    part3 = key_body[group_size * 2:]

    return f"ZOQIRA-{part1}-{part2}-{part3}"


def validate_key(key: str) -> Tuple[bool, str, Optional[int]]:
    """
    Validate a license key and return (is_valid, message, expiry_timestamp).

    Returns:
        (True, "Valid until YYYY-MM-DD", expiry_ts) if valid
        (False, "Error message", None) if invalid
    """
    key = key.strip().upper()

    # Normalize: remove spaces, accept with or without ZOQIRA- prefix
    if not key.startswith("ZOQIRA-"):
        return False, "❌ ទម្រង់ License Key មិនត្រឹមត្រូវ។ ត្រូវចាប់ផ្តើមដោយ ZOQIRA-", None

    key_body = key[7:]  # Remove "ZOQIRA-"
    key_body = key_body.replace("-", "").replace(" ", "")

    if len(key_body) < 20:
        return False, "❌ License Key ខ្លីពេក។ សូមពិនិត្យឡើងវិញ។", None

    try:
        # Extract signature (last 12 chars) and payload (the rest)
        signature = key_body[-12:].lower()
        payload_b64 = key_body[:-12]

        # Add padding for base32 decode
        padding = 8 - (len(payload_b64) % 8)
        if padding != 8:
            payload_b64 += "=" * padding

        payload = base64.b32decode(payload_b64).decode()

        # Verify signature
        signing_key = _derive_key(MASTER_SECRET, LICENSE_PUBLIC_SALT)
        expected_sig = hmac.new(signing_key, payload.encode(), hashlib.sha256).hexdigest()[:12]

        if not hmac.compare_digest(signature, expected_sig):
            return False, "❌ License Key មិនត្រឹមត្រូវ (signature mismatch)។ សូមទាក់ទងអ្នកលក់។", None

        # Parse payload: expiry_ts:customer_id:price_cents
        parts = payload.split(":")
        if len(parts) < 1:
            return False, "❌ License Key ខូច។", None

        expiry_ts = int(parts[0])
        customer_id = parts[1] if len(parts) > 1 else ""
        price_cents = float(parts[2]) if len(parts) > 2 else 0

        # Check expiry
        now = int(time.time())
        if now > expiry_ts:
            expiry_date = datetime.fromtimestamp(expiry_ts).strftime("%d/%m/%Y")
            return False, f"⏰ License Key ផុតកំណត់ហើយ (ថ្ងៃ {expiry_date})។ សូមទិញថ្មី។", None

        # Valid!
        expiry_date = datetime.fromtimestamp(expiry_ts).strftime("%d/%m/%Y %H:%M")
        days_left = (expiry_ts - now) // 86400
        msg = f"✅ License មានសុពលភាព! ផុតកំណត់ថ្ងៃ {expiry_date} ({days_left} ថ្ងៃទៀត)"

        return True, msg, expiry_ts

    except Exception as e:
        return False, f"❌ មានបញ្ហាក្នុងការផ្ទៀងផ្ទាត់ License Key: {e}", None


def get_activated_license() -> Optional[dict]:
    """Get the currently activated license info."""
    _ensure_dir()
    license_file = os.path.join(LICENSE_DIR, "activated.json")
    if not os.path.exists(license_file):
        return None
    try:
        with open(license_file, "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_activated_license(key: str, expiry_ts: int, message: str) -> bool:
    """Save an activated license to disk."""
    _ensure_dir()
    license_file = os.path.join(LICENSE_DIR, "activated.json")
    try:
        data = {
            "key_masked": key[:15] + "..." + key[-5:],
            "key_hash": hashlib.sha256(key.encode()).hexdigest(),
            "expiry_ts": expiry_ts,
            "expiry_date": datetime.fromtimestamp(expiry_ts).strftime("%Y-%m-%d %H:%M:%S"),
            "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": message,
        }
        with open(license_file, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def is_license_valid() -> Tuple[bool, str]:
    """
    Check if the bot has a valid license.
    Returns (True, message) or (False, message).
    """
    lic = get_activated_license()
    if not lic:
        return False, (
            "🔐 *មិនទាន់មាន License Key*\n\n"
            "សូមទិញ License Key ពី @TradekhmerAI ឬទំនាក់ទំនងអ្នកលក់។\n"
            "បន្ទាប់មកប្រើពាក្យបញ្ជា:\n"
            "`/activate ZOQIRA-XXXX-XXXX-XXXX`\n\n"
            "⚠️ បើគ្មាន License, bot នឹងដំណើរការបាន 7 ថ្ងៃសាកល្បង។"
        )

    expiry_ts = lic.get("expiry_ts", 0)
    now = int(time.time())

    if now > expiry_ts:
        return False, (
            "⏰ *License ផុតកំណត់ហើយ!*\n\n"
            f"ផុតកំណត់ថ្ងៃ: {lic.get('expiry_date', 'Unknown')}\n"
            "សូមទិញ License Key ថ្មីពី @TradekhmerAI\n"
            "រួចប្រើ `/activate <key>` ដើម្បីបន្តប្រើប្រាស់។"
        )

    days_left = (expiry_ts - now) // 86400
    return True, f"✅ License មានសុពលភាព — {days_left} ថ្ងៃទៀត (ដល់ {lic.get('expiry_date', '?')})"


def check_license_on_startup():
    """Print license status on bot startup."""
    valid, msg = is_license_valid()
    if valid:
        print(f"🔐 LICENSE: {msg}")
    else:
        print(f"⚠️ LICENSE: No valid license found. Running in trial mode (7 days).")
        print(f"   Activate: /activate ZOQIRA-XXXX-XXXX-XXXX")
    return valid
