const BASE = "/api";

async function req(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

export const api = {
  // Characters
  getCharacters: () => req("GET", "/characters"),
  createCharacter: (d) => req("POST", "/characters", d),
  updateCharacter: (id, d) => req("PUT", `/characters/${id}`, d),
  deleteCharacter: (id) => req("DELETE", `/characters/${id}`),

  // Blueprints
  getBlueprints: () => req("GET", "/blueprints"),
  createBlueprint: (d) => req("POST", "/blueprints", d),
  updateBlueprint: (id, d) => req("PUT", `/blueprints/${id}`, d),
  deleteBlueprint: (id) => req("DELETE", `/blueprints/${id}`),
  getCategories: () => req("GET", "/blueprints/categories"),

  // Character blueprints
  getCharacterBlueprints: (cid) => req("GET", `/characters/${cid}/blueprints`),
  setStatus: (cid, bid, learned, acquired_count) =>
    req("PUT", `/characters/${cid}/blueprints/${bid}`, { learned, acquired_count }),
  bulkSetStatus: (cid, updates) =>
    req("PUT", `/characters/${cid}/blueprints/bulk`, updates),

  // Reports
  reportSummary: () => req("GET", "/reports/character-summary"),
  reportCoverage: () => req("GET", "/reports/blueprint-coverage"),
  reportMissing: (bid) => req("GET", `/reports/missing-blueprint?blueprint_id=${bid}`),
  reportHaving: (bid) => req("GET", `/reports/characters-with-blueprint?blueprint_id=${bid}`),
  reportExtras: () => req("GET", "/reports/extras"),
  search: (q) => req("GET", `/reports/search?q=${encodeURIComponent(q)}`),

  // Seed
  seed: () => req("POST", "/seed"),
};
