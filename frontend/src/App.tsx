import { useEffect, useState } from "react";
import Header from "./components/Header";
import VesselList from "./components/VesselList";
import VesselMap from "./components/VesselMap";
import VesselDetail from "./components/VesselDetail";
import ScoreBreakdown from "./components/ScoreBreakdown";
import OwnershipGraph from "./components/OwnershipGraph";
import InterdictionBrief from "./components/InterdictionBrief";
import SARViewer from "./components/SARViewer";
import EvidenceTimeline from "./components/EvidenceTimeline";
import { api } from "./lib/api";
import type { Vessel } from "./lib/types";

type Tab = "score" | "evidence" | "ownership" | "sar" | "brief";

export default function App() {
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [vesselError, setVesselError] = useState<string | null>(null);
  const [selectedImo, setSelectedImo] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("score");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.listVessels().then(setVessels).catch((e) => setVesselError(String(e)));
  }, []);

  const selected = vessels.find((v) => v.imo === selectedImo) ?? null;

  return (
    <div className="grid h-full grid-cols-[260px_1fr_460px] grid-rows-[56px_1fr] bg-ink-900 text-slate-100">
      <Header search={search} onSearch={setSearch} totalVessels={vessels.length} />

      <aside className="row-start-2 border-r border-ink-600/60 bg-ink-800/40 panel-scroll overflow-y-auto">
        <VesselList
          vessels={vessels}
          search={search}
          selectedImo={selectedImo}
          onSelect={(imo) => {
            setSelectedImo(imo);
            setTab("score");
          }}
          error={vesselError}
        />
      </aside>

      <main className="row-start-2 relative">
        <VesselMap
          vessels={vessels}
          selectedImo={selectedImo}
          onSelect={(imo) => {
            setSelectedImo(imo);
            setTab("score");
          }}
        />
      </main>

      <aside className="row-start-2 flex flex-col border-l border-ink-600/60 bg-ink-800/40 min-h-0">
        {!selected && <EmptyPanel />}
        {selected && (
          <>
            <PanelHeader vessel={selected} />
            <nav className="flex border-b border-ink-600/60 text-xs uppercase tracking-wider">
              {(
                [
                  ["score", "Score"],
                  ["evidence", "Evidence"],
                  ["ownership", "Network"],
                  ["sar", "SAR"],
                  ["brief", "Brief"],
                ] as [Tab, string][]
              ).map(([t, label]) => (
                <button
                  key={t}
                  className={`flex-1 px-3 py-2.5 transition-colors ${
                    tab === t
                      ? "bg-ink-700 text-accent-cyan border-b-2 border-accent-cyan"
                      : "text-slate-400 hover:text-slate-100"
                  }`}
                  onClick={() => setTab(t)}
                >
                  {label}
                </button>
              ))}
            </nav>

            <div className="flex-1 panel-scroll overflow-y-auto p-4">
              {tab === "score" && (
                <>
                  <VesselDetail imo={selected.imo} />
                  <div className="mt-6">
                    <ScoreBreakdown imo={selected.imo} />
                  </div>
                </>
              )}
              {tab === "evidence" && <EvidenceTimeline imo={selected.imo} />}
              {tab === "ownership" && <OwnershipGraph imo={selected.imo} />}
              {tab === "sar" && <SARViewer imo={selected.imo} />}
              {tab === "brief" && <InterdictionBrief imo={selected.imo} />}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}

function EmptyPanel() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="h-12 w-12 rounded-full border border-accent-cyan/30 bg-accent-cyan/5 flex items-center justify-center text-accent-cyan">
        <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 12c1.5-3 6-7 9-7s7.5 4 9 7c-1.5 3-6 7-9 7s-7.5-4-9-7z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </div>
      <p className="text-sm text-slate-400">Select a vessel from the list or map to begin.</p>
      <p className="text-xs text-slate-600 max-w-xs">
        Markers are colored by their current deception score. Critical-band
        vessels pulse on the map.
      </p>
    </div>
  );
}

function PanelHeader({ vessel }: { vessel: Vessel }) {
  return (
    <div className="border-b border-ink-600/60 px-4 py-3">
      <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
        IMO {vessel.imo} · {vessel.flag}
      </div>
      <div className="text-lg font-semibold leading-tight">{vessel.name}</div>
    </div>
  );
}
