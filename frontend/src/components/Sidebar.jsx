import { NavLink } from "react-router-dom";
import { Settings, Building2 } from "lucide-react";
import { NAV_ITEMS } from "../utils/navigation";

export default function Sidebar() {
  return (
    <aside className="w-[244px] shrink-0 bg-accent-dark text-[#dbe6e0] px-3.5 py-5 flex flex-col sticky top-0 h-screen z-20">
      <div className="flex items-center px-2 mb-8">
        <span className="bg-[#75c2a5] text-accent-dark rounded-md w-6 h-6 inline-flex items-center justify-center text-sm font-bold mr-2.5">
          R
        </span>
        <span className="text-white font-bold text-lg tracking-[0.11em]">
          RECLAIM
        </span>
      </div>

      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2.5 w-full rounded-lg px-3 py-2.5 text-sm text-left transition-colors ${
                isActive
                  ? "bg-accent-darker text-white shadow-[inset_2px_0_0_#75c2a5]"
                  : "text-[#aebdb6] hover:bg-accent-darker hover:text-white"
              }`
            }
          >
            <Icon size={17} strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto pt-3.5 border-t border-[#294137]">
        <div className="bg-[#19342c] border border-[#315246] rounded-lg p-2.5 mb-3">
          <strong className="block text-[10px] tracking-[0.1em] text-[#a9dbc5]">
            SIMULATED TEST ENVIRONMENT
          </strong>
          <span className="block text-[11px] text-[#aebdb6] mt-0.5">
            No real payments or merchant funds are involved.
          </span>
        </div>

        <button className="flex items-center gap-2.5 w-full rounded-lg px-3 py-2.5 text-sm text-left text-[#aebdb6] hover:bg-accent-darker hover:text-white transition-colors">
          <Building2 size={17} strokeWidth={1.75} />
          Merchant
        </button>
        <button className="flex items-center gap-2.5 w-full rounded-lg px-3 py-2.5 text-sm text-left text-[#aebdb6] hover:bg-accent-darker hover:text-white transition-colors">
          <Settings size={17} strokeWidth={1.75} />
          Settings
        </button>
      </div>
    </aside>
  );
}
