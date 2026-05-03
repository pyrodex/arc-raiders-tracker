import React, { useEffect, useRef, useState, useCallback } from "react";
import { api } from "../api.js";
import { useToast } from "../Toast.jsx";
import BlueprintIcon from "../BlueprintIcon.jsx";

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
  width: 28,
  height: 28,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "var(--bg-dark)",
  border: "1px solid var(--border)",
  borderRadius: 3,
  color: disabled ? "var(--text-muted)" : "var(--text-secondary)",
  cursor: disabled ? "default" : "pointer",
  fontSize: "1rem",
  lineHeight: 1,
  flexShrink: 0,
});

// ── Blueprint card ──────────────────────────────────────────────────────────
function BpCard({ bp, onChange, saving }) {
  const learned        = Number(bp.learned        ?? 0);
  const acquired_count = Number(bp.acquired_count ?? 0);
  const ext            = learned ? acquired_count : Math.max(0, acquired_count - 1);
  const cardClass      = learned ? "learned" : acquired_count > 0 ? "acquired" : "not_acquired";

  function toggleLearned() {
    onChange(bp, { learned: learned ? 0 : 1, acquired_count });
  }

  function adjustCount(delta) {
    const next = Math.max(0, acquired_count + delta);
    onChange(bp, { learned, acquired_count: next });
  }

  return (
    <div className={`bp-card ${cardClass}`}>
      {/* Icon banner */}
      <div style={{
        display: "flex", justifyContent: "center", alignItems: "center",
        background: "var(--bg-dark)", borderRadius: "var(--radius)",
        padding: "0.5rem", marginBottom: "0.1rem", minHeight: 72,
        position: "relative",
      }}>
        <BlueprintIcon icon={bp.icon} icon_url={bp.icon_url} size={64} />
        {ext > 0 && (
          <span style={{ ...extrasBadgeStyle, position: "absolute", top: 4, right: 4 }}>
            +{ext} extra{ext !== 1 ? "s" : ""}
          </span>
        )}
        {saving && (
          <span style={{ position: "absolute", top: 4, left: 6, color: "var(--text-muted)", fontSize: "0.55rem" }}>↑</span>
        )}
      </div>

      {/* Name row */}
      <div style={{
        fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "1rem",
        color: "var(--text-primary)", lineHeight: 1.3,
        textAlign: "center",
      }}>
        {bp.name}
      </div>

      {/* Meta */}
      <div className="bp-card-meta" style={{ justifyContent: "center", flexWrap: "wrap" }}>
        <span className="tag">{bp.category}</span>
        <span className={`rarity rarity-${bp.rarity}`}>{bp.rarity}</span>
      </div>

      {/* Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.25rem", flexWrap: "wrap" }}>
        {/* Learned toggle */}
        <button
          onClick={toggleLearned}
          style={{
            flex: 1,
            fontFamily: "var(--font-mono)",
            fontSize: "0.8rem",
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            padding: "0.4rem 0.5rem",
            borderRadius: 3,
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
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.73rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Copies
          </span>
          <button style={countBtnStyle(acquired_count <= 0)} onClick={() => adjustCount(-1)} disabled={acquired_count <= 0}>−</button>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: "0.95rem", minWidth: 22, textAlign: "center",
            color: acquired_count > 0 ? "var(--color-success)" : "var(--text-muted)", fontWeight: 600,
          }}>
            {acquired_count}
          </span>
          <button style={countBtnStyle(false)} onClick={() => adjustCount(1)}>+</button>
        </div>
      </div>

    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────
export default function TrackerPage() {
  const toast = useToast();
  const [characters, setCharacters]     = useState([]);
  const [selectedChar, setSelectedChar] = useState(null);
  const [blueprints, setBlueprints]     = useState([]);
  const [loading, setLoading]           = useState(false);
  const [catFilter, setCatFilter]       = useState("All");
  const [stateFilter, setStateFilter]   = useState("All");
  const [search, setSearch]             = useState("");
  const [savingIds, setSavingIds]       = useState(new Set()); // bp ids currently being saved
  const debounceTimers = useRef({});

  useEffect(() => {
    api.getCharacters().then((chars) => {
      setCharacters(chars);
      if (chars.length > 0) setSelectedChar(chars[0]);
    });
  }, []);

  useEffect(() => {
    if (!selectedChar) return;
    setLoading(true);
    Object.values(debounceTimers.current).forEach(clearTimeout);
    debounceTimers.current = {};
    api.getCharacterBlueprints(selectedChar.id)
      .then(setBlueprints)
      .finally(() => setLoading(false));
  }, [selectedChar]);

  const handleChange = useCallback((bp, update) => {
    // Optimistically update local state immediately
    setBlueprints((bps) => bps.map((b) =>
      b.id === bp.id ? { ...b, ...update } : b
    ));

    // Debounce the API call so rapid +/- clicks coalesce into one request
    if (debounceTimers.current[bp.id]) clearTimeout(debounceTimers.current[bp.id]);
    debounceTimers.current[bp.id] = setTimeout(async () => {
      setSavingIds((s) => new Set([...s, bp.id]));
      try {
        await api.setStatus(selectedChar.id, bp.id, update.learned, update.acquired_count);
      } catch (e) {
        toast(e.message, "error");
        // Revert on failure
        setBlueprints((bps) => bps.map((b) =>
          b.id === bp.id ? { ...b, learned: bp.learned, acquired_count: bp.acquired_count } : b
        ));
      } finally {
        setSavingIds((s) => { const n = new Set(s); n.delete(bp.id); return n; });
      }
    }, 400);
  }, [selectedChar, toast]);

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
    const lrn = Number(b.learned ?? 0);
    const cnt = Number(b.acquired_count ?? 0);
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

  // ── Summary counts ──
  const totals = blueprints.reduce((acc, b) => {
    const lrn = Number(b.learned ?? 0);
    const cnt = Number(b.acquired_count ?? 0);
    const ext = lrn ? cnt : Math.max(0, cnt - 1);
    acc.learned      += lrn;
    acc.acquired     += cnt > 0 ? 1 : 0;
    acc.extras       += ext;
    acc.not_acquired += (lrn === 0 && cnt === 0) ? 1 : 0;
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
        {savingIds.size > 0 && (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Saving…
          </span>
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
                  <div className="stat-value" style={{ color: totals.not_acquired > 0 ? "var(--color-danger)" : "var(--color-success)", fontSize: "1.4rem" }}>{totals.not_acquired}</div>
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
                      saving={savingIds.has(bp.id)}
                      onChange={handleChange}
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
