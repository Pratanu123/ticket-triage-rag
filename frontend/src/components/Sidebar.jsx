import { NavLink } from "react-router-dom";

const linkClass = ({ isActive }) =>
  [
    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
    isActive
      ? "bg-accent-soft text-accent"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  ].join(" ");

export default function Sidebar() {
  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-line bg-surface px-4 py-6">
      <div className="mb-8 px-2">
        <div className="text-xs font-semibold uppercase tracking-[0.14em] text-teal-700/80">
          CloudNova
        </div>
        <h1 className="mt-1 text-xl font-bold tracking-tight text-ink">Ticket Triage</h1>
        <p className="mt-1 text-sm text-muted">RAG support desk</p>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        <NavLink to="/" end className={linkClass}>
          All tickets
        </NavLink>
        <NavLink to="/new" className={linkClass}>
          New ticket
        </NavLink>
      </nav>

      <NavLink
        to="/new"
        className="mt-4 inline-flex items-center justify-center rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800"
      >
        + New Ticket
      </NavLink>
    </aside>
  );
}
