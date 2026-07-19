const API_BASE = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

export function listTickets() {
  return request("/tickets");
}

export function getTicket(id) {
  return request(`/tickets/${id}`);
}

export function createTicket({ subject, body }) {
  return request("/tickets", {
    method: "POST",
    body: JSON.stringify({ subject, body }),
  });
}

export function overrideTicket(id, payload) {
  return request(`/tickets/${id}/override`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getHealth() {
  return request("/health");
}
