import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { SAROverlay } from "../lib/types";

interface Props {
  imo: string;
}

/**
 * Sentinel-1 SAR overlay viewer — shows the satellite scene + the AIS-vs-SAR
 * position mismatch when a vessel went dark.
 */
export default function SARViewer({ imo }: Props) {
  const [overlay, setOverlay] = useState<SAROverlay | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setOverlay(null);
    setError(null);
    api.getSAR(imo).then(setOverlay).catch((e) => setError(String(e)));
  }, [imo]);

  return (
    <section>
      <h2 className="text-xs uppercase tracking-widest text-slate-500">
        SARViewer
      </h2>
      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
      {!overlay && !error && <p className="mt-2 text-xs text-slate-500">loading…</p>}
      {overlay && (
        <div className="mt-2 text-xs text-slate-400">
          acquired: {overlay.acquired_at}
        </div>
      )}
    </section>
  );
}
