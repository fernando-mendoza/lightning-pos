import { Outlet, NavLink } from "react-router-dom";
import {
  ShoppingCart,
  Package,
  BarChart3,
  Settings,
  LogOut,
  LayoutDashboard,
} from "lucide-react";
import { clearSessionAndReload } from "../../application/hooks/useAuth";

const navItems = [
  { to: "/dashboard", label: "Inicio", icon: LayoutDashboard },
  { to: "/pos", label: "POS", icon: ShoppingCart },
  { to: "/products", label: "Productos", icon: Package },
  { to: "/history", label: "Historial", icon: BarChart3 },
  { to: "/settings", label: "Config", icon: Settings },
];

export default function AppLayout() {
  return (
    // App shell de altura fija: header y nav siempre visibles; el scroll vive
    // DENTRO de <main>. Ninguna pagina puede empujar el nav fuera del viewport.
    <div className="flex h-dvh flex-col bg-bg-primary">
      <header className="border-b border-border-default bg-bg-surface px-4 py-2.5">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between">
          <div className="flex items-baseline gap-2">
            <h1 className="text-sm font-bold tracking-wide">
              Lightning <span className="text-accent">POS</span>
            </h1>
            <span className="text-[10px] text-text-secondary/70">
              Powered by AgentykCo
            </span>
          </div>
          <button
            onClick={clearSessionAndReload}
            className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-text-secondary transition-colors hover:bg-bg-surface-hover hover:text-error"
            aria-label="Cerrar sesion"
          >
            <LogOut size={14} />
            <span className="hidden sm:inline">Salir</span>
          </button>
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mx-auto h-full w-full max-w-5xl">
          <Outlet />
        </div>
      </main>

      <nav className="relative border-t border-border-default bg-bg-surface">
        {/* Branding en el hueco derecho del nav; oculto en movil donde los 5
            items ocupan todo el ancho */}
        <span className="absolute inset-y-0 right-4 hidden items-center text-[10px] text-text-secondary/70 md:flex">
          Powered by AgentykCo
        </span>
        <div className="mx-auto flex w-full max-w-5xl justify-around">
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
