import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./presentation/layouts/AppLayout";
import PosPage from "./presentation/pages/PosPage";
import ProductsPage from "./presentation/pages/ProductsPage";
import HistoryPage from "./presentation/pages/HistoryPage";
import SettingsPage from "./presentation/pages/SettingsPage";
import LoginPage from "./presentation/pages/LoginPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppLayout />}>
          <Route path="/pos" element={<PosPage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/pos" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
