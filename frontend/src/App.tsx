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

export default function App() {
  const { authenticated, pinSet, loading } = useAuth();

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
