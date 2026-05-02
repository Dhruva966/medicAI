# Scoring Rubric

Per-vessel deception score on a **0–1000** scale. Higher = more likely the vessel is misrepresenting itself.

> **Status:** placeholder. Final weights, thresholds, and evidence rules will be tuned during the hackathon.

## Bands

| Band       | Range     | Meaning                                                                  |
|------------|-----------|--------------------------------------------------------------------------|
| `low`      | 0–249     | Behavior consistent with stated identity and route.                      |
| `medium`   | 250–549   | Some anomalies. Watch.                                                   |
| `high`     | 550–799   | Multiple deception signals. Flag for sanctions review.                   |
| `critical` | 800–1000  | Strong deception fingerprint. Recommend interdiction brief immediately.  |

## Components (placeholder weights)

| Component             | Weight | Trigger                                                                   |
|-----------------------|--------|---------------------------------------------------------------------------|
| `ais_gap`             | 150    | AIS off > 6h, especially in known STS zones or near sanctioned routes.    |
| `flag_hopping`        | 100    | ≥ 2 flag changes in 12 months, or change to a flag of convenience.        |
| `ownership_shell`     | 150    | Owner is a shell company tied to previously sanctioned vessels.           |
| `sts_proximity`       | 150    | Encounter with another vessel in open water > 1h, no port call logged.   |
| `route_implausible`   | 100    | Stated route inconsistent with port history, draft change, or fuel range. |
| `sanctions_neighbor`  | 100    | Direct contact (encounter, port co-occurrence) with an SDN-listed vessel. |
| `identity_mismatch`   | 100    | MMSI / IMO / name / call-sign inconsistencies between sources.            |
| `sar_visual_mismatch` | 100    | SAR detection in a location where AIS says the vessel was elsewhere.      |
| `dark_port_call`      |  50    | Arrival/departure recorded by port but AIS was off during transit.        |

Total max: 1000.

## Output shape

```json
{
  "vessel_imo": "9876543",
  "score": 842,
  "band": "critical",
  "computed_at": "2026-05-02T19:00:00Z",
  "components": [
    {"name": "ais_gap", "weight": 150, "value": 1.0, "contribution": 150, "evidence": {...}},
    {"name": "flag_hopping", "weight": 100, "value": 0.8, "contribution": 80, "evidence": {...}}
  ]
}
```
