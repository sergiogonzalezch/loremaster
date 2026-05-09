/**
 * Hook para acceder al contexto de autenticación.
 *
 * Debe usarse dentro de un AuthProvider.
 *
 * @returns El contexto de autenticación (usuario, login, logout, etc.)
 * @throws Error si se usa fuera de AuthProvider
 */
import { useContext } from "react";
import { AuthContext } from "../contexts/AuthContext";

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
