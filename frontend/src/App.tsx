/**
 * Componente raíz de la aplicación.
 *
 * Configura React Router con AuthProvider, rutas públicas y rutas protegidas.
 * Cuando VITE_CLERK_PUBLISHABLE_KEY está definida, envuelve la app con
 * ClerkProvider y monta ClerkBridge para sincronizar la sesión con el backend.
 */

import { useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { ClerkProvider, useAuth as useClerkAuth } from "@clerk/clerk-react";
import { AuthProvider } from "./contexts/AuthContext";
import { useAuth } from "./hooks/useAuth";
import { syncClerkSession } from "./api/clerkSync";
import { clerkKey } from "./utils/clerkConfig";
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

/**
 * Detecta el login con Clerk y sincroniza la sesión con el backend.
 *
 * Solo se renderiza dentro de ClerkProvider (cuando clerkKey está definida).
 * Tras la sincronización actualiza AuthContext y navega a "/" para evitar
 * que ProtectedRoute redirija al login antes de que el usuario esté listo.
 */
function ClerkBridge() {
  const { getToken, isSignedIn } = useClerkAuth();
  const { login } = useAuth();
  const navigate = useNavigate();
  const syncedRef = useRef(false);

  useEffect(() => {
    if (!isSignedIn) {
      syncedRef.current = false;
      return;
    }
    if (syncedRef.current) return;
    syncedRef.current = true;

    getToken()
      .then((token) =>
        token ? syncClerkSession(token) : Promise.reject(new Error("no token")),
      )
      .then(() => login())
      .then(() => {
        if (window.location.pathname === "/login") {
          navigate("/", { replace: true });
        }
      })
      .catch(() => {
        syncedRef.current = false;
      });
  }, [isSignedIn, getToken, login, navigate]);

  return null;
}

/** Redirige al login via React Router cuando apiClient emite auth:unauthorized. */
function UnauthorizedHandler() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  useEffect(() => {
    function handleUnauthorized() {
      logout();
      navigate("/login", { replace: true });
    }
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () =>
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [logout, navigate]);

  return null;
}

/** Árbol de rutas compartido por los dos modos de auth (local y Clerk). */
function AppRoutes() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <UnauthorizedHandler />
        {clerkKey && <ClerkBridge />}
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

export default function App() {
  if (clerkKey) {
    return (
      <ClerkProvider publishableKey={clerkKey}>
        <AppRoutes />
      </ClerkProvider>
    );
  }
  return <AppRoutes />;
}
