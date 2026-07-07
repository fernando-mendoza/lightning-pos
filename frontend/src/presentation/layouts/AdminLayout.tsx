import { NavLink, Navigate, Outlet } from "react-router-dom";
import { BarChart3, LogOut, Package, Settings, Smartphone, Users, Zap } from "lucide-react";
import { clearAdminSession, getAdminSession } from "../../infrastructure/adminApi";

const NAV = [
  { to: "/admin", label: "Reportes", icon: BarChart3, end: true },
  { to: "/admin/catalogo", label: "Catálogo", icon: Package, end: false },
  { to: "/admin/terminales", label: "Terminales", icon: Smartphone, end: false },
  { to: "/admin/miembros", label: "Miembros", icon: Users, end: false },
  { to: "/admin/ajustes", label: "Ajustes", icon: Settings, end: false },
];

export default function AdminLayout() {
  const session = getAdminSession();
  if (!session) return <Navigate to="/admin/login" replace />;

  const logout = () => {
    clearAdminSession();
    window.location.replace("/admin/login");
  };

  return (
    <div className="flex min-h-dvh flex-col bg-bg-primary">
      <header className="flex items-center justify-between border-b border-border-default px-4 py-3">
        <div className="flex items-baseline gap-2">
          <span className="flex items-center gap-1.5 font-bold">
            <Zap className="text-accent" size={18} />
            {session.tenantName}
          </span>
          <span className="text-[10px] text-text-secondary/70">Powered by AgentykCo</span>
        </div>
        <button
          onClick={logout}
          data-testid="admin-logout"
          className="flex items-center gap-1.5 rounded-lg border border-border-default px-3 py-1.5 text-sm text-text-secondary hover:border-accent hover:text-text-primary"
        >
          <LogOut size={14} />
          Salir
        </button>
      </header>

      <nav className="border-b border-border-default px-4">
        <div className="mx-auto flex max-w-5xl gap-1 overflow-x-auto">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm ${
                  isActive
                    ? "border-accent font-medium text-text-primary"
                    : "border-transparent text-text-secondary hover:text-text-primary"
                }`
              }
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
