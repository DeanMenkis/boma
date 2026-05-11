#!/usr/bin/env python3
"""
One-shot DigiKey OAuth bootstrap.

Why this exists
---------------
The `digikey-api` library we use for product search has its callback URL
**hardcoded** to ``https://localhost:8139/digikey_callback`` and runs a tiny
HTTPS server there for the OAuth dance. That URL is rarely what's registered
in a DigiKey developer portal app — most BOMA users register
``https://localhost:8000/digikey/callback`` (the same port + path the BOMA
backend's `/digikey/callback` route uses).

This script:
1. Generates a self-signed cert for ``localhost``.
2. Spins up a minimal HTTPS server on ``https://localhost:8000`` that listens
   for ``/digikey/callback?code=...``.
3. Opens your browser at DigiKey's consent screen with the correct
   ``redirect_uri`` (matches your portal).
4. Catches the redirect, exchanges the code for access + refresh tokens via
   ``bom_supplier_connector.digikey_oauth.exchange_code``.
5. Writes those tokens into
   ``{DIGIKEY_STORAGE_PATH}/token_storage.json`` in the format the
   ``digikey-api`` library reads from. On its next call, the library will load
   the existing tokens (refreshing automatically) and skip its own
   :8139 OAuth flow entirely.

Run once:
  # Stop the backend first so :8000 is free.
  python bom_supplier_connector/setup_digikey_token.py

Then set ``BOMA_USE_MOCK_CATALOG=0`` in ``.env`` and restart the backend.
"""
from __future__ import annotations

import http.server
import json
import os
import ssl
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# `bom_supplier_connector.__init__` loads `<repo>/.env` for us.
from bom_supplier_connector import digikey_oauth  # noqa: E402

CALLBACK_HOST = "localhost"
CALLBACK_PORT = 8000
CALLBACK_PATH = "/digikey/callback"

PACKAGE_DIR = Path(__file__).resolve().parent
CACHE_DIR = Path(
    os.getenv("DIGIKEY_STORAGE_PATH")
    or str(PACKAGE_DIR / "cache")
).resolve()
CERT_FILE = CACHE_DIR / "boma-localhost-cert.pem"
KEY_FILE = CACHE_DIR / "boma-localhost-key.pem"
TOKEN_FILE = CACHE_DIR / "token_storage.json"


def ensure_cert() -> None:
    """Make sure we have a self-signed cert for ``localhost`` that's valid."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if CERT_FILE.is_file() and KEY_FILE.is_file():
        return
    print("[BOMA-OAUTH] Generating self-signed dev cert for localhost…")
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-nodes",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(KEY_FILE),
            "-out",
            str(CERT_FILE),
            "-days",
            "365",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def write_token_storage(tokens: dict) -> None:
    """Persist tokens in the layout the `digikey-api` library expects."""
    # The library reads `access_token`, `refresh_token`, `token_type`,
    # `expires_in`, and `expires` (epoch seconds, with ~60s margin baked in).
    expires = int(tokens.get("expires_at") or 0)
    if not expires:
        expires = int(
            datetime.now(timezone.utc).timestamp()
            + int(tokens.get("expires_in", 1800))
            - 60
        )
    out = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type", "Bearer"),
        "expires_in": int(tokens.get("expires_in", 1800)),
        "expires": expires,
    }
    TOKEN_FILE.write_text(json.dumps(out, indent=2))
    print(f"[BOMA-OAUTH] Saved tokens → {TOKEN_FILE}")


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    server_version = "BOMA-OAuth/1.0"

    def log_message(self, *_args, **_kwargs):  # silence access log noise
        return

    def do_GET(self):  # noqa: N802 — http.server expects this name
        parsed = urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self._respond_html(
                404,
                "<h1>BOMA OAuth helper</h1>"
                "<p>Waiting for the DigiKey callback…</p>",
            )
            return

        qs = parse_qs(parsed.query)
        if "error" in qs:
            err = qs["error"][0]
            self._respond_html(400, f"<h1>DigiKey returned an error</h1><p>{err}</p>")
            self.server.boma_error = err  # type: ignore[attr-defined]
            self.server.boma_done = True  # type: ignore[attr-defined]
            return

        code = (qs.get("code") or [""])[0]
        state = (qs.get("state") or [""])[0]
        if not code or not state:
            self._respond_html(400, "<h1>Missing ?code or ?state in callback</h1>")
            self.server.boma_error = "missing code/state"  # type: ignore[attr-defined]
            self.server.boma_done = True  # type: ignore[attr-defined]
            return

        if not digikey_oauth.consume_oauth_state(state):
            self._respond_html(400, "<h1>State mismatch — possible CSRF</h1>")
            self.server.boma_error = "state mismatch"  # type: ignore[attr-defined]
            self.server.boma_done = True  # type: ignore[attr-defined]
            return

        try:
            tokens = digikey_oauth.exchange_code(code)
        except digikey_oauth.DigiKeyOAuthError as exc:
            self._respond_html(500, f"<h1>Token exchange failed</h1><pre>{exc}</pre>")
            self.server.boma_error = str(exc)  # type: ignore[attr-defined]
            self.server.boma_done = True  # type: ignore[attr-defined]
            return

        write_token_storage(tokens)
        self._respond_html(
            200,
            "<h1>BOMA · DigiKey connected ✓</h1>"
            "<p>You can close this tab and return to the terminal.</p>",
        )
        self.server.boma_tokens = tokens  # type: ignore[attr-defined]
        self.server.boma_done = True  # type: ignore[attr-defined]

    def _respond_html(self, status: int, body: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            f"<html><body style='font-family:system-ui;padding:2rem;max-width:40rem;margin:auto'>{body}</body></html>".encode()
        )


def run_oauth_flow(timeout_sec: int = 300) -> None:
    if not os.getenv("DIGIKEY_CLIENT_ID") or not os.getenv("DIGIKEY_CLIENT_SECRET"):
        sys.exit(
            "DIGIKEY_CLIENT_ID / DIGIKEY_CLIENT_SECRET are not set — check your .env"
        )

    expected = f"https://{CALLBACK_HOST}:{CALLBACK_PORT}{CALLBACK_PATH}"
    actual = digikey_oauth.redirect_uri()
    if actual != expected:
        print(
            "[BOMA-OAUTH] WARNING: connector redirect_uri() returned "
            f"{actual!r} but this helper listens on {expected!r}. "
            "Set DIGIKEY_REDIRECT_URI in .env if your portal callback differs."
        )

    ensure_cert()

    state = digikey_oauth.new_oauth_state()
    auth_url = digikey_oauth.build_authorize_url(state)

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))

    httpd = http.server.HTTPServer((CALLBACK_HOST, CALLBACK_PORT), _CallbackHandler)
    httpd.socket = ssl_ctx.wrap_socket(httpd.socket, server_side=True)
    httpd.boma_done = False  # type: ignore[attr-defined]
    httpd.boma_tokens = None  # type: ignore[attr-defined]
    httpd.boma_error = None  # type: ignore[attr-defined]

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    print(f"[BOMA-OAUTH] Listening on {expected}")
    print("[BOMA-OAUTH] Opening your browser at the DigiKey consent screen…")
    print(
        "[BOMA-OAUTH] (Your browser will warn about the self-signed cert — "
        "click 'Advanced → Proceed to localhost'.)"
    )
    print(f"[BOMA-OAUTH] If the browser doesn't open, visit:\n    {auth_url}\n")

    if not webbrowser.open_new(auth_url):
        print("[BOMA-OAUTH] Could not auto-open the browser — copy the URL above.")

    start = time.monotonic()
    while not httpd.boma_done:  # type: ignore[attr-defined]
        if time.monotonic() - start > timeout_sec:
            print("[BOMA-OAUTH] Timed out waiting for callback.")
            break
        time.sleep(0.2)

    httpd.shutdown()
    server_thread.join(timeout=2)

    if httpd.boma_tokens:  # type: ignore[attr-defined]
        print("[BOMA-OAUTH] DigiKey is connected. You can now set "
              "BOMA_USE_MOCK_CATALOG=0 in .env and restart the backend.")
    else:
        err = httpd.boma_error or "no tokens received"  # type: ignore[attr-defined]
        sys.exit(f"[BOMA-OAUTH] OAuth did not complete: {err}")


if __name__ == "__main__":
    run_oauth_flow()
