import { useState } from "react";
import VesselMap from "./components/VesselMap";
import VesselDetail from "./components/VesselDetail";
import ScoreBreakdown from "./components/ScoreBreakdown";
import OwnershipGraph from "./components/OwnershipGraph";
import InterdictionBrief from "./components/InterdictionBrief";
import SARViewer from "./components/SARViewer";
import Legend from "./components/Legend";

type Tab = "detail" | "ownership" | "sar" | "brief";

export default function App() {
  const [selectedImo, setSelectedImo] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("detail");

  return (
    <div className="grid h-full grid-cols-[1fr_420px] grid-rows-[48px_1fr]">
      <header className="col-span-2 flex items-center justify-between border-b border-slate-800 px-4">
        <h1 className="text-lg font-semibold tracking-tight">
          ShadowFleet <span className="text-slate-400">OS</span>
        </h1>
        <Legend />
      </header>

      <main className="relative">
        <VesselMap selectedImo={selectedImo} onSelect={setSelectedImo} />
      </main>

      <aside className="flex flex-col border-l border-slate-800">
        <nav className="flex border-b border-slate-800 text-sm">
          {(["detail", "ownership", "sar", "brief"] as Tab[]).map((t) => (
            <button
              key={t}
              className={`flex-1 px-3 py-2 capitalize ${
                tab === t ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"
              }`}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </nav>

        <div className="flex-1 overflow-y-auto p-4">
          {!selectedImo && (
            <p className="text-sm text-slate-400">Select a vessel on the map.</p>
          )}
          {selectedImo && tab === "detail" && (
            <>
              <VesselDetail imo={selectedImo} />
              <div className="mt-6">
                <ScoreBreakdown imo={selectedImo} />
              </div>
            </>
          )}
          {selectedImo && tab === "ownership" && <OwnershipGraph imo={selectedImo} />}
          {selectedImo && tab === "sar" && <SARViewer imo={selectedImo} />}
          {selectedImo && tab === "brief" && <InterdictionBrief imo={selectedImo} />}
        </div>
      </aside>
    </div>
  );
}
