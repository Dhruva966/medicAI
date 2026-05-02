# Demo Flow — 3 minutes

The `demo_shadow_001` scenario was curated to walk through cleanly in three minutes. Hero vessel: **IMO 9876543 / ATLANTIS PIONEER**.

## Setup (before the judges)

```bash
cd backend && uv run python -m app.seed.demo_vessels   # ~2s, idempotent
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm dev                                 # http://localhost:5173
```

## Beat 1 — The map (0:00–0:30)

- Open the app. World map, **58 vessels**, color-coded by score band.
- One marker pulses red in the Arabian Sea — `ATLANTIS PIONEER`.
- "Most of these vessels are doing what they say they're doing. One is not."
- Click any green vessel from the left list — boring detail panel: matching identity, plausible route, no anomalies.

## Beat 2 — The hit (0:30–1:30)

- Click the red vessel.
- **Score: 819. Band: CRITICAL. Recommendation: notify command.**
- Score breakdown shows five firing detectors:
  - `dark_activity` 180/180 — 16h gap inside a known STS zone
  - `sanctions_match` 160/200 — sanctioned shell two hops up
  - `sts_proximity` 150/150 — 3h open-water encounter
  - `kinematic_anomaly` 120/120 — implied speed > 80 kn across an 18h gap
  - `identity_inconsistency` 94/110 — four flag changes in 12 months
- Each row has one-line evidence with a severity badge.

## Beat 3 — Evidence trail (1:30–2:00)

- Switch to **Evidence** tab.
- Chronological timeline of every alert. Each card has source-type badge (AIS, OFAC, Registry, SAR), severity chip, source ref (`aisgap://4`, `ofac://sdn/owner/2`), and confidence percent.
- "Nothing here is opaque. Every line traces back to a stored, citable record an analyst can audit."

## Beat 4 — Ownership graph (2:00–2:30)

- Switch to **Network** tab.
- D3 force-directed graph. Hero (cyan) → `Marshall Pacific Holdings` (shell) → `Hong Kong Pearl Maritime` (sanctioned shell) → `Sovcomflot OJSC` (sanctioned parent). A red ring marks every sanctioned entity.
- Sister vessel `KRUSHEVA` floats off Sovcomflot — directly on the OFAC SDN list. The dashed red edge from hero to KRUSHEVA shows the lateral link.
- "The shell company is two hops from a vessel sanctioned by Treasury for moving Russian oil."

## Beat 5 — SAR cross-check (2:30–2:45)

- Switch to **SAR** tab.
- Small map shows AIS-reported position (cyan) vs SAR-detected position (red) during the 16h dark window. Different ocean.
- "AIS says it was here. Satellite says it was here. The vessel is lying about its location."

## Beat 6 — The brief (2:45–3:00)

- Switch to **Brief** tab. Click *Generate interdiction brief*.
- Structured output: headline, summary paragraph, evidence bullets, recommended action, confidence percent.
- "*ATLANTIS PIONEER matches shadow-fleet deception pattern. Recommended action: notify command.*"
- "Copy markdown" button hands the brief to the analyst's chat-of-record.

## Closing line

> *"This is one ship in one ocean. Multiply by every shadow-fleet vessel currently dark in the Gulf, the Black Sea, and the Strait of Malacca, and that's the gap we close."*
