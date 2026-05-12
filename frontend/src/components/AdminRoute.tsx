/**
 * Guard de ruta que redirige si el usuario no es administrador.
 *
 * Requiere autenticacion (debe usarse dentro de ProtectedRoute o despues
 * de verificar auth). Redirige a la pagina principal si el usuario no
 * tiene rol de administrador.
 */

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function AdminRoute() {
  const { user } = useAuth();
  if (!user?.is_admin) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
