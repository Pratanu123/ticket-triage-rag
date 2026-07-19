import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createTicket } from "../api";

export default function NewTicket() {
  const navigate = useNavigate();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    if (!subject.trim() || !body.trim()) {
      setError("Subject and body are required.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const ticket = await createTicket({
        subject: subject.trim(),
        body: body.trim(),
      });
      navigate(`/tickets/${ticket.id}`);
    } catch (err) {
      setError(err.message || "Failed to create ticket");
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h2 className="text-2xl font-bold tracking-tight text-ink">New ticket</h2>
        <p className="mt-1 text-sm text-muted">
          Submit a support request. The local model will retrieve docs, classify,
          and either draft a reply or escalate for review.
        </p>
      </header>

      <form
        onSubmit={onSubmit}
        className="space-y-5 rounded-lg border border-line bg-surface p-6 shadow-sm"
      >
        <label className="block">
          <span className="mb-1.5 block text-sm font-semibold text-slate-700">Subject</span>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            disabled={submitting}
            placeholder="e.g. I cannot log in — 2FA not working"
            className="w-full rounded-lg border border-line bg-white px-3.5 py-2.5 text-sm text-ink outline-none ring-teal-600/30 transition placeholder:text-slate-400 focus:border-teal-600 focus:ring-2 disabled:bg-slate-50"
          />
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-semibold text-slate-700">Body</span>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            disabled={submitting}
            rows={8}
            placeholder="Describe the issue in a few sentences…"
            className="w-full resize-y rounded-lg border border-line bg-white px-3.5 py-2.5 text-sm text-ink outline-none ring-teal-600/30 transition placeholder:text-slate-400 focus:border-teal-600 focus:ring-2 disabled:bg-slate-50"
          />
        </label>

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {submitting ? (
          <div className="flex items-start gap-3 rounded-lg border border-teal-100 bg-teal-50/70 px-4 py-3">
            <span className="mt-0.5 inline-block h-4 w-4 animate-spin rounded-full border-2 border-teal-700 border-t-transparent" />
            <div>
              <p className="text-sm font-semibold text-teal-900">Classifying with local Ollama…</p>
              <p className="mt-0.5 text-xs text-teal-800/80">
                Retrieving knowledge-base chunks and scoring confidence. This can take a few seconds.
              </p>
            </div>
          </div>
        ) : null}

        <div className="flex items-center justify-end gap-3 pt-1">
          <button
            type="button"
            disabled={submitting}
            onClick={() => navigate("/")}
            className="rounded-lg px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Working…" : "Submit ticket"}
          </button>
        </div>
      </form>
    </div>
  );
}
