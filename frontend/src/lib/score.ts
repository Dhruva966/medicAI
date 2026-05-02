// Shared score-band utilities used across the UI.

import type { Band, Severity } from "./types";

export const BAND_CLASS: Record<Band, string> = {
  low: "text-band-low",
  medium: "text-band-medium",
  high: "text-band-high",
  critical: "text-band-critical",
};

export const BAND_BG: Record<Band, string> = {
  low: "bg-band-low",
  medium: "bg-band-medium",
  high: "bg-band-high",
  critical: "bg-band-critical",
};

export const BAND_HEX: Record<Band, string> = {
  low: "#22c55e",
  medium: "#eab308",
  high: "#f97316",
  critical: "#ef4444",
};

export const SEV_BG: Record<Severity, string> = {
  low: "bg-band-low/15 text-band-low border-band-low/30",
  medium: "bg-band-medium/15 text-band-medium border-band-medium/30",
  high: "bg-band-high/15 text-band-high border-band-high/30",
  critical: "bg-band-critical/15 text-band-critical border-band-critical/30",
};

export const DETECTOR_LABEL: Record<string, string> = {
  dark_activity: "Dark activity",
  kinematic_anomaly: "Kinematic anomaly",
  sts_proximity: "STS proximity",
  sanctions_match: "Sanctions match",
  identity_inconsistency: "Identity inconsistency",
  route_plausibility: "Route plausibility",
};

export function scoreToBand(score: number): Band {
  if (score >= 800) return "critical";
  if (score >= 550) return "high";
  if (score >= 250) return "medium";
  return "low";
}
