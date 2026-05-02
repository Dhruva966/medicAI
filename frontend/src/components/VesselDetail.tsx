import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Band, VesselDetail as VesselDetailT } from "../lib/types";
import { BAND_BG, BAND_CLASS } from "../lib/score";

interface Props {
  imo: string;
}

export default function VesselDetail({ imo }: Props) {
  const [vessel, setVessel] = useState<VesselDetailT | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setVessel(null);
    setError(null);
    api.getVessel(imo).then(setVessel).catch((e) => setError(String(e)));
  }, [imo]);

  if (error) return <p className="text-xs text-rose-400">error: {error}</p>;
  if (!vessel) return <p className="text-xs text-slate-500">loading…</p>;

  const band = (vessel.band as Band | undefined) ?? null;

  return (
    <section>
      {/* Score header */}
      {vessel.score != null && band && (
        <div
          className={`mb-4 rounded-lg border ${
            band === "critical"
              ? "border-band-critical/40 bg-band-critical/5 shadow-glow-critical"
              : band === "high"
              ? "border-band-high/40 bg-band-high/5"
              : band === "medium"
              ? "border-band-medium/40 bg-band-medium/5"
              : "border-band-low/40 bg-band-low/5"
          } px-4 py-3`}
        >
          <div className="flex items-baseline justify-between gap-4">
            <div className="flex items-baseline gap-3">
              <div className="tabular text-3xl font-semibold leading-none">{vessel.score}</div>
              <div className="text-xs text-slate-500">/ 1000</div>
            </div>
            <div className={`text-xs font-semibold uppercase tracking-widest ${BAND_CLASS[band]}`}>
              {band}
            </div>
          </div>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
            <div
              className={`h-full rounded-full ${BAND_BG[band]}`}
              style={{ width: `${Math.max(2, (vessel.score / 1000) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Identity card */}
      <div className="space-y-3">
        <Field label="Type" value={vessel.type} />
        <Field label="Flag" value={vessel.flag} />
        <Field label="MMSI" value={vessel.mmsi} mono />
        <Field
          label="Build"
          value={
            vessel.year_built
              ? `${vessel.year_built} · ${vessel.length_m ?? "—"}m × ${vessel.beam_m ?? "—"}m · ${
                  vessel.gross_tonnage?.toLocaleString() ?? "—"
                } GT`
              : null
          }
        />
        <Field
          label="Last fix"
          value={
            vessel.last_seen_lat != null && vessel.last_seen_lon != null
              ? `${vessel.last_seen_lat.toFixed(3)}, ${vessel.last_seen_lon.toFixed(3)}${
                  vessel.last_seen_at ? ` · ${formatRel(vessel.last_seen_at)}` : ""
                }`
              : null
          }
          mono
        />
      </div>

      {/* Owner */}
      {vessel.owner && (
        <div className="mt-5 rounded-md border border-ink-600/60 bg-ink-800/40 p-3">
          <div className="text-[10px] uppercase tracking-widest text-slate-500">
            Registered owner
          </div>
          <div className="mt-1 flex items-center gap-2 text-sm">
            <span className="font-medium">{vessel.owner.name}</span>
            {vessel.owner.country && (
              <span className="text-xs text-slate-500">· {vessel.owner.country}</span>
            )}
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5 text-[10px]">
            {vessel.owner.sanctioned && (
              <span className="rounded border border-band-critical/40 bg-band-critical/10 px-1.5 py-0.5 text-band-critical">
                SANCTIONED · OFAC SDN
              </span>
            )}
            {vessel.owner.shell_company && (
              <span className="rounded border border-band-high/40 bg-band-high/10 px-1.5 py-0.5 text-band-high">
                SHELL COMPANY
              </span>
            )}
          </div>
        </div>
      )}

      {/* Flag history */}
      {vessel.flag_history && vessel.flag_history.length > 1 && (
        <div className="mt-5">
          <div className="text-[10px] uppercase tracking-widest text-slate-500">
            Flag history ({vessel.flag_history.length})
          </div>
          <ol className="mt-2 space-y-1 text-xs">
            {[...vessel.flag_history]
              .sort((a, b) => (b.start_date || "").localeCompare(a.start_date || ""))
              .map((f, i) => (
                <li
                  key={`${f.flag}-${i}`}
                  className="flex items-center justify-between border-b border-ink-600/40 pb-1"
                >
                  <span className="font-medium">{f.flag}</span>
                  <span className="tabular text-slate-500">
                    {f.start_date?.slice(0, 10)}
                    {f.end_date ? ` → ${f.end_date.slice(0, 10)}` : " · current"}
                  </span>
                </li>
              ))}
          </ol>
        </div>
      )}
    </section>
  );
}

function Field({ label, value, mono = false }: { label: string; value: string | null | undefined; mono?: boolean }) {
  return (
    <div className="grid grid-cols-[80px_1fr] gap-x-3 text-sm">
      <div className="text-[10px] uppercase tracking-widest text-slate-500 self-center">
        {label}
      </div>
      <div className={mono ? "font-mono text-xs" : ""}>{value ?? <span className="text-slate-600">—</span>}</div>
    </div>
  );
}

function formatRel(iso: string): string {
  const d = new Date(iso);
  const diffH = Math.round((Date.now() - d.getTime()) / 3_600_000);
  if (diffH < 1) return "just now";
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.round(diffH / 24)}d ago`;
}
