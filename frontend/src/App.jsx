import React, { useState, useEffect } from "react";
import { ToastProvider } from "./Toast.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import TrackerPage from "./pages/TrackerPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";
import ThemeToggle from "./ThemeToggle.jsx";

const PAGES = [
  { id: "dashboard", label: "Dashboard" },
  { id: "tracker",   label: "Tracker"   },
  { id: "reports",   label: "Reports"   },
  { id: "admin",     label: "Admin"     },
];

function resolveTheme(mode) {
  if (mode === "auto") {
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  return mode;
}

function App() {
  const [page, setPage] = useState("dashboard");
  const [themeMode, setThemeMode] = useState(
    () => localStorage.getItem("themeMode") || "dark"
  );

  useEffect(() => {
    const apply = () => {
      document.documentElement.dataset.theme = resolveTheme(themeMode);
    };
    apply();
    localStorage.setItem("themeMode", themeMode);

    // Re-apply if auto mode and system preference changes
    if (themeMode === "auto") {
      const mq = window.matchMedia("(prefers-color-scheme: light)");
      mq.addEventListener("change", apply);
      return () => mq.removeEventListener("change", apply);
    }
  }, [themeMode]);

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
          <ThemeToggle mode={themeMode} onChange={setThemeMode} />
        </header>
        <main className="main-content">
          {page === "dashboard" && <DashboardPage />}
          {page === "tracker"   && <TrackerPage />}
          {page === "reports"   && <ReportsPage />}
          {page === "admin"     && <AdminPage />}
        </main>
      </div>
    </ToastProvider>
  );
}

export default App;
