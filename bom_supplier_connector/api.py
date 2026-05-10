"""
FastAPI service for BOM enrichment.
Run from repository root:
  uvicorn bom_supplier_connector.api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile

from .pipeline import enrich_bom

app = FastAPI(title="BOM Supplier Connector")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/enrich")
async def enrich(
    file: UploadFile = File(...),
    deadline_days: int = Form(30),
) -> dict:
    suffix = Path(file.filename or "bom.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        return enrich_bom(tmp_path, deadline_days)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
