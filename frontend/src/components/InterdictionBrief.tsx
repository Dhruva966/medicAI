import { useState } from "react";
import { api } from "../lib/api";
import type { InterdictionBriefOut } from "../lib/types";

interface Props {
  imo: string;
}

/**
 * Renders the LLM-generated interdiction brief. Click the button to call
 * POST /vessels/{imo}/brief.
 */
export default function InterdictionBrief({ imo }: Props) {
  const [brief, setBrief] = useState<InterdictionBriefOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const b = await api.generateBrief(imo);
      setBrief(b);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section>
      <h2 className="text-xs uppercase tracking-widest text-slate-500">
        InterdictionBrief
      </h2>
      <button
        className="mt-2 rounded bg-band-critical px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
        onClick={generate}
        disabled={loading}
      >
        {loading ? "generating…" : "Generate interdiction brief"}
      </button>
      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
      {brief && (
        <div className="mt-3 space-y-2 text-sm">
          <h3 className="font-semibold">{brief.headline}</h3>
          <p className="text-slate-300">{brief.summary}</p>
          <ul className="list-disc pl-5 text-slate-400">
            {brief.evidence.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
          <p className="text-slate-200">
            <span className="text-slate-500">Recommended action: </span>
            {brief.recommended_action}
          </p>
          <p className="text-xs text-slate-500">
            confidence: {(brief.confidence * 100).toFixed(0)}%
          </p>
        </div>
      )}
    </section>
  );
}
