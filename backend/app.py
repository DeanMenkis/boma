import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth_middleware import get_current_user
from firebase_init import get_firebase_app

load_dotenv()

# Eagerly initialise Firebase Admin on startup.
get_firebase_app()

app = FastAPI(title="BOMA Backend")

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server and any configured origin
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
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
