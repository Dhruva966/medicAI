/**
 * Score-band legend shown in the header.
 */
export default function Legend() {
  const items: Array<{ label: string; range: string; cls: string }> = [
    { label: "low", range: "0–249", cls: "bg-band-low" },
    { label: "medium", range: "250–549", cls: "bg-band-medium" },
    { label: "high", range: "550–799", cls: "bg-band-high" },
    { label: "critical", range: "800+", cls: "bg-band-critical" },
  ];
  return (
    <div className="flex items-center gap-3 text-xs">
      {items.map((i) => (
        <span key={i.label} className="flex items-center gap-1">
          <span className={`inline-block h-2 w-2 rounded-full ${i.cls}`} />
          <span className="text-slate-400">{i.label}</span>
          <span className="text-slate-600">{i.range}</span>
        </span>
      ))}
    </div>
  );
}
