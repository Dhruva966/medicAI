# Scoring Rubric

Per-vessel deception score on a **0–1000** scale. Higher = more likely the vessel is misrepresenting itself.

## Bands

| Band | Range | Meaning | Recommendation |
|---|---|---|---|
| `low` | 0–249 | Behavior consistent with stated identity and route | `monitor` |
| `medium` | 250–549 | Some anomalies, signal is not yet decisive | `investigate` |
| `high` | 550–799 | Multiple deception signals, pattern is shadow-fleet-like | `sanctions review` |
| `critical` | 800–1000 | Strong deception fingerprint across multiple sources | `notify command` |

## Components (current weights)

The six implemented detectors sum to `RUBRIC_MAX = 860`. The raw component total is normalized to 0–1000 in the response, leaving headroom for future detectors (SAR visual mismatch, dark port call, etc.) without rebalancing.

| Detector | Weight | Trigger |
|---|---|---|
| `dark_activity` | 180 | AIS off > 4h. Severity scales with duration; doubled inside a known STS zone. |
| `kinematic_anomaly` | 120 | Implied transit speed across an AIS gap exceeds 30 kn. |
| `sts_proximity` | 150 | Open-water encounter > 30 min, no port call. Boosted by classified STS + known zone + oil cargo. |
| `sanctions_match` | 200 | Direct OFAC SDN hit on vessel IMO, or sanctioned ancestor in owner chain. Shell-company owners contribute. |
| `identity_inconsistency` | 110 | ≥ 2 flag changes in 12 months, switch to a flag of convenience, or missing MMSI. |
| `route_plausibility` | 100 | Last-known position > 4000 nm from any recently-called port. |

## Output shape

```json
{
  "vessel_imo": "9876543",
  "score": 819,
  "band": "critical",
  "recommendation": "notify command",
  "computed_at": "2026-05-02T19:00:00Z",
  "components": [
    {
      "name": "dark_activity",
      "weight": 180,
      "value": 1.0,
      "contribution": 180,
      "evidence_records": [{
        "id": 12,
        "detector_name": "dark_activity",
        "title": "16.0h AIS dark period inside a known STS-transfer corridor",
        "description": "...",
        "source_type": "ais",
        "source_ref": "aisgap://4",
        "severity": "critical",
        "confidence": 0.85,
        "geometry": {"type": "LineString", "coordinates": [...]},
        "...": "..."
      }]
    }
  ]
}
```
