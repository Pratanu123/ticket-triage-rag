import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getTicket, overrideTicket } from "../api";
import ConfidenceBar from "../components/ConfidenceBar";
import StatusBadge from "../components/StatusBadge";
import { formatRelativeTime } from "../lib/format";

export default function TicketDetail() {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const data = await getTicket(id);
        if (!cancelled) {
          setTicket(data);
          setDraft(data.suggested_response || "");
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load ticket");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function onApprove(event) {
    event.preventDefault();
    if (!draft.trim()) {
      setError("A response is required before approving.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const updated = await overrideTicket(id, {
        suggested_response: draft.trim(),
        note: note.trim() || null,
        category: ticket.category,
      });
      setTicket(updated);
      setDraft(updated.suggested_response || "");
    } catch (err) {
      setError(err.message || "Override failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="py-16 text-center text-sm text-muted">Loading ticket…</div>;
  }

  if (!ticket) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {error || "Ticket not found"}
      </div>
    );
  }

  const needsReview = ticket.status === "needs_human_review";
  const chunks = ticket.retrieved_chunks || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/" className="text-sm font-medium text-teal-700 hover:text-teal-900">
            ← Back to tickets
          </Link>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-ink">{ticket.subject}</h2>
          <p className="mt-1 text-sm text-muted">
            Created {formatRelativeTime(ticket.created_at)} · ID {ticket.id.slice(0, 8)}…
          </p>
        </div>
        <StatusBadge status={ticket.status} />
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <section className="rounded-lg border border-line bg-surface p-6 shadow-sm">
        <SectionLabel>Original ticket</SectionLabel>
        <h3 className="mt-2 text-lg font-semibold text-ink">{ticket.subject}</h3>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
          {ticket.body}
        </p>
      </section>

      <section className="rounded-lg border border-line bg-surface p-6 shadow-sm">
        <SectionLabel>Classification</SectionLabel>
        <div className="mt-4 flex flex-wrap items-end gap-8">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Category
            </div>
            <div className="mt-1 text-lg font-semibold capitalize text-ink">
              {ticket.category}
            </div>
          </div>
          <ConfidenceBar value={ticket.confidence} />
        </div>
        <div className="mt-5 rounded-lg bg-slate-50 px-4 py-3 ring-1 ring-slate-100">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            AI reasoning
          </div>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">
            {ticket.reasoning || "No reasoning recorded."}
          </p>
        </div>
      </section>

      <section className="rounded-lg border border-line bg-surface p-6 shadow-sm">
        <SectionLabel>Retrieved sources</SectionLabel>
        {chunks.length === 0 ? (
          <p className="mt-3 text-sm text-muted">No knowledge-base chunks were stored for this ticket.</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {chunks.map((chunk, index) => (
              <li
                key={`${chunk.source}-${chunk.chunk_index}-${index}`}
                className="rounded-lg border border-line bg-slate-50/70 px-4 py-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-ink">{chunk.source}</span>
                  <span className="text-xs text-muted">
                    {chunk.category} · score {Number(chunk.score).toFixed(2)}
                  </span>
                </div>
                <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-slate-600">
                  {chunk.content}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-line bg-surface p-6 shadow-sm">
        <SectionLabel>
          {needsReview ? "Human review / override" : "Suggested response"}
        </SectionLabel>

        {needsReview ? (
          <form onSubmit={onApprove} className="mt-4 space-y-4">
            <p className="text-sm text-muted">
              Confidence was below the threshold, so no auto-reply was sent. Edit a response
              and approve to mark this ticket human-resolved.
            </p>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={8}
              disabled={saving}
              placeholder="Write the customer-facing reply…"
              className="w-full resize-y rounded-lg border border-line bg-white px-3.5 py-2.5 text-sm text-ink outline-none ring-teal-600/30 focus:border-teal-600 focus:ring-2 disabled:bg-slate-50"
            />
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={saving}
              placeholder="Optional reviewer note"
              className="w-full rounded-lg border border-line bg-white px-3.5 py-2.5 text-sm text-ink outline-none ring-teal-600/30 focus:border-teal-600 focus:ring-2 disabled:bg-slate-50"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-800 disabled:opacity-60"
              >
                {saving ? "Saving…" : "Approve and send"}
              </button>
            </div>
          </form>
        ) : (
          <div className="mt-4 rounded-lg bg-slate-50 px-4 py-4 ring-1 ring-slate-100">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
              {ticket.suggested_response || "No response recorded."}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
      {children}
    </div>
  );
}
