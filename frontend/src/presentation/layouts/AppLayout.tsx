import { Outlet, NavLink } from "react-router-dom";
import { ShoppingCart, Package, BarChart3, Settings, LogOut } from "lucide-react";
import { clearSessionAndReload } from "../../application/hooks/useAuth";

const navItems = [
  { to: "/pos", label: "POS", icon: ShoppingCart },
  { to: "/products", label: "Productos", icon: Package },
  { to: "/history", label: "Historial", icon: BarChart3 },
  { to: "/settings", label: "Config", icon: Settings },
];

export default function AppLayout() {
  return (
    <div className="flex min-h-dvh flex-col bg-bg-primary">
      <header className="flex items-center justify-between border-b border-border-default bg-bg-surface px-4 py-2.5">
        <h1 className="text-sm font-bold tracking-wide">
          Lightning <span className="text-accent">POS</span>
        </h1>
        <button
          onClick={clearSessionAndReload}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-text-secondary transition-colors hover:bg-bg-surface-hover hover:text-error"
          aria-label="Cerrar sesion"
        >
          <LogOut size={14} />
          <span className="hidden sm:inline">Salir</span>
        </button>
      </header>

      <main className="flex-1 p-4 md:p-6">
        <Outlet />
      </main>

      <nav className="border-t border-border-default bg-bg-surface">
        <div className="flex justify-around">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-1 flex-col items-center gap-1 py-3 text-xs font-medium transition-colors ${
                  isActive
                    ? "text-accent"
                    : "text-text-secondary hover:text-text-primary"
                }`
              }
            >
              <Icon size={20} />
              <span>{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
