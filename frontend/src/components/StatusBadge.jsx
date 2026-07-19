import { statusLabel } from "../lib/format";

const STYLES = {
  auto_resolved: "bg-good-soft text-good ring-1 ring-green-200/80",
  needs_human_review: "bg-warn-soft text-warn ring-1 ring-amber-200/80",
  human_resolved: "bg-info-soft text-info ring-1 ring-blue-200/80",
};

export default function StatusBadge({ status }) {
  const classes = STYLES[status] || "bg-slate-100 text-slate-600 ring-1 ring-slate-200";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold tracking-wide ${classes}`}
    >
      {statusLabel(status)}
    </span>
  );
}
