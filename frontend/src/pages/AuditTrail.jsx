import { useEffect, useState } from "react";
import { getAuditTrail } from "../services/api";
import { formatDateTime } from "../utils/format";

export default function AuditTrail() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = () => {
    setLoading(true);
    setError(false);
    getAuditTrail().then(setEvents).catch(() => setError(true)).finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) return <div className="text-muted text-sm">Loading audit trail…</div>;
  if (error)
    return (
      <div className="text-sm">
        <p className="text-danger mb-3">Unable to load audit trail.</p>
        <button onClick={load} className="border border-line rounded-lg px-3 py-1.5 hover:border-accent">Retry</button>
      </div>
    );
  if (!events.length) return <div className="text-muted text-sm">No audit events yet.</div>;

  return (
    <div className="bg-panel border border-line rounded-xl overflow-hidden overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-canvas text-muted text-xs uppercase">
          <tr>
            <th className="text-left px-4 py-3">Timestamp</th>
            <th className="text-left px-4 py-3">Transaction</th>
            <th className="text-left px-4 py-3">Event</th>
            <th className="text-left px-4 py-3">Action</th>
            <th className="text-left px-4 py-3">Result</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id} className="border-t border-line">
              <td className="px-4 py-3 text-muted">{formatDateTime(e.executed_at)}</td>
              <td className="px-4 py-3">#{e.transaction_id}</td>
              <td className="px-4 py-3">{e.event_type.replaceAll("_", " ")}</td>
              <td className="px-4 py-3 text-muted">{e.action?.replaceAll("_", " ") || "—"}</td>
              <td className="px-4 py-3">{e.outcome || e.policy_result || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}