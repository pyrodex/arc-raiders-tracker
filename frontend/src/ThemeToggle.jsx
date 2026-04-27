import React from "react";

const MODES = [
  { id: "dark",  label: "☾", title: "Dark mode"  },
  { id: "light", label: "☀", title: "Light mode" },
  { id: "auto",  label: "⬤", title: "Auto (system)" },
];

export default function ThemeToggle({ mode, onChange }) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "0.15rem",
      background: "var(--bg-dark)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius)",
      padding: "0.15rem",
    }}>
      {MODES.map((m) => (
        <button
          key={m.id}
          title={m.title}
          onClick={() => onChange(m.id)}
          style={{
            background: mode === m.id ? "var(--bg-active)" : "transparent",
            border: mode === m.id ? "1px solid var(--border-accent)" : "1px solid transparent",
            color: mode === m.id ? "var(--text-accent)" : "var(--text-muted)",
            borderRadius: "2px",
            width: 26,
            height: 24,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            fontSize: m.id === "auto" ? "0.45rem" : "0.85rem",
            lineHeight: 1,
            transition: "all 0.12s",
          }}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
