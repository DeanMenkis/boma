# BOMA

> **From a BOM spreadsheet to a ready-to-buy hardware order.**

BOMA is a procurement agent for hardware teams. Upload the bill-of-materials your EDA tool already exports, and the agent finds every part across suppliers, compares price and lead time, and assembles a cart in under 60 seconds. Pay BOMA in USDC via AllScale and we hand back a pre-filled supplier cart for one-click checkout.

## How it works

- **Dual-tier model routing through CLōD** — a fast 8B model normalizes every BOM line into a structured spec; a frontier reasoning model ranks live supplier matches. ~**8× cheaper** on tokens, no measurable hit on match quality.
- **Live Digi-Key API** for real prices and stock.
- **Greptile + KiCad** symbols/footprints — grounding fuzzy matches in real, reviewed open-source hardware.
- **AllScale USDC checkout** — BOMA is the merchant of payment, so suppliers don't have to accept stablecoins.

## Built with

`Cursor` · `Claude` · `CLōD` · `AllScale` · `Greptile` · `Digi-Key API` · `FastAPI` · `Lovable` · `Next.js` · `TypeScript`

## Team

Popal Daudzai · Athif Saleem · Dean David Menkis · Ilia Moroz

## Links

- **Devpost** — <https://devpost.com/software/boma>
- **Hackathon** — Cursor Hackathon Vancouver, 2026
