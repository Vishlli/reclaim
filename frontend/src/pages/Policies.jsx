import { useEffect, useState } from "react";
import { getPolicies, updatePolicy } from "../services/api";

const FIELDS = [
  { key: "max_attempts", label: "Maximum Recovery Attempts", type: "number" },
  { key: "max_discount", label: "Maximum Discount (%)", type: "number" },
  { key: "high_value_threshold", label: "High Value Threshold (₹)", type: "number" },
  { key: "manual_approval_threshold", label: "Manual Approval Threshold (₹)", type: "number" },
  { key: "contact_start_time", label: "Contact Window Start", type: "time" },
  { key: "contact_end_time", label: "Contact Window End", type: "time" },
];

export default function Policies() {
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = () => {
    setLoading(true);
    setError(false);
    getPolicies()
      .then((rows) => setPolicy(rows[0]))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const save = () => {
    setSaving(true);
    setSaved(false);
    updatePolicy(policy)
      .then(() => setSaved(true))
      .finally(() => setSaving(false));
  };

  if (loading) return <div className="text-muted text-sm">Loading policies…</div>;
  if (error)
    return (
      <div className="text-sm">
        <p className="text-danger mb-3">Unable to load policies.</p>
        <button onClick={load} className="border border-line rounded-lg px-3 py-1.5 hover:border-accent">Retry</button>
      </div>
    );

  return (
    <div className="bg-panel border border-line rounded-xl p-5 max-w-xl">
      <div className="grid grid-cols-2 gap-4">
        {FIELDS.map(({ key, label, type }) => (
          <div key={key}>
            <label className="block text-xs text-muted mb-1">{label}</label>
            <input
              type={type}
              value={policy[key]}
              onChange={(e) => setPolicy({ ...policy, [key]: e.target.value })}
              className="w-full border border-line rounded-lg px-3 py-2 text-sm"
            />
          </div>
        ))}
      </div>
      <button
        onClick={save}
        disabled={saving}
        className="mt-5 bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save Changes"}
      </button>
      {saved && <span className="ml-3 text-sm text-success">Policy updated.</span>}
    </div>
  );
}