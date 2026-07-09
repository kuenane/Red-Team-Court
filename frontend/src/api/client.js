const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

export const api = {
  uploadDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/v1/documents", { method: "POST", body: form });
  },
  startRun: (documentId) => request(`/api/v1/documents/${documentId}/analyze`, { method: "POST" }),
  getRun: (runId) => request(`/api/v1/runs/${runId}`),
  streamRunUrl: (runId) => `${BASE_URL}/api/v1/runs/${runId}/events`,
};
