import Legend from "./Legend";

interface Props {
  search: string;
  onSearch: (s: string) => void;
  totalVessels: number;
}

export default function Header({ search, onSearch, totalVessels }: Props) {
  return (
    <header className="col-span-3 row-start-1 flex items-center justify-between gap-4 border-b border-ink-600/60 bg-ink-900/95 px-4 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-accent-cyan/30 bg-accent-cyan/10 text-accent-cyan">
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
            <path d="M2 19c2-2 4-2 6 0s4 2 6 0 4-2 6 0" strokeLinecap="round" />
            <path d="M4 14h16l-3-7H7l-3 7z" strokeLinejoin="round" />
            <path d="M12 7V3" strokeLinecap="round" />
          </svg>
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight tracking-tight">
            ShadowFleet <span className="text-slate-500">OS</span>
          </div>
          <div className="text-[10px] uppercase tracking-widest text-slate-500">
            Maritime deception workbench
          </div>
        </div>
      </div>

      <div className="relative max-w-sm flex-1">
        <input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Search by name, IMO, flag…"
          className="w-full rounded-md border border-ink-600 bg-ink-800 px-3 py-1.5 pl-8 text-sm placeholder:text-slate-600 focus:border-accent-cyan/60 focus:outline-none focus:ring-1 focus:ring-accent-cyan/40"
        />
        <svg
          className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" strokeLinecap="round" />
        </svg>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-xs text-slate-500">
          <span className="text-slate-300 tabular">{totalVessels}</span> vessels tracked
        </div>
        <Legend />
      </div>
    </header>
  );
}
