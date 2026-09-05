export function formatCurrency(n) {
  return "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function formatDateTime(s) {
  return s ? new Date(s).toLocaleString() : "—";
}

export function statusClasses(status) {
  switch (status) {
    case "RECOVERED":
      return "bg-success-soft text-success";
    case "STOPPED":
      return "bg-danger-soft text-danger";
    case "MANUAL_REVIEW":
      return "bg-warning-soft text-warning";
    case "ACTION_TAKEN":
      return "bg-accent-soft text-accent";
    default:
      return "bg-line text-muted";
  }
}