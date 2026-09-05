import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDashboard, getTransactions } from "../services/api";
import { formatCurrency } from "../utils/format";
import StatusBadge from "../components/StatusBadge";

function MetricCard({ label, value, caption }) {
  return (
    <div className="bg-panel border border-line rounded-xl p-5">
      <div className="text-xs text-muted mb-2">{label}</div>
      <div className="text-2xl font-semibold text-ink">{value}</div>
      {caption && <div className="text-xs text-muted mt-2">{caption}</div>}
    </div>
  );
}

function classifyRisk(t) {
  if (t.recovery_status === "RECOVERED") return "Already Recovered";
  if (t.attempt_count >= 3) return "Too Many Attempts";
  if (t.amount > 25000) return "High Value";
  if (t.status === "ABANDONED") return "Checkout Abandonment";
  if (t.attempt_count === 2) return "Repeated Failure";
  return "Transient Failure";
}

export default function Overview() {
  const [metrics, setMetrics] = useState(null);
  const [txns, setTxns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    setError(false);
    Promise.all([getDashboard(), getTransactions()])
      .then(([m, t]) => {
        setMetrics(m);
        setTxns(t);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) return <div className="text-muted text-sm">Loading dashboard…</div>;
  if (error)
    return (
      <div className="text-sm">
        <p className="text-danger mb-3">Unable to load dashboard.</p>
        <button onClick={load} className="border border-line rounded-lg px-3 py-1.5 hover:border-accent">Retry</button>
      </div>
    );

  const atRisk = txns.filter((t) => t.status === "FAILED" || t.status === "ABANDONED");
  const riskCounts = {};
  atRisk.forEach((t) => {
    const cat = classifyRisk(t);
    riskCounts[cat] = (riskCounts[cat] || 0) + 1;
  });

  const recentCases = atRisk.slice(0, 6);

  return (
    <div className="space-y-6">
      {/* Hero metrics */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Revenue at Risk" value={formatCurrency(metrics.revenue_at_risk)} caption={`From ${metrics.transactions_analyzed} synthetic transactions`} />
        <MetricCard label="Recovered Revenue" value={formatCurrency(metrics.recovered_revenue)} />
        <MetricCard label="Recovery Actions" value={metrics.actions_executed} />
        <MetricCard label="Successful Recoveries" value={metrics.successful_recoveries} />
      </div>

      {/* Pipeline funnel */}
      <div className="bg-panel border border-line rounded-xl p-5">
        <div className="text-xs text-muted uppercase mb-3">Recovery Pipeline</div>
        <div className="flex items-center gap-3 text-sm flex-wrap">
          <span className="bg-canvas border border-line rounded-full px-3 py-1.5">{metrics.transactions_analyzed} At Risk</span>
          <span className="text-muted">→</span>
          <span className="bg-canvas border border-line rounded-full px-3 py-1.5">{metrics.eligible_cases} Eligible</span>
          <span className="text-muted">→</span>
          <span className="bg-canvas border border-line rounded-full px-3 py-1.5">{metrics.actions_executed} Actions Executed</span>
          <span className="text-muted">→</span>
          <span className="bg-accent-soft border border-accent/20 text-accent rounded-full px-3 py-1.5 font-medium">{metrics.successful_recoveries} Recovered</span>
        </div>
      </div>

      {/* Risk breakdown */}
      <div className="bg-panel border border-line rounded-xl p-5">
        <div className="text-xs text-muted uppercase mb-3">Risk Breakdown</div>
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(riskCounts).map(([cat, count]) => (
            <div key={cat} className="bg-canvas border border-line rounded-lg p-3">
              <div className="text-sm">{cat}</div>
              <div className="text-lg font-semibold">{count}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent cases */}
      <div className="bg-panel border border-line rounded-xl overflow-hidden">
        <div className="text-xs text-muted uppercase px-5 pt-4 pb-2">Recent Recovery Cases</div>
        <table className="w-full text-sm">
          <thead className="bg-canvas text-muted text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Transaction</th>
              <th className="text-left px-4 py-2">Customer</th>
              <th className="text-left px-4 py-2">Amount</th>
              <th className="text-left px-4 py-2">Failure</th>
              <th className="text-left px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {recentCases.map((t) => (
              <tr key={t.id} onClick={() => navigate(`/recovery-cases/${t.transaction_ref}`)} className="border-t border-line hover:bg-canvas cursor-pointer">
                <td className="px-4 py-2 font-medium">{t.transaction_ref}</td>
                <td className="px-4 py-2">{t.customer_id}</td>
                <td className="px-4 py-2">{formatCurrency(t.amount)}</td>
                <td className="px-4 py-2 text-muted">{t.failure_code || "abandoned"}</td>
                <td className="px-4 py-2"><StatusBadge status={t.recovery_status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}