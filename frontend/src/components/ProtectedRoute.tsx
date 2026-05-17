/**
 * Guard de ruta que redirige al login si el usuario no está autenticado.
 *
 * Modo local  (sin VITE_CLERK_PUBLISHABLE_KEY): usa AuthContext.
 * Modo Clerk  (con VITE_CLERK_PUBLISHABLE_KEY): usa el estado de sesión
 *   del SDK de Clerk, que es inmediato y no espera al sync con el backend.
 *   Esto evita un redirect prematuro al login durante el breve intervalo
 *   entre el login con Clerk y la finalización del sync de cookies.
 */

import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { useAuth } from "../hooks/useAuth";
import LoadingSpinner from "./LoadingSpinner";
import { clerkKey } from "../utils/clerkConfig";

/** Gate para el modo Clerk. Solo se renderiza dentro de ClerkProvider. */
function ProtectedRouteClerk() {
  const { isSignedIn, isLoaded } = useUser();
  const { user, loading } = useAuth();
  const location = useLocation();

  // Espera tanto a Clerk como al sync de cookie con el backend antes de decidir.
  if (!isLoaded || loading) return <LoadingSpinner />;
  // isSignedIn cubre sesión Clerk expirada; !user cubre sesión backend revocada post-sync.
  if (!isSignedIn || !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <Outlet />;
}

/** Gate para el modo local (auth propia con JWT + cookies). */
function ProtectedRouteLocal() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingSpinner />;
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <Outlet />;
}

export default function ProtectedRoute() {
  return clerkKey ? <ProtectedRouteClerk /> : <ProtectedRouteLocal />;
}
