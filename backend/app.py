import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Make sibling modules importable regardless of how uvicorn was launched.
# `auth_middleware` and `firebase_init` live inside bom_supplier_connector/
# (legacy layout); the connector package itself is at repo root.
_BACKEND_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_DIR.parent
_CONNECTOR_DIR = _REPO_ROOT / "bom_supplier_connector"
for _p in (_BACKEND_DIR, _REPO_ROOT, _CONNECTOR_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from auth_middleware import get_current_user  # noqa: E402
from firebase_init import get_firebase_app  # noqa: E402

load_dotenv()

app = FastAPI(title="BOMA Backend")

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server and any configured origin
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"status": "success", "message": "BOMA Backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/test-search")
def test_search(part_name: str = "resistor", quantity: int = 1):
    return {
        "query": {"part_name": part_name, "quantity": quantity},
        "results": [
            {"id": "mock-1", "name": f"{part_name} 10k", "price": 0.05},
            {"id": "mock-2", "name": f"{part_name} 100k", "price": 0.07},
        ],
    }


@app.post("/test-bom")
def test_bom(data: dict):
    return {
        "received": data,
        "message": "BOM data received successfully",
        "item_count": len(data.get("items", [])),
    }


# ---------------------------------------------------------------------------
# /enrich — main BOM agent endpoint
# ---------------------------------------------------------------------------

@app.post("/enrich")
async def enrich(
    file: UploadFile = File(...),
    deadline_days: Optional[int] = Form(default=None),
    list_name: Optional[str] = Form(default=None),
) -> JSONResponse:
    """Parse uploaded BOM CSV → run orchestrator/specialist agents → build a
    DigiKey third-party MyList. Returns enriched parts, summary, total cost,
    and a single-use ``list_url`` when DigiKey accepts the cart.

    Auth is intentionally open here so the agent demo works for signed-out
    visitors. Add ``Depends(get_current_user)`` if you want to gate it.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    # Lazy-imported so the backend boots even when the connector's extra
    # deps (openai, digikey-api, etc.) aren't installed — only /enrich
    # actually needs them. Importing the package also triggers
    # load_connector_env(), pulling CLōD + DigiKey creds from <repo>/.env.
    try:
        from bom_supplier_connector import digikey_lists, enrich_bom
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Backend is missing agent dependencies. "
                "Run: pip install -r bom_supplier_connector/requirements.txt"
                f" (ImportError: {exc})"
            ),
        ) from exc

    suffix = Path(file.filename).suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = enrich_bom(tmp_path, deadline_days)
    except RuntimeError as exc:
        # Most common cause: CLOD_API_KEY missing → can't run agents.
        Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    parts = result.get("parts", [])
    summary = result.get("summary", {})
    response: dict = {
        "parts": parts,
        "summary": summary,
        "deadline_days": deadline_days,
        "total_cost_usd": summary.get("total_cost_usd"),
    }

    list_parts = [
        {
            "part_number": p.get("digikey_part_number") or "",
            "quantity": int(p.get("quantity") or 1),
            "designator": p.get("designator") or "",
            "notes": (p.get("match_reason") or "")[:500],
        }
        for p in parts
        if p.get("digikey_part_number")
    ]

    if list_parts:
        # Hand the formatted payload back so the frontend can regenerate a
        # fresh single-use URL on every "Open list on DigiKey" click —
        # DigiKey's third-party MyList URLs are one-shot and easily burned
        # by browser prefetch / link preview.
        response["list_parts"] = list_parts
        response["list_name"] = list_name or (Path(file.filename).stem or "BOMA list")

    return JSONResponse(response)


# ---------------------------------------------------------------------------
# /digikey/list — on-demand single-use MyList URL
# ---------------------------------------------------------------------------

@app.post("/digikey/list")
def create_digikey_list(payload: dict = Body(...)) -> JSONResponse:
    """Mint a fresh DigiKey third-party MyList URL for the given parts.

    The frontend hits this on every "Open list on DigiKey" click so each
    URL is unburnt — DigiKey's third-party endpoint returns single-use
    redirects that are easily consumed by browser prefetchers and link
    previewers.

    Body shape:
        {
          "parts": [{"part_number": "490-1512-1-ND", "quantity": 2,
                     "designator": "C1", "notes": "..."}, ...],
          "list_name": "Forklift BOM"   # optional
        }
    """
    try:
        from bom_supplier_connector import digikey_lists
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Missing dependency for DigiKey list: {exc}",
        ) from exc

    parts = payload.get("parts") or []
    if not isinstance(parts, list) or not parts:
        raise HTTPException(
            status_code=400, detail="Request body must include a non-empty `parts` array."
        )

    name = (payload.get("list_name") or "BOMA list").strip() or "BOMA list"
    try:
        info = digikey_lists.create_list_with_parts(
            list_name=f"BOMA — {name}",
            parts=parts,
        )
    except digikey_lists.DigiKeyListError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return JSONResponse(
        {
            "list_url": info.get("list_url") or info.get("single_use_url"),
            "added_count": info.get("added_count"),
            "skipped_count": info.get("skipped_count"),
        }
    )


# ---------------------------------------------------------------------------
# Protected routes (require a valid Firebase ID token)
# ---------------------------------------------------------------------------

@app.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """Returns the Firebase user claims from the verified ID token."""
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "email_verified": user.get("email_verified"),
        "name": user.get("name"),
        "picture": user.get("picture"),
    }
