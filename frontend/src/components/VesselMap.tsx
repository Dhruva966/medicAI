import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Vessel } from "../lib/types";

interface Props {
  selectedImo: string | null;
  onSelect: (imo: string) => void;
}

/**
 * Leaflet world map. Each vessel is a circle marker colored by its
 * deception-score band (low/medium/high/critical). Clicking calls onSelect.
 *
 * TODO: drop in <MapContainer> + <CircleMarker> from react-leaflet,
 *       fetch list, color via tailwind 'band' colors.
 */
export default function VesselMap({ selectedImo, onSelect }: Props) {
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listVessels()
      .then(setVessels)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="flex h-full w-full items-center justify-center bg-slate-900 text-slate-500">
      <div className="text-center">
        <div className="text-sm uppercase tracking-widest">VesselMap</div>
        <div className="mt-2 text-xs">
          {error
            ? `error: ${error}`
            : vessels.length === 0
            ? "no vessels (seed required)"
            : `${vessels.length} vessels`}
        </div>
        <div className="mt-2 text-xs">
          selected: <span className="text-slate-300">{selectedImo ?? "—"}</span>
        </div>
        <button
          className="mt-4 rounded border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800"
          onClick={() => onSelect("9876543")}
        >
          stub: select demo IMO 9876543
        </button>
      </div>
    </div>
  );
}
