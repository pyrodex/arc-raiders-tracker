import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../Toast.jsx";

// ── small inline CSS additions ──────────────────────────────────────────────
const extrasBadgeStyle = {
  display: "inline-flex",
  alignItems: "center",
  gap: "0.2rem",
  fontFamily: "var(--font-mono)",
  fontSize: "0.65rem",
  background: "rgba(232,160,48,0.15)",
  border: "1px solid var(--amber-dark)",
  color: "var(--amber)",
  borderRadius: "10px",
  padding: "0.1rem 0.45rem",
  whiteSpace: "nowrap",
};

const countBtnStyle = (disabled) => ({
  width: 22,
  height: 22,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "var(--bg-dark)",
  border: "1px solid var(--border)",
  borderRadius: 2,
  color: disabled ? "var(--text-muted)" : "var(--text-secondary)",
  cursor: disabled ? "default" : "pointer",
  fontSize: "0.9rem",
  lineHeight: 1,
  flexShrink: 0,
});

// ── Blueprint card ──────────────────────────────────────────────────────────
function BpCard({ bp, pending, onChange }) {
  const learned        = pending?.learned        ?? bp.learned;
  const acquired_count = pending?.acquired_count ?? bp.acquired_count;
  const ext            = learned ? acquired_count : Math.max(0, acquired_count - 1);
  const isDirty        = pending !== undefined;

  // Determine visual state
  const cardClass = learned ? "learned" : acquired_count > 0 ? "acquired" : "not_acquired";

  function toggleLearned() {
    onChange({ learned: learned ? 0 : 1, acquired_count });
  }

  function adjustCount(delta) {
    const next = Math.max(0, acquired_count + delta);
    onChange({ learned, acquired_count: next });
  }

  return (
    <div className={`bp-card ${cardClass}`}>
      {/* Name row */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "0.35rem" }}>
        <span style={{ fontSize: "1rem", lineHeight: 1.2, flexShrink: 0 }}>{bp.icon || "📋"}</span>
        <div style={{
          fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "0.85rem",
          color: isDirty ? "var(--amber)" : "var(--text-primary)", lineHeight: 1.2, flex: 1,
        }}>
          {bp.name}
          {isDirty && <span style={{ color: "var(--amber)", marginLeft: "0.3rem", fontSize: "0.6rem" }}>●</span>}
        </div>
        {ext > 0 && <span style={extrasBadgeStyle}>+{ext} extra{ext !== 1 ? "s" : ""}</span>}
      </div>

      {/* Meta */}
      <div className="bp-card-meta">
        <span className="tag">{bp.category}</span>
        {bp.item_type && <span>{bp.item_type}</span>}
        <span className={`rarity rarity-${bp.rarity}`}>{bp.rarity}</span>
      </div>

      {/* Source */}
      {bp.source && (
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.63rem", color: "var(--text-muted)", lineHeight: 1.3 }}>
          {bp.source}
        </div>
      )}

      {/* Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.35rem", flexWrap: "wrap" }}>
        {/* Learned toggle */}
        <button
          onClick={toggleLearned}
          style={{
            flex: 1,
            fontFamily: "var(--font-mono)",
            fontSize: "0.68rem",
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            padding: "0.28rem 0.5rem",
            borderRadius: 2,
            border: `1px solid ${learned ? "var(--amber-dark)" : "var(--border)"}`,
            background: learned ? "var(--amber-glow)" : "var(--bg-dark)",
            color: learned ? "var(--amber)" : "var(--text-muted)",
            cursor: "pointer",
            transition: "all 0.12s",
            whiteSpace: "nowrap",
          }}
        >
          {learned ? "✓ Learned" : "○ Not Learned"}
        </button>

        {/* Acquired count */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Copies
          </span>
          <button style={countBtnStyle(acquired_count <= 0)} onClick={() => adjustCount(-1)} disabled={acquired_count <= 0}>−</button>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: "0.82rem", minWidth: 18, textAlign: "center",
            color: acquired_count > 0 ? "#40c878" : "var(--text-muted)", fontWeight: 600,
          }}>
            {acquired_count}
          </span>
          <button style={countBtnStyle(false)} onClick={() => adjustCount(1)}>+</button>
        </div>
      </div>

      {/* State summary line */}
      {(acquired_count > 0 || learned) && (
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
          {learned && acquired_count === 0 && "Learned — no copies in inventory"}
          {learned && acquired_count > 0  && `Learned + ${acquired_count} cop${acquired_count === 1 ? "y" : "ies"} in inventory (${ext} extra${ext !== 1 ? "s" : ""})`}
          {!learned && acquired_count === 1 && "1 copy — not yet learned"}
          {!learned && acquired_count > 1  && `${acquired_count} copies — not yet learned (${ext} extra${ext !== 1 ? "s" : ""})`}
        </div>
      )}
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────
export default function TrackerPage() {
  const toast = useToast();
  const [characters, setCharacters]   = useState([]);
  const [selectedChar, setSelectedChar] = useState(null);
  const [blueprints, setBlueprints]   = useState([]);
  const [loading, setLoading]         = useState(false);
  const [catFilter, setCatFilter]     = useState("All");
  const [stateFilter, setStateFilter] = useState("All");
  const [search, setSearch]           = useState("");
  const [pending, setPending]         = useState({}); // { blueprint_id: {learned, acquired_count} }
  const [saving, setSaving]           = useState(false);

  useEffect(() => {
    api.getCharacters().then((chars) => {
      setCharacters(chars);
      if (chars.length > 0) setSelectedChar(chars[0]);
    });
  }, []);

  useEffect(() => {
    if (!selectedChar) return;
    setLoading(true);
    setPending({});
    api.getCharacterBlueprints(selectedChar.id)
      .then(setBlueprints)
      .finally(() => setLoading(false));
  }, [selectedChar]);

  function handleChange(bp, update) {
    setPending((p) => ({ ...p, [bp.id]: update }));
  }

  const hasPending = Object.keys(pending).length > 0;

  async function saveChanges() {
    if (!selectedChar || !hasPending) return;
    setSaving(true);
    try {
      const updates = Object.entries(pending).map(([bid, v]) => ({
        blueprint_id: parseInt(bid),
        learned: v.learned,
        acquired_count: v.acquired_count,
      }));
      await api.bulkSetStatus(selectedChar.id, updates);
      setBlueprints((bps) => bps.map((b) =>
        pending[b.id] ? { ...b, ...pending[b.id], extras: pending[b.id].learned ? pending[b.id].acquired_count : Math.max(0, pending[b.id].acquired_count - 1) } : b
      ));
      setPending({});
      toast(`Saved ${updates.length} update${updates.length !== 1 ? "s" : ""}`);
    } catch (e) {
      toast(e.message, "error");
    } finally {
      setSaving(false);
    }
  }

  // ── Filters ──
  const categories = ["All", ...new Set(blueprints.map((b) => b.category))];

  const STATE_FILTERS = [
    { id: "All",           label: "All" },
    { id: "learned",       label: "Learned" },
    { id: "acquired",      label: "Has Copies" },
    { id: "extras",        label: "Has Extras" },
    { id: "not_acquired",  label: "Missing" },
  ];

  const filtered = blueprints.filter((b) => {
    const lrn = pending[b.id]?.learned        ?? b.learned;
    const cnt = pending[b.id]?.acquired_count ?? b.acquired_count;
    const ext = lrn ? cnt : Math.max(0, cnt - 1);
    const matchCat = catFilter === "All" || b.category === catFilter;
    const matchSearch = !search || b.name.toLowerCase().includes(search.toLowerCase()) ||
      b.category.toLowerCase().includes(search.toLowerCase());
    let matchState = true;
    if (stateFilter === "learned")      matchState = lrn === 1;
    if (stateFilter === "acquired")     matchState = cnt > 0;
    if (stateFilter === "extras")       matchState = ext > 0;
    if (stateFilter === "not_acquired") matchState = lrn === 0 && cnt === 0;
    return matchCat && matchSearch && matchState;
  });

  // ── Summary counts (across ALL blueprints for selected char) ──
  const totals = blueprints.reduce((acc, b) => {
    const lrn = pending[b.id]?.learned        ?? b.learned;
    const cnt = pending[b.id]?.acquired_count ?? b.acquired_count;
    const ext = lrn ? cnt : Math.max(0, cnt - 1);
    acc.learned        += lrn;
    acc.acquired       += cnt > 0 ? 1 : 0;
    acc.extras         += ext;
    acc.not_acquired   += (lrn === 0 && cnt === 0) ? 1 : 0;
    return acc;
  }, { learned: 0, acquired: 0, extras: 0, not_acquired: 0 });

  const total = blueprints.length;
  const pct   = total ? Math.round((totals.learned / total) * 100) : 0;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-md" style={{ flexWrap: "wrap", gap: "0.75rem" }}>
        <h1 style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1.5rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-accent)" }}>
          Blueprint Tracker
        </h1>
        {hasPending && (
          <div className="flex gap-sm">
            <button className="btn btn-secondary" onClick={() => setPending({})}>
              Discard ({Object.keys(pending).length})
            </button>
            <button className="btn btn-primary" onClick={saveChanges} disabled={saving}>
              {saving ? "Saving…" : `Save (${Object.keys(pending).length})`}
            </button>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "210px 1fr", gap: "1rem", alignItems: "start" }}>
        {/* ── Character sidebar ── */}
        <div className="panel" style={{ position: "sticky", top: "72px" }}>
          <div className="panel-header"><span className="panel-title">Characters</span></div>
          <div style={{ padding: "0.4rem" }}>
            {characters.length === 0 ? (
              <div className="empty-state" style={{ padding: "1rem" }}>No characters. Add in Admin.</div>
            ) : characters.map((c) => {
              const isSel = selectedChar?.id === c.id;
              return (
                <button key={c.id} onClick={() => setSelectedChar(c)} style={{
                  display: "block", width: "100%", textAlign: "left",
                  background: isSel ? "var(--bg-active)" : "none",
                  border: `1px solid ${isSel ? "var(--border-accent)" : "transparent"}`,
                  borderRadius: "var(--radius)", padding: "0.55rem 0.7rem",
                  marginBottom: "0.2rem", cursor: "pointer", transition: "all 0.12s",
                }}>
                  <div style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "0.88rem", color: isSel ? "var(--amber)" : "var(--text-primary)" }}>
                    {c.name}
                  </div>
                  {c.class && <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--cyan)", marginTop: "0.1rem" }}>{c.class}</div>}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Right panel ── */}
        <div>
          {selectedChar ? (
            <>
              {/* Stats */}
              <div className="stat-grid" style={{ gridTemplateColumns: "repeat(5, 1fr)", marginBottom: "1rem" }}>
                <div className="stat-tile">
                  <div className="stat-label">Total</div>
                  <div className="stat-value">{total}</div>
                </div>
                <div className="stat-tile">
                  <div className="stat-label">Learned</div>
                  <div className="stat-value" style={{ color: "var(--amber)" }}>{totals.learned}</div>
                </div>
                <div className="stat-tile">
                  <div className="stat-label">Has Copies</div>
                  <div className="stat-value green">{totals.acquired}</div>
                </div>
                <div className="stat-tile">
                  <div className="stat-label">Extras</div>
                  <div className="stat-value cyan">{totals.extras}</div>
                </div>
                <div className="stat-tile">
                  <div className="stat-label">Missing</div>
                  <div className="stat-value" style={{ color: totals.not_acquired > 0 ? "#e05050" : "#48c878", fontSize: "1.4rem" }}>{totals.not_acquired}</div>
                </div>
              </div>

              {/* Progress bar */}
              <div style={{ marginBottom: "1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.3rem" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Learned Progress</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--amber)" }}>{pct}%</span>
                </div>
                <div className="progress-bar-wrap" style={{ height: 6 }}>
                  <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
                </div>
              </div>

              {/* Filters */}
              <div className="panel" style={{ marginBottom: "1rem" }}>
                <div className="panel-body" style={{ paddingBottom: "0.5rem" }}>
                  <div className="flex items-center gap-md mb-sm" style={{ flexWrap: "wrap" }}>
                    <div className="search-bar">
                      <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search blueprints…" />
                    </div>
                    <div className="filter-row" style={{ margin: 0 }}>
                      {STATE_FILTERS.map((s) => (
                        <button key={s.id} className={`filter-pill ${stateFilter === s.id ? "active" : ""}`} onClick={() => setStateFilter(s.id)}>
                          {s.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="filter-row">
                    {categories.map((c) => (
                      <button key={c} className={`filter-pill ${catFilter === c ? "active" : ""}`} onClick={() => setCatFilter(c)}>{c}</button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Blueprint grid */}
              {loading ? (
                <div className="empty-state">Loading blueprints…</div>
              ) : filtered.length === 0 ? (
                <div className="empty-state">No blueprints match your filters.</div>
              ) : (
                <div className="bp-grid">
                  {filtered.map((bp) => (
                    <BpCard
                      key={bp.id}
                      bp={bp}
                      pending={pending[bp.id]}
                      onChange={(update) => handleChange(bp, update)}
                    />
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="empty-state" style={{ marginTop: "3rem" }}>Select a character to view their blueprints.</div>
          )}
        </div>
      </div>
    </div>
  );
}
