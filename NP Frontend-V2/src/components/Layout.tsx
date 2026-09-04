import { Link, useRouterState } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import {
  LayoutDashboard,
  PlusCircle,
  Store,
  TrendingUp,
  Wallet,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/submit", label: "Submit Price", icon: PlusCircle },
  { to: "/markets", label: "Market Explorer", icon: Store },
  { to: "/trends", label: "Trends", icon: TrendingUp },
  { to: "/budget", label: "Budget Planner", icon: Wallet },
];

export default function Layout({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="min-h-screen flex bg-bg text-text">
      {/* desktop sidebar */}
      <aside
        className={`hidden md:flex flex-col border-r border-border shrink-0 transition-all duration-200 ${
          collapsed ? "w-[76px]" : "w-60"
        }`}
      >
        <div className="h-16 flex items-center px-4 border-b border-border">
          {!collapsed && (
            <span className="text-xl font-extrabold tracking-tight text-amber">
              NaijaPrice
            </span>
          )}
          {collapsed && <span className="text-xl font-extrabold text-amber">N</span>}
        </div>
        <nav className="flex-1 py-4 px-3 space-y-1">
          {NAV.map((item) => {
            const active = pathname === item.to;
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  active
                    ? "bg-amber/10 text-amber"
                    : "text-stable hover:text-text hover:bg-surface"
                }`}
              >
                <Icon size={18} strokeWidth={2} />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="m-3 flex items-center justify-center gap-2 py-2 rounded-xl text-stable hover:text-text hover:bg-surface text-sm"
        >
          {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
        </button>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 pb-24 md:pb-0">{children}</main>

        <footer className="hidden md:block border-t border-border px-6 py-4 text-xs text-text-secondary">
          Data sourced from NBS Nigeria · © NaijaPrice 2026 ·{" "}
          <Link to="/model-performance" className="text-amber hover:underline">
            How accurate are these forecasts?
          </Link>
        </footer>
      </div>

      {/* mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-surface border-t border-border flex justify-around py-2 z-20">
        {NAV.map((item) => {
          const active = pathname === item.to;
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex flex-col items-center gap-1 px-3 py-1 text-[11px] font-medium ${
                active ? "text-amber" : "text-stable"
              }`}
            >
              <Icon size={20} strokeWidth={2} />
              {item.label.split(" ")[0]}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
