import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./application/hooks/useAuth";
import AppLayout from "./presentation/layouts/AppLayout";
import PosPage from "./presentation/pages/PosPage";
import ProductsPage from "./presentation/pages/ProductsPage";
import HistoryPage from "./presentation/pages/HistoryPage";
import SettingsPage from "./presentation/pages/SettingsPage";
import LoginPage from "./presentation/pages/LoginPage";
import PaymentPage from "./presentation/pages/PaymentPage";
import ConfirmationPage from "./presentation/pages/ConfirmationPage";
import DashboardPage from "./presentation/pages/DashboardPage";
import AdminLayout from "./presentation/layouts/AdminLayout";
import AdminLoginPage from "./presentation/pages/admin/AdminLoginPage";
import AdminReportsPage from "./presentation/pages/admin/AdminReportsPage";
import AdminCatalogPage from "./presentation/pages/admin/AdminCatalogPage";
import AdminTerminalsPage from "./presentation/pages/admin/AdminTerminalsPage";
import AdminMembersPage from "./presentation/pages/admin/AdminMembersPage";
import AdminSettingsPage from "./presentation/pages/admin/AdminSettingsPage";

export default function App() {
  const { authenticated, pinSet, loading } = useAuth();

  // El área /admin (multi-tenant, JWT propio) vive fuera del gate de PIN del POS v1.
  if (window.location.pathname.startsWith("/admin")) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminReportsPage />} />
            <Route path="catalogo" element={<AdminCatalogPage />} />
            <Route path="terminales" element={<AdminTerminalsPage />} />
            <Route path="miembros" element={<AdminMembersPage />} />
            <Route path="ajustes" element={<AdminSettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </BrowserRouter>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg-primary">
        <p className="text-text-secondary">Cargando...</p>
      </div>
    );
  }

  // If PIN is set but not authenticated, show login
  if (pinSet && !authenticated) {
    return (
      <BrowserRouter>
        <LoginPage onAuthenticated={() => window.location.replace("/pos")} />
      </BrowserRouter>
    );
  }

  // If no PIN set, show setup then continue
  if (!pinSet && !authenticated) {
    return (
      <BrowserRouter>
        <LoginPage onAuthenticated={() => window.location.replace("/pos")} />
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/pos" element={<PosPage />} />
          <Route path="/pos/pay" element={<PaymentPage />} />
          <Route path="/pos/confirmed" element={<ConfirmationPage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/pos" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
