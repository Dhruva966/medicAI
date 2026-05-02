// Thin fetch wrappers around the backend. The Vite dev server proxies
// /api/* to http://localhost:8000 (see vite.config.ts).

import type {
  Evidence,
  InterdictionBriefOut,
  OwnershipNetwork,
  SAROverlay,
  Score,
  Vessel,
  VesselDetail,
} from "./types";

const API = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  listVessels: () => get<Vessel[]>("/vessels"),
  getVessel: (imo: string) => get<VesselDetail>(`/vessels/${imo}`),
  getScore: (imo: string) => get<Score>(`/vessels/${imo}/score`),
  getEvidence: (imo: string) => get<Evidence[]>(`/vessels/${imo}/evidence`),
  getNetwork: (imo: string, depth = 2) =>
    get<OwnershipNetwork>(`/vessels/${imo}/network?depth=${depth}`),
  getSAR: (imo: string) => get<SAROverlay>(`/vessels/${imo}/sar`),
  generateBrief: (imo: string) => post<InterdictionBriefOut>(`/vessels/${imo}/brief`),
};
