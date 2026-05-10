"""
DigiKey 3-legged OAuth helper.

Endpoints (production) per https://developer.digikey.com/tutorials-and-resources/oauth-20-3-legged-flow
  Authorize: GET  https://api.digikey.com/v1/oauth2/authorize
  Token:     POST https://api.digikey.com/v1/oauth2/token

Setup the user must do once in the DigiKey developer portal:
  - Register a Production app and grant it the "MyLists" product subscription.
  - Add `DIGIKEY_REDIRECT_URI` (e.g. https://localhost:8000/digikey/callback)
    as an allowed redirect URI. It MUST match exactly, including any trailing
    slash, and MUST be https:// — DigiKey rejects http:// callbacks.

For local dev, run uvicorn with a self-signed cert so the callback URL is
reachable over https. See README.

This module only handles the token dance. Third-party MyLists (no auth) live in
`digikey_lists.py`. Token storage is in-memory and keyed by an opaque
`session_id` cookie set in `api.py`.
"""
from __future__ import annotations

import os
import secrets
import time
from threading import Lock
from typing import Optional
from urllib.parse import urlencode

import requests

from .env import load_connector_env

load_connector_env()

AUTHORIZE_URL = "https://api.digikey.com/v1/oauth2/authorize"
TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
TIMEOUT = 15

# Default callback when DIGIKEY_REDIRECT_URI isn't set. The user MUST register
# this same string in the DigiKey portal — DigiKey requires an exact match.
DEFAULT_REDIRECT_URI = "https://localhost:8000/digikey/callback"


class DigiKeyOAuthError(RuntimeError):
    """Raised when DigiKey OAuth credentials or response are bad."""


def _client_id() -> str:
    cid = os.getenv("DIGIKEY_CLIENT_ID")
    if not cid:
        raise DigiKeyOAuthError("DIGIKEY_CLIENT_ID is not set in env.")
    return cid


def _client_secret() -> str:
    sec = os.getenv("DIGIKEY_CLIENT_SECRET")
    if not sec:
        raise DigiKeyOAuthError("DIGIKEY_CLIENT_SECRET is not set in env.")
    return sec


def redirect_uri() -> str:
    """Callback URL sent to DigiKey — must match the portal exactly (no stray spaces)."""
    raw = (os.getenv("DIGIKEY_REDIRECT_URI") or "").strip()
    return raw or DEFAULT_REDIRECT_URI


def build_authorize_url(state: str) -> str:
    """Build the URL to redirect the end user to so they can grant the app
    access to their DigiKey account."""
    params = {
        "response_type": "code",
        "client_id": _client_id(),
        "redirect_uri": redirect_uri(),
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange a one-time authorization code (valid for 60 s) for an access
    + refresh token pair. Returns the raw token JSON plus an `expires_at`
    epoch second computed from `expires_in`."""
    data = {
        "code": code,
        "client_id": _client_id(),
        "client_secret": _client_secret(),
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=TIMEOUT)
    if resp.status_code != 200:
        raise DigiKeyOAuthError(
            f"DigiKey token exchange failed ({resp.status_code}): {resp.text}"
        )
    payload = resp.json()
    payload["expires_at"] = int(time.time()) + int(payload.get("expires_in", 1800)) - 30
    return payload


def refresh_access_token(refresh_token: str) -> dict:
    """Use a stored refresh token to mint a new access token (and a new
    refresh token — DigiKey rotates them on every refresh)."""
    data = {
        "client_id": _client_id(),
        "client_secret": _client_secret(),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=TIMEOUT)
    if resp.status_code != 200:
        raise DigiKeyOAuthError(
            f"DigiKey token refresh failed ({resp.status_code}): {resp.text}"
        )
    payload = resp.json()
    payload["expires_at"] = int(time.time()) + int(payload.get("expires_in", 1800)) - 30
    return payload


# ---------------------------------------------------------------------------
# Tiny in-memory session store. Good for a hackathon demo, NOT for prod.
# ---------------------------------------------------------------------------

_SESSIONS: dict[str, dict] = {}
_PENDING_STATES: dict[str, float] = {}  # state -> created_at, for CSRF check
_LOCK = Lock()
_STATE_TTL_SEC = 600


def new_session_id() -> str:
    return secrets.token_urlsafe(24)


def new_oauth_state() -> str:
    state = secrets.token_urlsafe(16)
    with _LOCK:
        _prune_states_locked()
        _PENDING_STATES[state] = time.time()
    return state


def consume_oauth_state(state: str) -> bool:
    with _LOCK:
        _prune_states_locked()
        return _PENDING_STATES.pop(state, None) is not None


def _prune_states_locked() -> None:
    now = time.time()
    stale = [s for s, t in _PENDING_STATES.items() if now - t > _STATE_TTL_SEC]
    for s in stale:
        _PENDING_STATES.pop(s, None)


def store_tokens(session_id: str, tokens: dict) -> None:
    with _LOCK:
        _SESSIONS[session_id] = tokens


def get_tokens(session_id: str) -> Optional[dict]:
    with _LOCK:
        return _SESSIONS.get(session_id)


def clear_tokens(session_id: str) -> None:
    with _LOCK:
        _SESSIONS.pop(session_id, None)


def get_valid_access_token(session_id: str) -> Optional[str]:
    """Return a non-expired access token for this session, refreshing if
    needed. Returns None if the session is unknown or refresh fails."""
    tokens = get_tokens(session_id)
    if not tokens:
        return None
    if int(time.time()) < int(tokens.get("expires_at", 0)):
        return tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    if not refresh:
        return None
    try:
        new_tokens = refresh_access_token(refresh)
    except DigiKeyOAuthError:
        return None
    store_tokens(session_id, new_tokens)
    return new_tokens.get("access_token")
