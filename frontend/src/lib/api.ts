// Thin fetch wrapper for the FastAPI backend (reached through the Next.js /api rewrite).

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Options = RequestInit & {
  json?: unknown;
  /** Send the browser to /login on 401 (default true). */
  redirectOn401?: boolean;
};

function detailMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  // FastAPI validation errors: [{ msg, loc }, ...]
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return `Request failed (${status})`;
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const { json, redirectOn401 = true, headers, ...init } = options;
  const res = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    headers: {
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : init.body,
  });

  if (res.status === 401 && redirectOn401 && typeof window !== "undefined") {
    const next = encodeURIComponent(window.location.pathname);
    // Deliberate full navigation: drops all cached client state with the expired session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = `/login?next=${next}`;
  }
  if (res.status === 204) return undefined as T;

  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, detailMessage(body, res.status));
  return body as T;
}
