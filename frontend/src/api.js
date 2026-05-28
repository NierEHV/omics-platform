const BASE = "/api";

export function parseSseFrame(chunk) {
  const frames = [];
  const lines = chunk.split("\n");
  let eventType = "";
  let dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event: ")) {
      eventType = line.slice(7).trim();
    } else if (line.startsWith("data: ")) {
      dataLines.push(line.slice(6));
    } else if (line === "" && eventType && dataLines.length > 0) {
      try {
        frames.push({ event: eventType, data: JSON.parse(dataLines.join("\n")) });
      } catch {
        frames.push({ event: eventType, data: dataLines.join("\n") });
      }
      eventType = "";
      dataLines = [];
    }
  }
  return frames;
}

export async function streamChat(message, files, history, { onEvent, onError, onDone, signal }) {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, files, history }),
    signal,
  });

  if (!res.ok) {
    const text = await res.text();
    onError(new Error(text));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const frames = parseSseFrame(buffer);
      if (frames.length > 0) {
        buffer = "";
        for (const frame of frames) {
          if (frame.event === "error") {
            onError(new Error(frame.data.msg || "Unknown error"));
          } else if (frame.event === "done") {
            onDone(frame.data);
          } else {
            onEvent(frame.event, frame.data);
          }
        }
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") onError(e);
  } finally {
    reader.releaseLock();
  }
}

// ── REST helpers ──

async function request(method, path, body) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.msg || res.statusText);
  }
  return res.json();
}

export function listFiles() {
  return request("GET", "/files");
}

export async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/files/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export function deleteFile(filename) {
  return request("DELETE", `/files/${encodeURIComponent(filename)}`);
}

export function getFileInfo(filename) {
  return request("GET", `/files/${encodeURIComponent(filename)}/info`);
}

export function dataInfo(path) {
  return request("POST", "/data/info", { path });
}

export function dataSearch(query) {
  return request("POST", "/data/search", { query });
}

export function dataFetch(accession) {
  return request("POST", "/data/fetch", { accession });
}

export function getGPUStatus() {
  return request("GET", "/system/gpu");
}

export function getConfig() {
  return request("GET", "/system/config");
}

export function getSettings() {
  return request("GET", "/settings");
}

export function updateSettings(data) {
  return request("PUT", "/settings", data);
}

export function getPresets() {
  return request("GET", "/settings/presets");
}

export function getSettingsStatus() {
  return request("GET", "/settings/status");
}

export function testConnection(data) {
  return request("POST", "/settings/test", data);
}

// ── Projects ──

export function fetchProjects(params = {}) {
  const qs = new URLSearchParams(params).toString()
  return request("GET", `/projects${qs ? '?' + qs : ''}`)
}
export function createProject(data) { return request("POST", "/projects", data) }
export function getProject(id) { return request("GET", `/projects/${id}`) }
export function updateProject(id, data) { return request("PUT", `/projects/${id}`, data) }
export function deleteProject(id) { return request("DELETE", `/projects/${id}`) }

export async function uploadFileToProject(projectId, file) {
  const form = new FormData()
  form.append("file", file)
  const res = await fetch(`${BASE}/projects/${projectId}/files/upload`, { method: "POST", body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}
export function deleteProjectFile(projectId, fileId) {
  return request("DELETE", `/projects/${projectId}/files/${fileId}`)
}

// ── DAG & Pipeline ──

export function getDAGTemplate(modality) { return request("GET", `/dag/templates/${modality}`) }
export function getDAGTemplates() { return request("GET", "/dag/templates") }
export function getNodeStates(projectId) { return request("GET", `/projects/${projectId}/nodes`) }
export function updateNodeParams(projectId, nodeId, data) {
  return request("PUT", `/projects/${projectId}/nodes/${nodeId}`, data)
}
export function getLogs(projectId, nodeId = null) {
  const qs = nodeId ? `?node_id=${nodeId}` : ''
  return request("GET", `/projects/${projectId}/logs${qs}`)
}

export async function runNode(projectId, nodeId, params, onEvent) {
  const res = await fetch(`${BASE}/projects/${projectId}/nodes/${nodeId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params || {}),
  })
  return streamSseResponse(res, onEvent)
}

export async function runPipeline(projectId, onEvent) {
  const res = await fetch(`${BASE}/projects/${projectId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  return streamSseResponse(res, onEvent)
}

async function streamSseResponse(res, onEvent) {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const frames = parseSseFrame(buffer)
      if (frames.length > 0) {
        buffer = ""
        for (const frame of frames) {
          if (onEvent) onEvent(frame.event, frame.data)
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// ── System ──

export function getSystemCapacity() { return request("GET", "/system/capacity") }
