import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../Toast.jsx";
import BlueprintIcon from "../BlueprintIcon.jsx";

// ── Generic confirm modal ─────────────────────────────────────────────────
function ConfirmModal({ msg, onConfirm, onCancel }) {
  return (
    <div className="modal-backdrop">
      <div className="modal" style={{ maxWidth: 380 }}>
        <div className="modal-header">
          <span className="modal-title">Confirm</span>
        </div>
        <div className="modal-body">
          <p style={{ fontFamily: "var(--font-body)", color: "var(--text-secondary)", fontSize: "0.88rem" }}>{msg}</p>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button className="btn btn-danger" onClick={onConfirm}>Delete</button>
        </div>
      </div>
    </div>
  );
}

// ── Character Form Modal ──────────────────────────────────────────────────
function CharacterModal({ initial, onSave, onClose }) {
  const [form, setForm] = useState(
    initial || { name: "", class: "", notes: "" }
  );
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">{initial ? "Edit Character" : "Add Character"}</span>
          <button className="btn btn-icon btn-secondary" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="form-row mb-md">
            <div className="form-group">
              <label className="form-label">Character Name *</label>
              <input className="form-input" value={form.name} onChange={set("name")} placeholder="Callsign..." />
            </div>
            <div className="form-group">
              <label className="form-label">Class / Role</label>
              <input className="form-input" value={form.class} onChange={set("class")} placeholder="e.g. Recon, Support..." />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Notes</label>
            <textarea className="form-textarea" value={form.notes} onChange={set("notes")} placeholder="Optional notes..." />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => form.name.trim() && onSave(form)}>
            {initial ? "Save Changes" : "Add Character"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Blueprint Form Modal ──────────────────────────────────────────────────
const RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary"];

const CATEGORIES = ["Weapons", "Mods", "Grenades", "Mines", "Quick Use", "Augments", "Materials"];

function BlueprintModal({ initial, onSave, onClose }) {
  const [form, setForm] = useState(
    initial || { name: "", category: "Weapons", rarity: "Epic", icon: "📋", description: "" }
  );
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-header">
          <span className="modal-title">{initial ? "Edit Blueprint" : "Add Blueprint"}</span>
          <button className="btn btn-icon btn-secondary" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="form-row mb-md">
            <div className="form-group" style={{ flex: 2 }}>
              <label className="form-label">Blueprint Name *</label>
              <input className="form-input" value={form.name} onChange={set("name")} placeholder="e.g. Anvil" />
            </div>
            <div className="form-group" style={{ flex: "none", width: 80 }}>
              <label className="form-label">Icon</label>
              <input className="form-input" value={form.icon} onChange={set("icon")} placeholder="📋" style={{ textAlign: "center", fontSize: "1.1rem" }} />
            </div>
            <div className="form-group">
              <label className="form-label">Rarity</label>
              <select className="form-select" value={form.rarity} onChange={set("rarity")}>
                {RARITIES.map((r) => <option key={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <div className="form-row mb-md">
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-select" value={form.category} onChange={set("category")}>
                {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Notes</label>
            <textarea className="form-textarea" value={form.description} onChange={set("description")} placeholder="Optional notes..." />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => form.name.trim() && onSave(form)}>
            {initial ? "Save Changes" : "Add Blueprint"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Admin Page ───────────────────────────────────────────────────────
export default function AdminPage() {
  const toast = useToast();
  const [tab, setTab] = useState("characters");

  // Characters state
  const [characters, setCharacters] = useState([]);
  const [charModal, setCharModal] = useState(null); // null | "add" | {char}
  const [confirmDel, setConfirmDel] = useState(null);

  // Blueprints state
  const [blueprints, setBlueprints] = useState([]);
  const [bpModal, setBpModal] = useState(null);
  const [bpSearch, setBpSearch] = useState("");
  const [bpCatFilter, setBpCatFilter] = useState("All");
  const [confirmDelBp, setConfirmDelBp] = useState(null);

  const loadChars = () => api.getCharacters().then(setCharacters).catch(() => {});
  const loadBps = () => api.getBlueprints().then(setBlueprints).catch(() => {});

  useEffect(() => {
    loadChars();
    loadBps();
  }, []);

  // ── Character handlers
  async function saveChar(form) {
    try {
      if (charModal?.id) {
        await api.updateCharacter(charModal.id, form);
        toast("Character updated");
      } else {
        await api.createCharacter(form);
        toast("Character added");
      }
      setCharModal(null);
      loadChars();
    } catch (e) { toast(e.message, "error"); }
  }

  async function deleteChar(id) {
    try {
      await api.deleteCharacter(id);
      toast("Character deleted");
      setConfirmDel(null);
      loadChars();
    } catch (e) { toast(e.message, "error"); }
  }

  // ── Blueprint handlers
  async function saveBp(form) {
    try {
      if (bpModal?.id) {
        await api.updateBlueprint(bpModal.id, form);
        toast("Blueprint updated");
      } else {
        await api.createBlueprint(form);
        toast("Blueprint added");
      }
      setBpModal(null);
      loadBps();
    } catch (e) { toast(e.message, "error"); }
  }

  async function deleteBp(id) {
    try {
      await api.deleteBlueprint(id);
      toast("Blueprint deleted");
      setConfirmDelBp(null);
      loadBps();
    } catch (e) { toast(e.message, "error"); }
  }

  async function seedData() {
    try {
      const r = await api.seed();
      toast(`Seeded ${r.seeded} sample blueprints`);
      loadBps();
    } catch (e) { toast(e.message, "error"); }
  }

  // ── Filtered blueprints
  const categories = ["All", ...new Set(blueprints.map((b) => b.category))];
  const filteredBps = blueprints.filter((b) => {
    const matchCat = bpCatFilter === "All" || b.category === bpCatFilter;
    const matchSearch = !bpSearch || b.name.toLowerCase().includes(bpSearch.toLowerCase()) ||
      b.category.toLowerCase().includes(bpSearch.toLowerCase());
    return matchCat && matchSearch;
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-md">
        <h1 style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1.5rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-accent)" }}>
          Admin Panel
        </h1>
      </div>

      <div className="tab-bar">
        <button className={`tab-btn ${tab === "characters" ? "active" : ""}`} onClick={() => setTab("characters")}>
          Characters ({characters.length})
        </button>
        <button className={`tab-btn ${tab === "blueprints" ? "active" : ""}`} onClick={() => setTab("blueprints")}>
          Blueprints ({blueprints.length})
        </button>
      </div>

      {/* ── Characters Tab ── */}
      {tab === "characters" && (
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Registered Characters</span>
            <button className="btn btn-primary" onClick={() => setCharModal("add")}>+ Add Character</button>
          </div>
          <div>
            {characters.length === 0 ? (
              <div className="empty-state">No characters registered — add one to get started.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Class / Role</th>
                    <th>Notes</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {characters.map((c, i) => (
                    <tr key={c.id}>
                      <td className="text-muted text-mono">{i + 1}</td>
                      <td className="char-name-cell">{c.name}</td>
                      <td><span className="char-class-tag">{c.class || "—"}</span></td>
                      <td className="text-muted text-sm">{c.notes || "—"}</td>
                      <td className="text-muted text-mono text-sm">{c.created_at?.slice(0, 10)}</td>
                      <td>
                        <div className="flex gap-sm">
                          <button className="btn btn-secondary btn-sm" onClick={() => setCharModal(c)}>Edit</button>
                          <button className="btn btn-danger btn-sm" onClick={() => setConfirmDel(c)}>Del</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ── Blueprints Tab ── */}
      {tab === "blueprints" && (
        <div>
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Blueprint Registry ({filteredBps.length} / {blueprints.length})</span>
              <div className="flex gap-sm">
                <button className="btn btn-secondary" onClick={seedData}>⚡ Seed ARC Raiders Blueprints</button>
                <button className="btn btn-primary" onClick={() => setBpModal("add")}>+ Add Blueprint</button>
              </div>
            </div>
            <div className="panel-body">
              <div className="flex items-center gap-md mb-sm">
                <div className="search-bar">
                  <input
                    value={bpSearch}
                    onChange={(e) => setBpSearch(e.target.value)}
                    placeholder="Search blueprints..."
                  />
                </div>
              </div>
              <div className="filter-row">
                {categories.map((c) => (
                  <button key={c} className={`filter-pill ${bpCatFilter === c ? "active" : ""}`} onClick={() => setBpCatFilter(c)}>
                    {c}
                  </button>
                ))}
              </div>
            </div>
            {filteredBps.length === 0 ? (
              <div className="empty-state">No blueprints match your filters.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Icon</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Rarity</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredBps.map((b) => (
                    <tr key={b.id}>
                      <td style={{ textAlign: "center" }}><BlueprintIcon icon={b.icon} icon_url={b.icon_url} size={28} /></td>
                      <td style={{ fontFamily: "var(--font-display)", fontWeight: 600 }}>{b.name}</td>
                      <td><span className="tag">{b.category}</span></td>
                      <td><span className={`rarity rarity-${b.rarity}`}>{b.rarity}</span></td>
                      <td>
                        <div className="flex gap-sm">
                          <button className="btn btn-secondary btn-sm" onClick={() => setBpModal(b)}>Edit</button>
                          <button className="btn btn-danger btn-sm" onClick={() => setConfirmDelBp(b)}>Del</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      {(charModal === "add" || charModal?.id) && (
        <CharacterModal
          initial={charModal?.id ? charModal : null}
          onSave={saveChar}
          onClose={() => setCharModal(null)}
        />
      )}

      {confirmDel && (
        <ConfirmModal
          msg={`Delete character "${confirmDel.name}"? This will also remove all their blueprint data.`}
          onConfirm={() => deleteChar(confirmDel.id)}
          onCancel={() => setConfirmDel(null)}
        />
      )}

      {(bpModal === "add" || bpModal?.id) && (
        <BlueprintModal
          initial={bpModal?.id ? bpModal : null}
          onSave={saveBp}
          onClose={() => setBpModal(null)}
        />
      )}

      {confirmDelBp && (
        <ConfirmModal
          msg={`Delete blueprint "${confirmDelBp.name}"? This removes it from all character records.`}
          onConfirm={() => deleteBp(confirmDelBp.id)}
          onCancel={() => setConfirmDelBp(null)}
        />
      )}
    </div>
  );
}
