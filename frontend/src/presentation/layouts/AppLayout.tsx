import { Outlet, NavLink } from "react-router-dom";
import { ShoppingCart, Package, BarChart3, Settings } from "lucide-react";

const navItems = [
  { to: "/pos", label: "POS", icon: ShoppingCart },
  { to: "/products", label: "Productos", icon: Package },
  { to: "/history", label: "Historial", icon: BarChart3 },
  { to: "/settings", label: "Config", icon: Settings },
];

export default function AppLayout() {
  return (
    <div className="flex min-h-dvh flex-col bg-bg-primary">
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
