// TypeScript types mirroring the pydantic schemas in backend/app/schemas/.

export type Band = "low" | "medium" | "high" | "critical";

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

export interface ScoreComponent {
  name: string;
  weight: number;
  value: number;
  contribution: number;
  evidence: Record<string, unknown>;
}

export interface Score {
  vessel_imo: string;
  score: number;
  band: Band;
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
  image_url: string;
  bbox: [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]
  acquired_at: string;
  ais_position: [number, number] | null;
  sar_position: [number, number] | null;
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
