import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { OwnershipNetwork } from "../lib/types";

interface Props {
  imo: string;
}

/**
 * D3 force-directed graph of vessel ↔ owner ↔ sanctioned-vessel edges.
 *
 * TODO: render via d3-force into an <svg>. For now, list nodes/edges.
 */
export default function OwnershipGraph({ imo }: Props) {
  const [network, setNetwork] = useState<OwnershipNetwork | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setNetwork(null);
    setError(null);
    api.getNetwork(imo).then(setNetwork).catch((e) => setError(String(e)));
  }, [imo]);

  return (
    <section>
      <h2 className="text-xs uppercase tracking-widest text-slate-500">
        OwnershipGraph
      </h2>
      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
      {!network && !error && <p className="mt-2 text-xs text-slate-500">loading…</p>}
      {network && (
        <div className="mt-2 text-xs text-slate-400">
          {network.nodes.length} nodes · {network.edges.length} edges
        </div>
      )}
    </section>
  );
}
