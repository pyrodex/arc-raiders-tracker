import React from "react";

/**
 * Renders a blueprint icon: a wiki image thumbnail when icon_url is set,
 * otherwise falls back to the emoji icon string.
 */
export default function BlueprintIcon({ icon, icon_url, size = 24, style = {} }) {
  if (icon_url) {
    return (
      <img
        src={icon_url}
        alt={icon || "blueprint"}
        width={size}
        height={size}
        style={{
          objectFit: "contain",
          imageRendering: "auto",
          verticalAlign: "middle",
          flexShrink: 0,
          ...style,
        }}
        onError={(e) => {
          // If image fails to load, swap in the emoji span
          const span = document.createElement("span");
          span.textContent = icon || "📋";
          e.target.replaceWith(span);
        }}
      />
    );
  }
  return <span style={{ flexShrink: 0, ...style }}>{icon || "📋"}</span>;
}
