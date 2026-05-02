import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Evidence } from "../lib/types";
import { DETECTOR_LABEL, SEV_BG } from "../lib/score";

interface Props {
  imo: string;
}

const SOURCE_BADGE: Record<string, string> = {
  ais: "AIS",
  sanctions: "OFAC",
  registry: "Registry",
  satellite: "SAR",
  port: "Port",
};

export default function EvidenceTimeline({ imo }: Props) {
  const [items, setItems] = useState<Evidence[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setItems(null);
    setError(null);
    api.getEvidence(imo).then(setItems).catch((e) => setError(String(e)));
  }, [imo]);

  if (error) return <p className="text-xs text-rose-400">error: {error}</p>;
  if (!items) return <p className="text-xs text-slate-500">loading…</p>;
  if (items.length === 0) {
    return <p className="text-xs text-slate-500">No evidence recorded for this vessel.</p>;
  }

  return (
    <section>
      <h2 className="mb-3 text-xs uppercase tracking-widest text-slate-500">Evidence timeline</h2>
      <ol className="space-y-3">
        {items.map((ev) => (
          <li
            key={ev.id}
            className="relative rounded-md border border-ink-600/60 bg-ink-800/40 p-3"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex flex-wrap items-center gap-1.5 text-[10px] uppercase tracking-wider">
                <span className={`rounded border px-1.5 py-0.5 ${SEV_BG[ev.severity]}`}>
                  {ev.severity}
                </span>
                <span className="rounded border border-ink-500 bg-ink-700/60 px-1.5 py-0.5 text-slate-400">
                  {SOURCE_BADGE[ev.source_type] ?? ev.source_type}
                </span>
                <span className="text-slate-500">
                  {DETECTOR_LABEL[ev.detector_name] ?? ev.detector_name}
                </span>
              </div>
              <span className="tabular text-[10px] text-slate-600">
                {ev.start_time ? new Date(ev.start_time).toISOString().slice(0, 10) : "—"}
              </span>
            </div>
            <h3 className="mt-2 text-sm font-medium leading-snug">{ev.title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-400">{ev.description}</p>
            <div className="mt-2 flex items-center justify-between text-[10px] text-slate-600">
              <span className="font-mono">{ev.source_ref}</span>
              <span className="tabular">conf {(ev.confidence * 100).toFixed(0)}%</span>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
