import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { VesselDetail as VesselDetailT } from "../lib/types";

interface Props {
  imo: string;
}

/**
 * Side-panel detail view for a clicked vessel: identity, owner, flag history.
 */
export default function VesselDetail({ imo }: Props) {
  const [vessel, setVessel] = useState<VesselDetailT | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setVessel(null);
    setError(null);
    api.getVessel(imo).then(setVessel).catch((e) => setError(String(e)));
  }, [imo]);

  return (
    <section>
      <h2 className="text-xs uppercase tracking-widest text-slate-500">
        VesselDetail
      </h2>
      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
      {!vessel && !error && <p className="mt-2 text-xs text-slate-500">loading…</p>}
      {vessel && (
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-slate-500">IMO</dt>
          <dd>{vessel.imo}</dd>
          <dt className="text-slate-500">Name</dt>
          <dd>{vessel.name}</dd>
          <dt className="text-slate-500">Type</dt>
          <dd>{vessel.type}</dd>
          <dt className="text-slate-500">Flag</dt>
          <dd>{vessel.flag}</dd>
          <dt className="text-slate-500">Owner</dt>
          <dd>{vessel.owner?.name ?? "—"}</dd>
        </dl>
      )}
    </section>
  );
}
