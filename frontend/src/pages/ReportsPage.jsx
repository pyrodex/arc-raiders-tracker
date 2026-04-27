import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import BlueprintIcon from "../BlueprintIcon.jsx";

function ProgressBar({ pct, color }) {
  return (
    <div className="progress-bar-wrap" style={{ minWidth: 80 }}>
      <div className="progress-bar-fill" style={{ width: `${pct}%`, background: color || undefined }} />
    </div>
  );
}

// ── Character Summary Report ─────────────────────────────────────────────
function CharSummaryReport() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState("completion_pct");
  const [dir, setDir] = useState("desc");

  useEffect(() => {
    api.reportSummary().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state">Loading...</div>;
  if (!data?.length) return <div className="empty-state">No data. Add characters and blueprints first.</div>;

  const sorted = [...data].sort((a, b) => dir === "desc" ? b[sort] - a[sort] : a[sort] - b[sort]);
  function toggleSort(col) { if (sort === col) setDir(d => d === "desc" ? "asc" : "desc"); else { setSort(col); setDir("desc"); } }
  const arrow = (col) => sort === col ? (dir === "desc" ? " ▼" : " ▲") : "";

  return (
    <div className="panel">
      <div className="panel-header"><span className="panel-title">Character Completion Summary</span></div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Character</th>
            <th>Class</th>
            <th style={{ cursor: "pointer" }} onClick={() => toggleSort("learned")}>Learned{arrow("learned")}</th>
            <th style={{ cursor: "pointer" }} onClick={() => toggleSort("acquired_not_learned")}>Has Copies{arrow("acquired_not_learned")}</th>
            <th style={{ cursor: "pointer" }} onClick={() => toggleSort("missing")}>Missing{arrow("missing")}</th>
            <th style={{ cursor: "pointer" }} onClick={() => toggleSort("total_extras")}>Extras{arrow("total_extras")}</th>
            <th style={{ cursor: "pointer" }} onClick={() => toggleSort("completion_pct")}>Completion{arrow("completion_pct")}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => (
            <tr key={c.id}>
              <td className="char-name-cell">{c.name}</td>
              <td><span className="char-class-tag">{c.class || "—"}</span></td>
              <td style={{ color: "var(--amber)" }}>{c.learned}</td>
              <td style={{ color: "var(--color-success)" }}>{c.acquired_not_learned}</td>
              <td style={{ color: "var(--text-muted)" }}>{c.missing}</td>
              <td style={{ color: "var(--cyan)" }}>{c.total_extras}</td>
              <td>
                <div className="flex items-center gap-sm">
                  <ProgressBar pct={c.completion_pct} />
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>{c.completion_pct}%</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Blueprint Coverage Report ────────────────────────────────────────────
function BlueprintCoverageReport() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [catFilter, setCatFilter] = useState("All");
  const [sort, setSort] = useState("coverage_pct");
  const [dir, setDir] = useState("asc");

  useEffect(() => {
    api.reportCoverage().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="empty-state">Loading...</div>;
  if (!data?.length) return <div className="empty-state">No blueprint data yet.</div>;

  const categories = ["All", ...new Set(data.map((b) => b.category))];
  const filtered = catFilter === "All" ? data : data.filter((b) => b.category === catFilter);
  const sorted = [...filtered].sort((a, b) => {
    const v = dir === "desc" ? b[sort] - a[sort] : a[sort] - b[sort];
    return v;
  });

  function toggleSort(col) {
    if (sort === col) setDir(d => d === "desc" ? "asc" : "desc");
    else { setSort(col); setDir("asc"); }
  }
  const arrow = (col) => sort === col ? (dir === "desc" ? " ▼" : " ▲") : "";

  return (
    <div>
      <div className="filter-row mb-md">
        {categories.map((c) => (
          <button key={c} className={`filter-pill ${catFilter === c ? "active" : ""}`} onClick={() => setCatFilter(c)}>{c}</button>
        ))}
      </div>
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Blueprint Acquisition Coverage (across all characters)</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th></th>
              <th>Blueprint</th>
              <th>Category</th>
              <th>Rarity</th>
              <th style={{ cursor: "pointer" }} onClick={() => toggleSort("learned")}>Learned{arrow("learned")}</th>
              <th style={{ cursor: "pointer" }} onClick={() => toggleSort("acquired_only")}>Has Copies (Not Learned){arrow("acquired_only")}</th>
              <th style={{ cursor: "pointer" }} onClick={() => toggleSort("missing")}>Missing{arrow("missing")}</th>
              <th style={{ cursor: "pointer" }} onClick={() => toggleSort("total_extras")}>Total Extras{arrow("total_extras")}</th>
              <th style={{ cursor: "pointer" }} onClick={() => toggleSort("coverage_pct")}>Coverage{arrow("coverage_pct")}</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((b) => (
              <tr key={b.id} style={{ opacity: b.missing === b.total_chars && b.total_chars > 0 ? 0.5 : 1 }}>
                <td style={{ textAlign: "center", width: 36 }}><BlueprintIcon icon={b.icon} icon_url={b.icon_url} size={24} /></td>
                <td style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "0.85rem" }}>{b.name}</td>
                <td><span className="tag">{b.category}</span></td>
                <td><span className={`rarity rarity-${b.rarity}`}>{b.rarity}</span></td>
                <td style={{ color: "var(--amber)" }}>{b.learned}</td>
                <td style={{ color: "var(--color-success)" }}>{b.acquired_only}</td>
                <td style={{ color: b.missing > 0 ? "var(--text-muted)" : "var(--color-success)" }}>{b.missing}</td>
                <td style={{ color: "var(--cyan)" }}>{b.total_extras}</td>
                <td>
                  <div className="flex items-center gap-sm">
                    <ProgressBar pct={b.coverage_pct} />
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                      {b.coverage_pct}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Missing Blueprint Report ─────────────────────────────────────────────
function MissingBlueprintReport() {
  const [blueprints, setBlueprints] = useState([]);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getBlueprints().then(setBlueprints);
  }, []);

  async function run() {
    if (!selected) return;
    setLoading(true);
    try {
      const r = await api.reportMissing(parseInt(selected));
      setResult(r);
    } finally {
      setLoading(false);
    }
  }

  const grouped = blueprints.reduce((acc, b) => {
    (acc[b.category] = acc[b.category] || []).push(b);
    return acc;
  }, {});

  return (
    <div>
      <div className="panel mb-md">
        <div className="panel-body">
          <div className="flex items-center gap-md" style={{ flexWrap: "wrap" }}>
            <div className="form-group" style={{ flex: 2, minWidth: 260 }}>
              <label className="form-label">Select Blueprint</label>
              <select className="form-select" value={selected} onChange={(e) => { setSelected(e.target.value); setResult(null); }}>
                <option value="">— choose a blueprint —</option>
                {Object.entries(grouped).map(([cat, bps]) => (
                  <optgroup key={cat} label={cat}>
                    {bps.map((b) => <option key={b.id} value={b.id}>{b.icon ? `${b.icon} ${b.name}` : b.name}</option>)}
                  </optgroup>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ flex: "none", alignSelf: "flex-end" }}>
              <button className="btn btn-primary" onClick={run} disabled={!selected || loading}>
                {loading ? "Running..." : "Find Missing"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {result && (
        <div className="panel">
          <div className="panel-header">
                    <span className="panel-title" style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <BlueprintIcon icon={result.blueprint.icon} icon_url={result.blueprint.icon_url} size={20} />
              Characters missing: {result.blueprint.name}
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-muted)" }}>
              {result.missing_count} character{result.missing_count !== 1 ? "s" : ""}
            </span>
          </div>
          {result.missing_count === 0 ? (
            <div className="empty-state" style={{ color: "var(--color-success)" }}>
              ✓ All characters have this blueprint!
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>Character</th><th>Class</th><th>Status</th></tr>
              </thead>
              <tbody>
                {result.characters.map((c) => (
                  <tr key={c.id}>
                    <td className="char-name-cell">{c.name}</td>
                    <td><span className="char-class-tag">{c.class || "—"}</span></td>
                    <td>
                      <span className={`status-badge status-${c.status}`}>{c.status.replace(/_/g, " ")}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

// ── Unique Blueprints Report ─────────────────────────────────────────────
function UniqueBlueprintsReport() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ran, setRan] = useState(false);

  async function run() {
    setLoading(true);
    setRan(true);
    try {
      const r = await api.reportUnique();
      setData(r);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="panel mb-md">
        <div className="panel-body">
          <p style={{ fontFamily: "var(--font-body)", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>
            Shows blueprints that only a single character has learned — useful for identifying rare exclusives or characters with unique advantages.
          </p>
          <button className="btn btn-primary" onClick={run} disabled={loading}>
            {loading ? "Running..." : "Find Unique Blueprints"}
          </button>
        </div>
      </div>

      {ran && !loading && data !== null && (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Exclusively Learned Blueprints</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-muted)" }}>{data.length} found</span>
          </div>
          {data.length === 0 ? (
            <div className="empty-state">No exclusively-learned blueprints found.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr><th></th><th>Blueprint</th><th>Category</th><th>Rarity</th><th>Only Character</th><th>Class</th></tr>
              </thead>
              <tbody>
                {data.map((r) => (
                  <tr key={`${r.id}-${r.char_id}`}>
                    <td style={{ textAlign: "center", width: 36 }}><BlueprintIcon icon={r.icon} icon_url={r.icon_url} size={24} /></td>
                    <td style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "0.85rem" }}>{r.name}</td>
                    <td><span className="tag">{r.category}</span></td>
                    <td><span className={`rarity rarity-${r.rarity}`}>{r.rarity}</span></td>
                    <td className="char-name-cell">{r.char_name}</td>
                    <td><span className="char-class-tag">{r.char_class || "—"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

// ── Search Report ────────────────────────────────────────────────────────
function SearchReport() {
  const [q, setQ] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run(e) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setLoading(true);
    try {
      const r = await api.search(q.trim());
      setResult(r);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="panel mb-md">
        <div className="panel-body">
          <form onSubmit={run} style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end" }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label className="form-label">Search across blueprints & characters</label>
              <input
                className="form-input"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Enter at least 2 characters..."
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={loading || q.trim().length < 2}>
              {loading ? "Searching..." : "Search"}
            </button>
          </form>
        </div>
      </div>

      {result && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Blueprints ({result.blueprints.length})</span>
            </div>
            {result.blueprints.length === 0 ? (
              <div className="empty-state">No blueprints found.</div>
            ) : (
              <table className="data-table">
                <thead><tr><th></th><th>Name</th><th>Category</th><th>Rarity</th></tr></thead>
                <tbody>
                  {result.blueprints.map((b) => (
                    <tr key={b.id}>
                      <td style={{ textAlign: "center", width: 36 }}><BlueprintIcon icon={b.icon} icon_url={b.icon_url} size={24} /></td>
                      <td style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "0.85rem" }}>{b.name}</td>
                      <td><span className="tag">{b.category}</span></td>
                      <td><span className={`rarity rarity-${b.rarity}`}>{b.rarity}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Characters ({result.characters.length})</span>
            </div>
            {result.characters.length === 0 ? (
              <div className="empty-state">No characters found.</div>
            ) : (
              <table className="data-table">
                <thead><tr><th>Name</th><th>Class</th><th>Notes</th></tr></thead>
                <tbody>
                  {result.characters.map((c) => (
                    <tr key={c.id}>
                      <td className="char-name-cell">{c.name}</td>
                      <td><span className="char-class-tag">{c.class || "—"}</span></td>
                      <td className="text-muted text-sm">{c.notes || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Extras Report ─────────────────────────────────────────────────────────
function ExtrasReport() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ran, setRan] = useState(false);
  const [charFilter, setCharFilter] = useState("All");

  async function run() {
    setLoading(true); setRan(true);
    try { setData(await api.reportExtras()); } finally { setLoading(false); }
  }

  const chars = data ? ["All", ...new Set(data.map(r => r.char_name))] : ["All"];
  const filtered = data ? (charFilter === "All" ? data : data.filter(r => r.char_name === charFilter)) : [];
  const totalExtras = filtered.reduce((s, r) => s + r.extras, 0);

  return (
    <div>
      <div className="panel mb-md">
        <div className="panel-body">
          <p style={{ fontFamily: "var(--font-body)", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>
            Shows every character/blueprint pair where spare copies exist — learned and still holding copies, or multiple unlearned copies.
          </p>
          <button className="btn btn-primary" onClick={run} disabled={loading}>
            {loading ? "Running..." : "Find All Extras"}
          </button>
        </div>
      </div>
      {ran && !loading && data !== null && (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Extra Copies</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-muted)" }}>
              {filtered.length} entries · {totalExtras} total extra cop{totalExtras !== 1 ? "ies" : "y"}
            </span>
          </div>
          {data.length > 0 && (
            <div style={{ padding: "0.5rem 1rem 0" }}>
              <div className="filter-row">
                {chars.map(c => (
                  <button key={c} className={`filter-pill ${charFilter === c ? "active" : ""}`} onClick={() => setCharFilter(c)}>{c}</button>
                ))}
              </div>
            </div>
          )}
          {filtered.length === 0 ? (
            <div className="empty-state">No extra copies found.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Blueprint</th>
                  <th>Category</th>
                  <th>Character</th>
                  <th>Learned</th>
                  <th>Copies Held</th>
                  <th>Extras</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, i) => (
                  <tr key={i}>
                    <td style={{ textAlign: "center", width: 36 }}><BlueprintIcon icon={r.icon} icon_url={r.icon_url} size={24} /></td>
                    <td style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "0.85rem" }}>{r.bp_name}</td>
                    <td><span className="tag">{r.category}</span></td>
                    <td>
                      <span className="char-name-cell">{r.char_name}</span>
                      {r.char_class && <span className="char-class-tag">{r.char_class}</span>}
                    </td>
                    <td>
                      {r.learned
                        ? <span style={{ color: "var(--amber)", fontFamily: "var(--font-mono)", fontSize: "0.72rem" }}>✓ Yes</span>
                        : <span style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.72rem" }}>○ No</span>}
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", color: "var(--color-success)", textAlign: "center" }}>{r.acquired_count}</td>
                    <td style={{ fontFamily: "var(--font-mono)", color: "var(--cyan)", fontWeight: 700, textAlign: "center" }}>{r.extras}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Reports Page ────────────────────────────────────────────────────
const REPORT_TABS = [
  { id: "summary",  label: "Character Summary" },
  { id: "coverage", label: "Blueprint Coverage" },
  { id: "missing",  label: "Missing Blueprint" },
  { id: "extras",   label: "Extras" },
  { id: "unique",   label: "Exclusive Blueprints" },
  { id: "search",   label: "Search" },
];

export default function ReportsPage() {
  const [tab, setTab] = useState("summary");

  return (
    <div>
      <div className="flex items-center justify-between mb-md">
        <h1 style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1.5rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-accent)" }}>
          Reports &amp; Analytics
        </h1>
      </div>

      <div className="tab-bar">
        {REPORT_TABS.map((t) => (
          <button key={t.id} className={`tab-btn ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "summary"  && <CharSummaryReport />}
      {tab === "coverage" && <BlueprintCoverageReport />}
      {tab === "missing"  && <MissingBlueprintReport />}
      {tab === "extras"   && <ExtrasReport />}
      {tab === "unique"   && <UniqueBlueprintsReport />}
      {tab === "search"   && <SearchReport />}
    </div>
  );
}
