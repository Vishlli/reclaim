import { useEffect, useState } from "react";
import { getReviews, approveReview, rejectReview } from "../services/api";
import { formatDateTime } from "../utils/format";

export default function ReviewQueue() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busyId, setBusyId] = useState(null);

  const load = () => {
    setLoading(true);
    setError(false);
    getReviews().then(setReviews).catch(() => setError(true)).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const act = (id, fn) => {
    setBusyId(id);
    fn(id).then(load).finally(() => setBusyId(null));
  };

  if (loading) return <div className="text-muted text-sm">Loading review queue…</div>;
  if (error)
    return (
      <div className="text-sm">
        <p className="text-danger mb-3">Unable to load review queue.</p>
        <button onClick={load} className="border border-line rounded-lg px-3 py-1.5 hover:border-accent">Retry</button>
      </div>
    );

  const pending = reviews.filter((r) => r.status === "AWAITING_MERCHANT_APPROVAL");
  if (!pending.length) return <div className="text-muted text-sm">No cases awaiting review.</div>;

  return (
    <div className="space-y-3">
      {pending.map((r) => (
        <div key={r.id} className="bg-panel border border-line rounded-xl p-5 flex items-center justify-between">
          <div>
            <div className="font-medium">Transaction #{r.transaction_id}</div>
            <div className="text-sm text-muted mt-1">{r.reason}</div>
            {r.recommendation && (
              <div className="text-sm mt-1">Recommended: {r.recommendation.replaceAll("_", " ")}</div>
            )}
          </div>
          <div className="flex gap-2">
            <button
              disabled={busyId === r.id}
              onClick={() => act(r.id, approveReview)}
              className="bg-accent text-white rounded-lg px-3 py-1.5 text-sm disabled:opacity-50"
            >
              Approve
            </button>
            <button
              disabled={busyId === r.id}
              onClick={() => act(r.id, rejectReview)}
              className="border border-line rounded-lg px-3 py-1.5 text-sm disabled:opacity-50"
            >
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}