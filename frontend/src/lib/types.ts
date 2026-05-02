// TypeScript types mirroring the pydantic schemas in backend/app/schemas/.

export type Band = "low" | "medium" | "high" | "critical";
export type Severity = "low" | "medium" | "high" | "critical";

export interface Owner {
  id: number;
  name: string;
  country: string | null;
  shell_company: boolean;
  sanctioned: boolean;
  sanctioned_at: string | null;
  parent_owner_id: number | null;
}

export interface FlagHistoryEntry {
  flag: string;
  start_date: string;
  end_date: string | null;
}

export interface Vessel {
  imo: string;
  name: string;
  type: string;
  flag: string;
  last_seen_lat: number | null;
  last_seen_lon: number | null;
  last_seen_at: string | null;
  score: number | null;
  band: Band | null;
}

export interface VesselDetail extends Vessel {
  mmsi: string | null;
  gross_tonnage: number | null;
  length_m: number | null;
  beam_m: number | null;
  year_built: number | null;
  owner: Owner | null;
  flag_history: FlagHistoryEntry[];
}

export interface Evidence {
  id: number;
  vessel_imo: string;
  detector_name: string;
  title: string;
  description: string;
  source_type: "ais" | "sanctions" | "registry" | "satellite" | "port";
  source_ref: string;
  start_time: string | null;
  end_time: string | null;
  geometry: Record<string, unknown>;
  severity: Severity;
  confidence: number;
  score_contribution: number;
  analyst_notes: string | null;
  created_at: string;
}

export interface ScoreComponent {
  name: string;
  weight: number;
  value: number;
  contribution: number;
  evidence_records: Evidence[];
}

export interface Score {
  vessel_imo: string;
  score: number;
  band: Band;
  recommendation: string;
  computed_at: string;
  components: ScoreComponent[];
}

export interface OwnershipNode {
  id: string;
  label: string;
  kind: "vessel" | "owner" | "sanctioned_vessel";
  sanctioned: boolean;
}

export interface OwnershipEdge {
  source: string;
  target: string;
  relation: string;
}

export interface OwnershipNetwork {
  nodes: OwnershipNode[];
  edges: OwnershipEdge[];
}

export interface SAROverlay {
  image_url: string | null;
  bbox: [number, number, number, number] | null;
  acquired_at: string | null;
  ais_position: [number, number] | null;
  sar_position: [number, number] | null;
  note?: string;
}

export interface InterdictionBriefOut {
  vessel_imo: string;
  generated_at: string;
  headline: string;
  summary: string;
  evidence: string[];
  recommended_action: string;
  confidence: number;
  raw_markdown: string;
}
