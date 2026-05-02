# Demo Flow — 3 minutes

> **Status:** placeholder. Tighten timing once the seed data and brief output are real.

## Setup (before the judges)

- `make seed` — load demo dataset (~50 vessels, 10 deliberately suspicious)
- `make dev` — both servers up
- Browser at `http://localhost:5173`

## Beat 1 — The map (0:00–0:30)

- Open the app. World map, ~50 vessels, color-coded by deception score.
- "Most of these ships are doing what they say they're doing. A handful are not."
- Click a green vessel → boring side panel: matching identity, plausible route, no anomalies.

## Beat 2 — The hit (0:30–1:30)

- Click a red vessel (critical band).
- Score: 842. Band: critical.
- Score breakdown shows: `ais_gap`, `flag_hopping`, `ownership_shell`, `sts_proximity`, `sar_visual_mismatch`.
- Each row has a one-line evidence string.

## Beat 3 — The ownership graph (1:30–2:00)

- Switch to ownership graph tab.
- D3 force-directed graph: this vessel → shell company → linked to two SDN-listed vessels.
- "The shell company is two degrees from a vessel sanctioned by Treasury for moving Russian oil."

## Beat 4 — The SAR (2:00–2:20)

- Switch to SAR overlay.
- Map shows AIS-reported position vs. SAR detection — different ocean.
- "AIS says it was here. Satellite says it was here. The vessel is lying about its location."

## Beat 5 — The brief (2:20–3:00)

- Click "Generate interdiction brief."
- Claude streams a 4-paragraph structured writeup: who, what, evidence, recommended action.
- Last line: *"Recommend immediate flag for sanctions review and notification of regional maritime command."*

## Closing line

> *"This is one ship in one ocean. Multiply by every shadow-fleet vessel currently dark in the Gulf, the Black Sea, and the Strait of Malacca, and that's the gap we close."*
