import React, { useState } from "react";
import { ToastProvider } from "./Toast.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import TrackerPage from "./pages/TrackerPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";

const PAGES = [
  { id: "dashboard", label: "Dashboard" },
  { id: "tracker", label: "Tracker" },
  { id: "reports", label: "Reports" },
  { id: "admin", label: "Admin" },
];

function App() {
  const [page, setPage] = useState("dashboard");

  return (
    <ToastProvider>
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar-logo">
            ARC <span>Raiders</span>
            <span style={{ color: "var(--text-muted)", fontWeight: 400, fontSize: "0.75rem", marginLeft: "0.5rem", letterSpacing: "0.2em" }}>
              // BLUEPRINT DB
            </span>
          </div>
          <nav className="topbar-nav">
            {PAGES.map((p) => (
              <button
                key={p.id}
                className={`nav-btn ${page === p.id ? "active" : ""}`}
                onClick={() => setPage(p.id)}
              >
                {p.label}
              </button>
            ))}
          </nav>
          <div style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)", letterSpacing: "0.08em" }}>
            SECURE TERMINAL v1.0
          </div>
        </header>
        <main className="main-content">
          {page === "dashboard" && <DashboardPage />}
          {page === "tracker" && <TrackerPage />}
          {page === "reports" && <ReportsPage />}
          {page === "admin" && <AdminPage />}
        </main>
      </div>
    </ToastProvider>
  );
}

export default App;
