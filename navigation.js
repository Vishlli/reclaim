import {
  LayoutDashboard,
  ListChecks,
  ClipboardCheck,
  Receipt,
  ShieldCheck,
  ScrollText,
} from "lucide-react";

// Single source of truth for sidebar nav + page titles, so the topbar
// title always matches whichever route is active.
export const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/recovery-cases", label: "Recovery Cases", icon: ListChecks },
  { to: "/review-queue", label: "Review Queue", icon: ClipboardCheck },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/policies", label: "Policies", icon: ShieldCheck },
  { to: "/audit", label: "Audit Trail", icon: ScrollText },
];
