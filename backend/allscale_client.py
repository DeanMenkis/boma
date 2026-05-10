"""
AllScale stablecoin checkout client.

Implements HMAC-SHA256 request signing per AllScale API docs:
  https://docs.allscale.io

Auth headers required on every request:
  X-API-Key    : API key
  X-Timestamp  : Unix seconds (must be within ±5 min of server)
  X-Nonce      : Random UUID (single-use)
  X-Signature  : v1=<Base64(HMAC-SHA256(secret, canonical_string))>

Canonical string (newline-joined):
  METHOD
  /path
  query_string_or_empty
  timestamp
  nonce
  hex(sha256(request_body_or_empty))
"""

import hashlib
import hmac
import json
import os
import time
import uuid
from base64 import b64encode
from typing import Optional
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://openapi.allscale.io"
TIMEOUT = 10

# Stablecoin enum (from AllScale docs)
USDT = 1
USDC = 2

# Terminal paid state
STATUS_CONFIRMED = 20
TERMINAL_STATES = {-4, -3, -2, -1, 20}

STATUS_NAMES = {
    -4: "CANCELED",
    -3: "UNDERPAID",
    -2: "REJECTED",
    -1: "FAILED",
    1: "CREATED",
    2: "VIEWED",
    3: "TEMP_WALLET_RECEIVED",
    10: "ON_CHAIN",
    20: "CONFIRMED",
}


def _sign_request(method: str, path: str, query: str, body_bytes: bytes) -> dict:
    """Build the four HMAC auth headers for an AllScale request."""
    api_key = os.environ["ALLSCALE_API_KEY"]
    api_secret = os.environ["ALLSCALE_API_SECRET"]

    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    body_hash = hashlib.sha256(body_bytes).hexdigest()

    canonical = "\n".join([method, path, query, timestamp, nonce, body_hash])
    signature = b64encode(
        hmac.new(api_secret.encode(), canonical.encode(), hashlib.sha256).digest()
    ).decode()

    return {
        "X-API-Key": api_key,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": f"v1={signature}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, body: Optional[dict] = None) -> dict:
    """Make a signed request to the AllScale API. Raises on non-2xx."""
    url = BASE_URL + path
    parsed = urlparse(url)
    query = parsed.query or ""
    body_bytes = json.dumps(body).encode() if body else b""

    headers = _sign_request(method.upper(), path, query, body_bytes)
    resp = requests.request(
        method,
        url,
        headers=headers,
        data=body_bytes if body_bytes else None,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def create_payment_link(
    amount_usd: float,
    order_id: str,
    description: str,
    success_url: Optional[str] = None,
) -> dict:
    """
    Create an AllScale checkout intent for the given USD amount.

    Returns:
        {
            "payment_url": str,
            "intent_id": str,
            "status": str,
            "raw": dict,
        }
    """
    # AllScale uses cents (integer); USDC is a stablecoin so 1 USD = 100 cents
    amount_cents = int(round(amount_usd * 100))

    payload = {
        "stable_coin": USDC,
        "amount_cents": amount_cents,
        "order_id": order_id,
        "order_description": description,
    }
    if success_url:
        payload["redirect_url"] = success_url

    raw = _request("POST", "/v1/checkout_intents/", body=payload)
    p = raw["payload"]

    return {
        "payment_url": p["checkout_url"],
        "intent_id": p["allscale_checkout_intent_id"],
        "status": "CREATED",
        "raw": raw,
    }


def get_payment_status(intent_id: str) -> dict:
    """
    Fetch the current status of a checkout intent.

    Returns:
        {
            "status": str,   # e.g. "CONFIRMED", "ON_CHAIN", "CREATED"
            "code": int,     # raw integer status code
            "raw": dict,
        }
    """
    raw = _request("GET", f"/v1/checkout_intents/{intent_id}/status")
    code = raw["payload"]
    name = STATUS_NAMES.get(code, f"UNKNOWN({code})")
    return {"status": name, "code": code, "raw": raw}


def is_paid(intent_id: str) -> bool:
    """Return True if the checkout intent has reached the CONFIRMED terminal state."""
    result = get_payment_status(intent_id)
    return result["code"] == STATUS_CONFIRMED


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    print("=== AllScale smoke test ===\n")

    # 1. Confirm API key works via test ping
    print("1. Pinging test route...")
    ping = _request("GET", "/v1/test/ping")
    assert ping.get("code") == 0, f"Ping failed: {ping}"
    print(f"   Ping OK: {ping['payload']}\n")

    # 2. Create a $5 USDC checkout intent
    print("2. Creating $5 USDC checkout intent...")
    result = create_payment_link(
        amount_usd=5.00,
        order_id="boma-smoke-001",
        description="BOMA smoke test — $5 hardware order",
        success_url="http://localhost:3000/success",
    )
    intent_id = result["intent_id"]
    payment_url = result["payment_url"]
    print(f"   Intent ID : {intent_id}")
    print(f"   Payment URL: {payment_url}\n")

    # 3. Poll status once
    print("3. Polling status...")
    status = get_payment_status(intent_id)
    print(f"   Status: {status['status']} (code={status['code']})\n")

    print("=== Done ===")
    print(f"\nOpen this URL to complete payment:\n  {payment_url}\n")
    sys.exit(0)
