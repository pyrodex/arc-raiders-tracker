import React, { useEffect, useState } from "react";
import { api } from "../api.js";

function ProgressBar({ pct }) {
  return (
    <div className="progress-bar-wrap">
      <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState([]);
  const [coverage, setCoverage] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.reportSummary(), api.reportCoverage()])
      .then(([s, c]) => { setSummary(s); setCoverage(c); })
      .finally(() => setLoading(false));
  }, []);

  const totalChars = summary.length;
  const totalBps = coverage.length;
  const totalLearned = summary.reduce((a, c) => a + c.learned, 0);
  const totalAcquired = summary.reduce((a, c) => a + c.acquired, 0);
  const avgCompletion = totalChars
    ? Math.round(summary.reduce((a, c) => a + c.completion_pct, 0) / totalChars)
    : 0;

  // Blueprint coverage: % of chars that have learned each bp
  const uncoveredBps = coverage.filter((b) => b.learned === 0 && totalChars > 0);
  const fullyLearned = coverage.filter((b) => b.not_acquired === 0 && totalChars > 0 && b.learned > 0);

  if (loading) return <div className="empty-state" style={{ marginTop: "4rem" }}>Loading dashboard...</div>;

  if (totalChars === 0 || totalBps === 0) {
    return (
      <div style={{ textAlign: "center", marginTop: "5rem" }}>
        <div style={{ fontFamily: "var(--font-display)", fontSize: "1.8rem", fontWeight: 700, color: "var(--amber)", letterSpacing: "0.15em", marginBottom: "0.75rem", textTransform: "uppercase" }}>
          ARC Raiders Blueprint Tracker
        </div>
        <div style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.8rem", marginBottom: "2rem" }}>
          Get started by adding characters and blueprints in the Admin panel.
        </div>
        <div style={{ display: "flex", gap: "1rem", justifyContent: "center", flexWrap: "wrap" }}>
          <div className="panel" style={{ padding: "1.5rem", maxWidth: 260 }}>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1rem", color: "var(--cyan)", marginBottom: "0.5rem" }}>① Admin</div>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.82rem" }}>Add your characters and the blueprints you want to track.</p>
          </div>
          <div className="panel" style={{ padding: "1.5rem", maxWidth: 260 }}>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1rem", color: "var(--cyan)", marginBottom: "0.5rem" }}>② Tracker</div>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.82rem" }}>Mark each blueprint as Not Acquired, Acquired, or Learned per character.</p>
          </div>
          <div className="panel" style={{ padding: "1.5rem", maxWidth: 260 }}>
            <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1rem", color: "var(--cyan)", marginBottom: "0.5rem" }}>③ Reports</div>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.82rem" }}>Analyze who's missing what, coverage stats, and unique exclusives.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-md">
        <h1 style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1.5rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-accent)" }}>
          Dashboard
        </h1>
      </div>

      {/* Top stats */}
      <div className="stat-grid mb-lg">
        <div className="stat-tile">
          <div className="stat-label">Characters</div>
          <div className="stat-value cyan">{totalChars}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Blueprints</div>
          <div className="stat-value">{totalBps}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Learned (total)</div>
          <div className="stat-value">{totalLearned}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Acquired</div>
          <div className="stat-value green">{totalAcquired}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Avg Completion</div>
          <div className="stat-value cyan">{avgCompletion}%</div>
        </div>
        <div className="stat-tile">
          <div className="stat-label">Fully Covered</div>
          <div className="stat-value" style={{ color: fullyLearned.length > 0 ? "#48c878" : "var(--text-muted)", fontSize: "1.4rem" }}>
            {fullyLearned.length} / {totalBps}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        {/* Character leaderboard */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Character Completion</span>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>Character</th><th>Class</th><th>Learned</th><th>Progress</th></tr>
            </thead>
            <tbody>
              {[...summary]
                .sort((a, b) => b.completion_pct - a.completion_pct)
                .map((c) => (
                  <tr key={c.id}>
                    <td className="char-name-cell">{c.name}</td>
                    <td><span className="char-class-tag">{c.class || "—"}</span></td>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--amber)" }}>
                      {c.learned}/{c.total}
                    </td>
                    <td>
                      <div className="flex items-center gap-sm">
                        <ProgressBar pct={c.completion_pct} />
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                          {c.completion_pct}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {/* Uncovered blueprints */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Blueprints No One Has Learned</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-muted)" }}>
              {uncoveredBps.length} total
            </span>
          </div>
          {uncoveredBps.length === 0 ? (
            <div className="empty-state" style={{ color: "#48c878" }}>
              ✓ Every blueprint has been learned by at least one character.
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>Blueprint</th><th>Category</th><th>Rarity</th></tr>
              </thead>
              <tbody>
                {uncoveredBps.slice(0, 20).map((b) => (
                  <tr key={b.id}>
                    <td style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "0.83rem" }}>{b.name}</td>
                    <td><span className="tag">{b.category}</span></td>
                    <td><span className={`rarity rarity-${b.rarity}`}>{b.rarity}</span></td>
                  </tr>
                ))}
                {uncoveredBps.length > 20 && (
                  <tr><td colSpan={3} className="text-muted text-mono" style={{ textAlign: "center", fontSize: "0.7rem" }}>
                    + {uncoveredBps.length - 20} more — check Reports for full list
                  </td></tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
