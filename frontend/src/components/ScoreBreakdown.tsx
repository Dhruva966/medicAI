import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Band, Score } from "../lib/types";

interface Props {
  imo: string;
}

const BAND_COLOR: Record<Band, string> = {
  low: "text-band-low",
  medium: "text-band-medium",
  high: "text-band-high",
  critical: "text-band-critical",
};

/**
 * Numeric score header + per-component contribution bars.
 */
export default function ScoreBreakdown({ imo }: Props) {
  const [score, setScore] = useState<Score | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setScore(null);
    setError(null);
    api.getScore(imo).then(setScore).catch((e) => setError(String(e)));
  }, [imo]);

  return (
    <section>
      <h2 className="text-xs uppercase tracking-widest text-slate-500">
        ScoreBreakdown
      </h2>
      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
      {!score && !error && <p className="mt-2 text-xs text-slate-500">loading…</p>}
      {score && (
        <>
          <div className="mt-2 flex items-baseline gap-3">
            <div className="text-3xl font-semibold tabular-nums">{score.score}</div>
            <div className={`text-sm uppercase ${BAND_COLOR[score.band]}`}>
              {score.band}
            </div>
          </div>
          <ul className="mt-3 space-y-1 text-sm">
            {score.components.map((c) => (
              <li key={c.name} className="flex justify-between border-b border-slate-800 py-1">
                <span className="text-slate-300">{c.name}</span>
                <span className="tabular-nums text-slate-400">
                  {c.contribution}/{c.weight}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
