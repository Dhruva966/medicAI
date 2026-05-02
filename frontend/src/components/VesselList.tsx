import { useMemo } from "react";
import type { Band, Vessel } from "../lib/types";
import { BAND_BG, BAND_CLASS } from "../lib/score";

interface Props {
  vessels: Vessel[];
  search: string;
  selectedImo: string | null;
  onSelect: (imo: string) => void;
  error: string | null;
}

const BAND_ORDER: Record<Band | "none", number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  none: 4,
};

export default function VesselList({ vessels, search, selectedImo, onSelect, error }: Props) {
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const matches = vessels.filter((v) => {
      if (!q) return true;
      return (
        v.name.toLowerCase().includes(q) ||
        v.imo.includes(q) ||
        v.flag.toLowerCase().includes(q)
      );
    });
    matches.sort((a, b) => {
      const ra = BAND_ORDER[(a.band as Band) ?? "none"];
      const rb = BAND_ORDER[(b.band as Band) ?? "none"];
      if (ra !== rb) return ra - rb;
      return (b.score ?? -1) - (a.score ?? -1);
    });
    return matches;
  }, [vessels, search]);

  if (error) {
    return <p className="p-4 text-xs text-rose-400">error: {error}</p>;
  }
  if (vessels.length === 0) {
    return (
      <div className="p-6 text-center text-sm text-slate-500">
        <p>No vessels yet.</p>
        <p className="mt-2 text-xs text-slate-600">
          Run <code className="font-mono text-slate-400">python -m app.seed.demo_vessels</code>{" "}
          in the backend to load the demo scenario.
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-ink-600/40">
      {filtered.map((v) => {
        const band = (v.band as Band | undefined) ?? null;
        const isSelected = v.imo === selectedImo;
        return (
          <li key={v.imo}>
            <button
              onClick={() => onSelect(v.imo)}
              className={`flex w-full items-center gap-3 px-3 py-2 text-left transition-colors ${
                isSelected ? "bg-ink-700/80" : "hover:bg-ink-700/40"
              }`}
            >
              <span
                className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ring-1 ring-white/10 ${
                  band ? BAND_BG[band] : "bg-slate-600"
                }`}
              />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{v.name}</div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  {v.imo} · {v.flag}
                </div>
              </div>
              {v.score != null && band && (
                <span className={`tabular text-xs font-semibold ${BAND_CLASS[band]}`}>
                  {v.score}
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
