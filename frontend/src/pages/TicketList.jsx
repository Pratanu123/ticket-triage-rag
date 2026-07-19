import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listTickets } from "../api";
import ConfidenceBar from "../components/ConfidenceBar";
import StatusBadge from "../components/StatusBadge";
import { formatRelativeTime } from "../lib/format";

export default function TicketList() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const data = await listTickets();
        if (!cancelled) setTickets(data.tickets || []);
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load tickets");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => {
    const total = tickets.length;
    const auto = tickets.filter((t) => t.status === "auto_resolved").length;
    const escalated = tickets.filter((t) => t.status === "needs_human_review").length;
    const human = tickets.filter((t) => t.status === "human_resolved").length;
    return {
      total,
      autoPct: total ? Math.round((auto / total) * 100) : 0,
      escalatedPct: total ? Math.round((escalated / total) * 100) : 0,
      human,
      auto,
      escalated,
    };
  }, [tickets]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink">Tickets</h2>
          <p className="mt-1 text-sm text-muted">
            Triage queue with confidence-based auto-resolve and human escalation.
          </p>
        </div>
        <Link
          to="/new"
          className="inline-flex items-center rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-800"
        >
          New ticket
        </Link>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Total tickets" value={String(stats.total)} hint="All time in this environment" />
        <StatCard
          label="Auto-resolved"
          value={`${stats.autoPct}%`}
          hint={`${stats.auto} tickets cleared by the agent`}
          tone="good"
        />
        <StatCard
          label="Escalated"
          value={`${stats.escalatedPct}%`}
          hint={`${stats.escalated} waiting on human review`}
          tone="warn"
        />
      </section>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <section className="overflow-hidden rounded-lg border border-line bg-surface shadow-sm">
        {loading ? (
          <div className="px-6 py-16 text-center text-sm text-muted">Loading tickets…</div>
        ) : tickets.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-line bg-slate-50/80 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3">Subject</th>
                  <th className="px-5 py-3">Category</th>
                  <th className="px-5 py-3">Confidence</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {tickets.map((ticket) => (
                  <tr key={ticket.id} className="transition hover:bg-slate-50/70">
                    <td className="px-5 py-4">
                      <Link
                        to={`/tickets/${ticket.id}`}
                        className="font-semibold text-ink hover:text-accent"
                      >
                        {ticket.subject}
                      </Link>
                      <p className="mt-0.5 line-clamp-1 max-w-md text-xs text-muted">
                        {ticket.body}
                      </p>
                    </td>
                    <td className="px-5 py-4 capitalize text-slate-600">{ticket.category}</td>
                    <td className="px-5 py-4">
                      <ConfidenceBar value={ticket.confidence} compact />
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={ticket.status} />
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-slate-500">
                      {formatRelativeTime(ticket.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({ label, value, hint, tone }) {
  const valueClass =
    tone === "good"
      ? "text-good"
      : tone === "warn"
        ? "text-warn"
        : "text-ink";
  return (
    <div className="rounded-lg border border-line bg-surface p-5 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-2 text-3xl font-bold tracking-tight ${valueClass}`}>{value}</div>
      <p className="mt-1 text-xs text-muted">{hint}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center px-6 py-16 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-accent">
        <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h8M8 12h5M6 4h12a2 2 0 0 1 2 2v13l-4-2-4 2-4-2-4 2V6a2 2 0 0 1 2-2z" />
        </svg>
      </div>
      <h3 className="mt-4 text-lg font-semibold text-ink">No tickets yet</h3>
      <p className="mt-2 max-w-sm text-sm text-muted">
        Create a support ticket to see RAG classification, confidence scoring, and
        auto-resolve vs human escalation in action.
      </p>
      <Link
        to="/new"
        className="mt-6 inline-flex rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-800"
      >
        Create your first ticket
      </Link>
    </div>
  );
}
