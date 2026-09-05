import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getTransactions } from "../services/api";
import { formatCurrency } from "../utils/format";
import StatusBadge from "../components/StatusBadge";

export default function Transactions() {
  const [txns, setTxns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    setError(false);
    getTransactions().then(setTxns).catch(() => setError(true)).finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) return <div className="text-muted text-sm">Loading transactions…</div>;
  if (error)
    return (
      <div className="text-sm">
        <p className="text-danger mb-3">Unable to load transactions.</p>
        <button onClick={load} className="border border-line rounded-lg px-3 py-1.5 hover:border-accent">Retry</button>
      </div>
    );

  const filtered = txns.filter(
    (t) =>
      t.transaction_ref.toLowerCase().includes(search.toLowerCase()) ||
      t.customer_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <input
        type="text"
        placeholder="Search by transaction or customer"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="border border-line rounded-lg px-3 py-2 text-sm mb-4 w-80"
      />
      <div className="bg-panel border border-line rounded-xl overflow-hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-canvas text-muted text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-3">Transaction</th>
              <th className="text-left px-4 py-3">Customer</th>
              <th className="text-left px-4 py-3">Amount</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Attempts</th>
              <th className="text-left px-4 py-3">Recovery Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr
                key={t.id}
                onClick={() => navigate(`/recovery-cases/${t.transaction_ref}`)}
                className="border-t border-line hover:bg-canvas cursor-pointer"
              >
                <td className="px-4 py-3 font-medium">{t.transaction_ref}</td>
                <td className="px-4 py-3">{t.customer_id}</td>
                <td className="px-4 py-3">{formatCurrency(t.amount)}</td>
                <td className="px-4 py-3 text-muted">{t.status}</td>
                <td className="px-4 py-3">{t.attempt_count}</td>
                <td className="px-4 py-3"><StatusBadge status={t.recovery_status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}