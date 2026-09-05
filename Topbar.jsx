import { useLocation } from "react-router-dom";
import { Search, Bell } from "lucide-react";
import { NAV_ITEMS } from "../utils/navigation";

function currentTitle(pathname) {
  // Longest matching "to" wins, so /recovery-cases/TXN-1 still resolves
  // to "Recovery Cases" rather than falling through to nothing.
  const match = [...NAV_ITEMS]
    .filter((item) => pathname === item.to || pathname.startsWith(item.to + "/"))
    .sort((a, b) => b.to.length - a.to.length)[0];
  return match?.label ?? "RECLAIM";
}

export default function Topbar() {
  const { pathname } = useLocation();

  return (
    <header className="min-h-[68px] border-b border-line bg-white/90 backdrop-blur-md flex items-center justify-between px-7.5 sticky top-0 z-10">
      <h1 className="text-sm font-semibold">{currentTitle(pathname)}</h1>

      <div className="flex items-center gap-3.5">
        <div className="w-[230px] relative">
          <Search
            size={15}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted"
          />
          <input
            type="text"
            placeholder="Search"
            className="w-full border border-line bg-white rounded-lg pl-8 pr-3 py-2 text-sm placeholder:text-muted"
          />
        </div>

        <button
          aria-label="Notifications"
          className="w-9 h-9 flex items-center justify-center rounded-lg border border-line text-muted hover:text-ink hover:border-accent transition-colors"
        >
          <Bell size={16} />
        </button>

        <span className="text-[11px] font-medium tracking-wide text-accent bg-accent-soft border border-accent/20 rounded-full px-2.5 py-1">
          SIMULATED
        </span>

        <div className="w-8 h-8 rounded-full bg-accent-soft border border-accent/20 flex items-center justify-center text-accent text-xs font-semibold">
          M
        </div>
      </div>
    </header>
  );
}
