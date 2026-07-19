import { formatPercent } from "../lib/format";

export default function ConfidenceBar({ value, compact = false }) {
  const pct = Math.max(0, Math.min(1, Number(value) || 0));
  const width = `${Math.round(pct * 100)}%`;
  const tone =
    pct >= 0.7 ? "bg-teal-600" : pct >= 0.45 ? "bg-amber-500" : "bg-rose-400";

  return (
    <div className={compact ? "w-28" : "w-full max-w-xs"}>
      <div className="mb-1 flex items-center justify-between gap-2 text-xs text-slate-500">
        <span>Confidence</span>
        <span className="font-semibold text-slate-700">{formatPercent(pct)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100 ring-1 ring-slate-200/70">
        <div
          className={`h-full rounded-full transition-all duration-500 ${tone}`}
          style={{ width }}
        />
      </div>
    </div>
  );
}
