import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Score } from "../lib/types";
import { BAND_BG, DETECTOR_LABEL, SEV_BG } from "../lib/score";

interface Props {
  imo: string;
}

export default function ScoreBreakdown({ imo }: Props) {
  const [score, setScore] = useState<Score | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setScore(null);
    setError(null);
    api.getScore(imo).then(setScore).catch((e) => setError(String(e)));
  }, [imo]);

  if (error) return <p className="text-xs text-rose-400">error: {error}</p>;
  if (!score) return <p className="text-xs text-slate-500">computing score…</p>;

  const sortedComponents = [...score.components].sort((a, b) => b.contribution - a.contribution);

  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-slate-500">Rubric breakdown</h2>
        <span className="text-[10px] uppercase tracking-widest text-slate-600">
          recommend · <span className="text-slate-300">{score.recommendation}</span>
        </span>
      </div>

      <ol className="space-y-2.5">
        {sortedComponents.map((c) => {
          const pct = (c.contribution / Math.max(c.weight, 1)) * 100;
          const sev =
            c.value >= 0.85 ? "critical" : c.value >= 0.6 ? "high" : c.value >= 0.3 ? "medium" : "low";
          return (
            <li
              key={c.name}
              className="rounded-md border border-ink-600/60 bg-ink-800/40 p-3 transition-colors hover:border-ink-500"
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-sm font-medium">{DETECTOR_LABEL[c.name] ?? c.name}</span>
                <span className="tabular text-xs text-slate-400">
                  <span className="text-slate-200">{c.contribution}</span>
                  <span className="text-slate-600"> / {c.weight}</span>
                </span>
              </div>
              <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-ink-700">
                <div
                  className={`h-full ${BAND_BG[sev]}`}
                  style={{ width: `${Math.min(100, Math.max(2, pct))}%` }}
                />
              </div>
              {c.evidence_records.length > 0 && (
                <ul className="mt-2 space-y-1.5">
                  {c.evidence_records.slice(0, 3).map((ev) => (
                    <li
                      key={ev.id}
                      className="text-[11px] leading-relaxed text-slate-400"
                    >
                      <span
                        className={`mr-1.5 inline-flex items-center rounded border px-1 py-0.5 text-[9px] uppercase tracking-wider ${
                          SEV_BG[ev.severity]
                        }`}
                      >
                        {ev.severity}
                      </span>
                      {ev.title}
                    </li>
                  ))}
                  {c.evidence_records.length > 3 && (
                    <li className="text-[10px] text-slate-600">
                      + {c.evidence_records.length - 3} more — see Evidence tab
                    </li>
                  )}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
