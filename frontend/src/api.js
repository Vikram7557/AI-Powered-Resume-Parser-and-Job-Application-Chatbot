const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function createSession() {
  const data = await request("/session", { method: "POST" });
  return data.session_id;
}

export async function sendChatMessage(sessionId, message) {
  return request("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export async function uploadResume(sessionId, file) {
  const formData = new FormData();
  formData.append("file", file);
  return request(`/upload-resume?session_id=${encodeURIComponent(sessionId)}`, {
    method: "POST",
    body: formData,
  });
}

export async function reuseResume(sessionId, roleTitle) {
  return request("/reuse-resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, role_title: roleTitle || null }),
  });
}

export async function fetchRoles() {
  return request("/roles");
}

export async function quickApply(sessionId, roleTitle) {
  return request("/quick-apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, role_title: roleTitle }),
  });
}

export async function previewRole(sessionId, roleTitle) {
  return request("/role-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, role_title: roleTitle }),
  });
}
