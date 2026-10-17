// REST helper – all URLs are relative so the UI works behind HA ingress.

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function errorText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => (d?.loc ? `${d.loc.slice(1).join(".")}: ${d.msg}` : JSON.stringify(d)))
      .join("; ");
  }
  return JSON.stringify(detail);
}

export async function api<T = any>(
  method: string,
  path: string,
  body?: unknown,
  headers: Record<string, string> = {},
): Promise<T> {
  const init: RequestInit = { method, headers: { ...headers } };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await fetch(`api/${path.replace(/^\//, "")}`, init);
  const text = await res.text();
  let data: any = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? errorText(data.detail) : text;
    throw new ApiError(detail || `HTTP ${res.status}`, res.status);
  }
  return data as T;
}

/** Calls to the gateway REST API (proxied by the add-on). */
export const gw = {
  get: <T = any>(p: string) => api<T>("GET", `gw${p}`),
  post: <T = any>(p: string, body?: unknown, headers?: Record<string, string>) =>
    api<T>("POST", `gw${p}`, body, headers),
  put: <T = any>(p: string, body?: unknown) => api<T>("PUT", `gw${p}`, body),
  del: <T = any>(p: string, headers?: Record<string, string>) => api<T>("DELETE", `gw${p}`, undefined, headers),
  control: (target: string, id: number | null, data: Record<string, unknown>) =>
    target === "broadcast"
      ? api("POST", "gw/broadcast/control", data)
      : api("POST", `gw/${target}/${id}/control`, data),
};

export function downloadUrl(path: string): string {
  return `api/${path.replace(/^\//, "")}`;
}
