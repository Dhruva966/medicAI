import { useState } from "react";
import { api } from "../lib/api";
import type { InterdictionBriefOut } from "../lib/types";

interface Props {
  imo: string;
}

export default function InterdictionBrief({ imo }: Props) {
  const [brief, setBrief] = useState<InterdictionBriefOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      setBrief(await api.generateBrief(imo));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const copy = () => {
    if (!brief) return;
    navigator.clipboard.writeText(brief.raw_markdown).catch(() => {});
  };

  return (
    <section>
      <div className="flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-widest text-slate-500">Interdiction brief</h2>
        {brief && (
          <button
            onClick={copy}
            className="text-[10px] uppercase tracking-widest text-slate-500 hover:text-slate-200"
          >
            copy markdown
          </button>
        )}
      </div>

      {!brief && (
        <button
          onClick={generate}
          disabled={loading}
          className="mt-3 w-full rounded-md border border-band-critical/40 bg-band-critical/10 px-4 py-3 text-sm font-semibold text-band-critical transition-colors hover:bg-band-critical/15 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate interdiction brief"}
        </button>
      )}

      {error && <p className="mt-3 text-xs text-rose-400">error: {error}</p>}

      {brief && (
        <article className="mt-4 space-y-4 text-sm leading-relaxed">
          <h3 className="text-base font-semibold text-band-critical">{brief.headline}</h3>
          <p className="text-slate-200">{brief.summary}</p>
          <div>
            <div className="mb-1.5 text-[10px] uppercase tracking-widest text-slate-500">
              Evidence
            </div>
            <ul className="space-y-1.5">
              {brief.evidence.map((e, i) => (
                <li key={i} className="flex gap-2 text-xs text-slate-300">
                  <span className="text-accent-cyan">▸</span>
                  <span>{e}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-md border border-band-critical/40 bg-band-critical/10 p-3">
            <div className="text-[10px] uppercase tracking-widest text-band-critical">
              Recommended action
            </div>
            <div className="mt-1 font-semibold uppercase">{brief.recommended_action}</div>
          </div>
          <div className="text-[10px] tabular text-slate-600">
            confidence {(brief.confidence * 100).toFixed(0)}% · generated{" "}
            {new Date(brief.generated_at).toLocaleString()}
          </div>
        </article>
      )}
    </section>
  );
}
