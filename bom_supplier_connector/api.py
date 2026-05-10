"""
FastAPI service for BOM enrichment.

Run from repository root:
  uvicorn bom_supplier_connector.api:app --host 0.0.0.0 --port 8000 \\
      --ssl-keyfile dev-cert/key.pem --ssl-certfile dev-cert/cert.pem

The TLS cert is required because DigiKey's OAuth callback MUST be https://.

Endpoints:
  GET  /health                    sanity check
  GET  /digikey/login             302 redirect → DigiKey consent screen
  GET  /digikey/callback          OAuth code exchange; sets boma_session cookie
  GET  /digikey/status            { logged_in: bool }
  POST /enrich                    multipart CSV upload → enriched BOM
                                  + DigiKey third-party single-use list URL when
                                    matched rows include DigiKey part numbers
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import Cookie, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from . import digikey_oauth
from .digikey_oauth import (
    DigiKeyOAuthError,
    build_authorize_url,
    consume_oauth_state,
    exchange_code,
    get_valid_access_token,
    new_oauth_state,
    new_session_id,
    store_tokens,
)
from .pipeline import enrich_bom

SESSION_COOKIE = "boma_session"
FRONTEND_BASE = os.getenv("BOMA_FRONTEND_URL", "http://localhost:3000")

app = FastAPI(title="BOM Supplier Connector")


@app.on_event("startup")
def _log_oauth_redirect_uri() -> None:
    """Log the exact redirect_uri sent to DigiKey — must match the developer portal."""
    from .digikey_oauth import redirect_uri as _ru

    print(f"[BOMA] OAuth redirect_uri (register this in DigiKey portal): {_ru()}")

# Next.js dev runs on :3000 (sometimes :3001). Without this every browser
# fetch is blocked by CORS even though the routes work fine from curl.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_BASE, "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# DigiKey OAuth
# ---------------------------------------------------------------------------

@app.get("/digikey/login")
def digikey_login() -> RedirectResponse:
    """Step 1 of 3-legged OAuth: send the user to DigiKey's consent screen.

    DigiKey will redirect them back to /digikey/callback?code=...&state=...
    """
    state = new_oauth_state()
    return RedirectResponse(url=build_authorize_url(state), status_code=302)


@app.get("/digikey/callback")
def digikey_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    boma_session: Optional[str] = Cookie(default=None),
) -> RedirectResponse:
    """Step 2: DigiKey hits this with ?code=...&state=... after the user
    consents. We swap the code for tokens, store them keyed by a session
    cookie, and bounce the user back to the frontend."""
    if error:
        return _bounce_to_frontend(digikey=f"error:{error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    if not consume_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    try:
        tokens = exchange_code(code)
    except DigiKeyOAuthError as e:
        return _bounce_to_frontend(digikey=f"error:{e}")

    sid = boma_session or new_session_id()
    store_tokens(sid, tokens)

    response = _bounce_to_frontend(digikey="ok")
    # The cookie is HTTPS-only because the whole API is HTTPS for OAuth anyway.
    response.set_cookie(
        SESSION_COOKIE,
        sid,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@app.get("/digikey/status")
def digikey_status(boma_session: Optional[str] = Cookie(default=None)) -> dict:
    """Tells the frontend whether the current session has a valid DigiKey
    token. Used to decide whether to show a 'Login with DigiKey' button."""
    if not boma_session:
        return {"logged_in": False}
    return {"logged_in": get_valid_access_token(boma_session) is not None}


def _bounce_to_frontend(**params: str) -> RedirectResponse:
    qs = urlencode({k: v for k, v in params.items() if v})
    return RedirectResponse(url=f"{FRONTEND_BASE}?{qs}", status_code=302)


# ---------------------------------------------------------------------------
# Enrich
# ---------------------------------------------------------------------------

@app.post("/enrich")
async def enrich(
    file: UploadFile = File(...),
    deadline_days: Optional[int] = Form(default=None),
    list_name: Optional[str] = Form(default=None),
) -> JSONResponse:
    """Parse the uploaded CSV, run the agent pipeline, then build a DigiKey
    third-party MyList (no login). Returns enriched parts, summary, and
    ``list_url`` (single-use link) when list creation succeeds."""
    suffix = Path(file.filename or "bom.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    stem = Path(file.filename or "bom.csv").stem or "BOMA list"
    list_label = (list_name or stem).strip() or stem
    try:
        result = enrich_bom(tmp_path, deadline_days, digikey_list_name=list_label)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    summary = result.get("summary", {})
    response: dict = {
        "parts": result.get("parts", []),
        "summary": summary,
        "deadline_days": deadline_days,
        "total_cost_usd": summary.get("total_cost_usd"),
    }
    for key in ("digikey_list", "list_url", "digikey_list_error"):
        if key in result:
            response[key] = result[key]

    return JSONResponse(response)
