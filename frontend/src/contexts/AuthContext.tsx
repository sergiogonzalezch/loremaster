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
  useRef,
  type ReactNode,
} from "react";
import { logoutApi } from "../api/auth";
import { getMyProfile, getMyAvatar } from "../api/users";

/** Datos del usuario obtenidos del backend. */
interface AuthUser {
  id: string;
  username: string;
  is_admin: boolean;
}

/** Valor expuesto por el contexto de autenticación. */
interface AuthContextValue {
  user: AuthUser | null;
  /** true mientras se verifica la sesión inicial (evita redirect prematuro en refresh) */
  loading: boolean;
  login: () => Promise<void>;
  logout: () => void;
  avatarUrl: string | null;
  setAvatarUrl: (url: string | null) => void;
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
  const [loading, setLoading] = useState(true);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const logoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const logout = useCallback(() => {
    if (logoutTimerRef.current) {
      clearTimeout(logoutTimerRef.current);
      logoutTimerRef.current = null;
    }
    void logoutApi().catch(() => {});
    setUser(null);
    setAvatarUrl(null);
  }, []);

  function scheduleLogout(expiresAt: string | null | undefined) {
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
    if (!expiresAt) return;
    const ms = new Date(expiresAt).getTime() - Date.now();
    if (ms <= 0) return;
    logoutTimerRef.current = setTimeout(logout, ms);
  }

  // Verifica la sesión activa al montar (lee la cookie HttpOnly automáticamente).
  // loading=true hasta que finalice para que ProtectedRoute no redirija antes de tiempo.
  useEffect(() => {
    getMyProfile()
      .then((profile) => {
        setUser({
          id: profile.id,
          username: profile.username,
          is_admin: profile.is_admin ?? false,
        });
        scheduleLogout(profile.expires_at);
        return getMyAvatar()
          .then((r) => setAvatarUrl(r.avatar_url ?? null))
          .catch(() => {});
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
    return () => {
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
    };
  }, []);

  function login(): Promise<void> {
    return getMyProfile()
      .then((profile) => {
        setUser({
          id: profile.id,
          username: profile.username,
          is_admin: profile.is_admin ?? false,
        });
        scheduleLogout(profile.expires_at);
      })
      .catch(() => {
        setUser(null);
      });
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, avatarUrl, setAvatarUrl }}
    >
      {children}
    </AuthContext.Provider>
  );
}
