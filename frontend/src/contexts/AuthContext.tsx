/**
 * Contexto de autenticación para la aplicación.
 *
 * Gestiona el estado del usuario autenticado, decodifica el JWT,
 * y programa auto-logout cuando el token expira.
 */

import {
  createContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { logoutApi } from "../api/auth";
import { getMyProfile } from "../api/users";

/** Datos del usuario obtenidos del backend. */
interface AuthUser {
  id: string;
  username: string;
  is_admin: boolean;
}

/** Valor expuesto por el contexto de autenticación. */
interface AuthContextValue {
  user: AuthUser | null;
  login: () => void;
  logout: () => void;
}

/* eslint-disable react-refresh/only-export-components */
export const AuthContext = createContext<AuthContextValue | null>(null);
/* eslint-enable react-refresh/only-export-components */

/**
 * Provider del contexto de autenticación.
 *
 * El token JWT se transporta via cookie HttpOnly (H-13).
 * El frontend nunca accede al token; solo consulta al backend
 * para verificar si hay sesión activa.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);

  const logout = useCallback(() => {
    void logoutApi().catch(() => {});
    setUser(null);
  }, []);

  // Verificar sesión activa al montar (lee cookie HttpOnly automaticamente)
  useEffect(() => {
    getMyProfile()
      .then((profile) => {
        setUser({
          id: profile.id,
          username: profile.username,
          is_admin: profile.is_admin ?? false,
        });
      })
      .catch(() => {
        // 401 = no hay sesión activa; mantener user en null
        setUser(null);
      });
  }, []);

  function login() {
    // El backend ya seteo las cookies en la respuesta de login.
    // Solo necesitamos obtener los datos del usuario.
    getMyProfile()
      .then((profile) => {
        setUser({
          id: profile.id,
          username: profile.username,
          is_admin: profile.is_admin ?? false,
        });
      })
      .catch(() => {
        setUser(null);
      });
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
