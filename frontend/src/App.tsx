/**
 * Componente raíz de la aplicación.
 *
 * Configura React Router con AuthProvider, rutas públicas y rutas protegidas.
 * Las rutas dentro de ProtectedRoute requieren autenticación.
 */

import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import LoginPage from "./pages/LoginPage";
import CollectionsPage from "./pages/CollectionsPage";
import CollectionDetailPage from "./pages/CollectionDetailPage";
import EntityDetailPage from "./pages/EntityDetailPage";
import GeneratePage from "./pages/GeneratePage";
import PublicFeedPage from "./pages/PublicFeedPage";
import PublicProfilePage from "./pages/PublicProfilePage";
import ProfilePage from "./pages/ProfilePage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/users/:username" element={<PublicProfilePage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<PublicFeedPage />} />
              <Route path="/feed" element={<PublicFeedPage />} />
              <Route path="/collections" element={<CollectionsPage />} />
              <Route
                path="/collections/:collectionId"
                element={<CollectionDetailPage />}
              />
              <Route
                path="/collections/:collectionId/entities/:entityId"
                element={<EntityDetailPage />}
              />
              <Route
                path="/collections/:collectionId/generate"
                element={<GeneratePage />}
              />
              <Route path="/profile" element={<ProfilePage />} />
              <Route element={<AdminRoute />}>
                <Route path="/admin" element={<AdminPage />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
