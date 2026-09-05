import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getRecoveryCase, analyzeTransaction, executeTransaction } from "../services/api";
import { formatCurrency, formatDateTime } from "../utils/format";
import StatusBadge from "../components/StatusBadge";

export default function RecoveryCaseDetail() {
  const { transactionId } = useParams();
  const [txn, setTxn] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState(null);

  const load = () => {
    setLoading(true);
    setError(false);
    setExecResult(null);
    Promise.all([getRecoveryCase(transactionId), analyzeTransaction(transactionId)])
      .then(([t, a]) => {
        setTxn(t);
        setAnalysis(a);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(load, [transactionId]);

  const runExecute = () => {
    setExecuting(true);
    executeTransaction(transactionId)
      .then((result) => {
        setExecResult(result);
        load();
      })
      .catch(() => setExecResult({ status: "FAILED", message: "Request failed unexpectedly." }))
      .finally(() => setExecuting(false));
  };

  if (loading) return <div className="text-muted text-sm">Loading case…</div>;
  if (error)
    return (
      <div className="text-sm">
        <p className="text-danger mb-3">Unable to load this case.</p>
        <button onClick={load} className="border border-line rounded-lg px-3 py-1.5 hover:border-accent">Retry</button>
      </div>
    );

  const decision = analysis.policy_decision.decision;
  const rec = analysis.recommendation;

  return (
    <div className="space-y-5">
      {/* Transaction summary */}
      <div className="bg-panel border border-line rounded-xl p-5 flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">{txn.transaction_ref}</div>
          <div className="text-sm text-muted mt-1">
            {txn.customer_id} · {txn.gateway} · Created {formatDateTime(txn.created_at)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xl font-semibold">{formatCurrency(txn.amount)}</div>
          <StatusBadge status={txn.recovery_status} />
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-panel border border-line rounded-xl p-5">
        <div className="text-xs text-muted uppercase mb-3">Case Timeline</div>
        <div className="flex flex-wrap gap-2 text-sm">
          {["Detected", "Diagnosed", "AI Recommendation", "Policy Gate", "Action Execution"].map((step, i) => (
            <span key={step} className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-full bg-canvas border border-line">{step}</span>
              {i < 4 && <span className="text-muted">→</span>}
            </span>
          ))}
        </div>
      </div>

      {/* AI Recommendation panel */}
      <div className="bg-panel border border-line rounded-xl p-5">
        <div className="text-xs text-accent uppercase font-semibold mb-2">AI Recovery Recommendation</div>
        <div className="text-lg font-medium mb-1">{rec.recommended_action.replaceAll("_", " ")}</div>
        <p className="text-sm text-muted mb-3">{rec.ai_explanation}</p>
        <div className="flex flex-wrap gap-2 mb-3">
          {rec.evidence.map((e) => (
            <span key={e} className="text-xs bg-canvas border border-line rounded-full px-2.5 py-1">{e}</span>
          ))}
        </div>
        <div className="text-sm">
          Recovery Score: <span className="font-semibold">{analysis.recovery_score.score}/100</span>{" "}
          <span className="text-muted">({analysis.recovery_score.label})</span>
        </div>
        <p className="text-xs text-muted mt-2">This recommendation is subject to merchant policy.</p>
      </div>

      {/* Policy Gate panel */}
      <div className="bg-panel border border-line rounded-xl p-5">
        <div className="text-xs text-muted uppercase font-semibold mb-2">Policy Gate</div>
        <div
          className={`inline-block rounded-full px-3 py-1 text-sm font-semibold mb-3 ${
            decision === "ALLOWED" ? "bg-success-soft text-success" :
            decision === "MANUAL_REVIEW" ? "bg-warning-soft text-warning" :
            "bg-danger-soft text-danger"
          }`}
        >
          {decision}
        </div>
        <p className="text-sm mb-2">{analysis.policy_decision.reason}</p>
        {analysis.policy_decision.alternative_action && (
          <p className="text-sm">
            <strong>Allowed alternative:</strong> {analysis.policy_decision.alternative_action.replaceAll("_", " ")}
          </p>
        )}
      </div>

      {/* Action panel */}
      <div className="bg-panel border border-line rounded-xl p-5">
        <div className="text-xs text-muted uppercase font-semibold mb-3">Action</div>
        {decision === "MANUAL_REVIEW" ? (
          <p className="text-sm text-warning">Awaiting Merchant Approval — see Review Queue.</p>
        ) : decision === "BLOCKED" && !analysis.policy_decision.alternative_action ? (
          <p className="text-sm text-danger">No allowed action available.</p>
        ) : (
          <button
            onClick={runExecute}
            disabled={executing}
            className="bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {executing ? "Executing…" : "Execute Recovery"}
          </button>
        )}

        {execResult && (
          <div className="mt-4 text-sm border-t border-line pt-4">
            <div className="font-semibold">
              {execResult.status === "EXECUTED" && "✓ Action executed"}
              {execResult.status === "FAILED" && "Action failed safely"}
              {execResult.status === "DUPLICATE_PREVENTED" && "Duplicate prevented"}
              {execResult.status === "AWAITING_APPROVAL" && "Awaiting merchant approval"}
            </div>
            <p className="text-muted mt-1">{execResult.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}