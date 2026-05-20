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
import { ApiAbortError } from "../api/apiClient";

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
  /**
   * Cierra la sesión.
   * Sin opciones: espera confirmación del backend; lanza si falla (caller muestra error).
   * Con `{ force: true }`: limpia estado local sin llamar al backend — para 401 o timer.
   */
  logout: (options?: { force?: boolean }) => Promise<void>;
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

  const logout = useCallback(async ({ force = false }: { force?: boolean } = {}) => {
    if (logoutTimerRef.current) {
      clearTimeout(logoutTimerRef.current);
      logoutTimerRef.current = null;
    }
    if (force) {
      setUser(null);
      setAvatarUrl(null);
      return;
    }
    await logoutApi();   // lanza si falla; el llamador decide qué mostrar
    setUser(null);
    setAvatarUrl(null);
  }, []);

  const scheduleLogout = useCallback((expiresAt: string | null | undefined) => {
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
    if (!expiresAt) return;
    const ms = new Date(expiresAt).getTime() - Date.now();
    if (ms <= 0) return;
    // force=true: la sesión ya expiró cuando dispara el timer, no necesita confirmación backend
    logoutTimerRef.current = setTimeout(() => { void logout({ force: true }); }, ms);
  }, [logout]);

  // Verifica la sesión activa al montar (lee la cookie HttpOnly automáticamente).
  // AbortController cancela la petición si el componente desmonta (Strict Mode safe).
  // loading baja a false en cuanto el perfil resuelve; el avatar carga después sin bloquear.
  useEffect(() => {
    const controller = new AbortController();

    getMyProfile({ signal: controller.signal })
      .then((profile) => {
        setUser({
          id: profile.id,
          username: profile.username,
          is_admin: profile.is_admin ?? false,
        });
        scheduleLogout(profile.expires_at);
        setLoading(false);
        return getMyAvatar({ signal: controller.signal })
          .then((r) => setAvatarUrl(r.avatar_url ?? null))
          .catch(() => {});
      })
      .catch((err) => {
        if (err instanceof ApiAbortError) return;
        setUser(null);
        setLoading(false);
      });

    return () => {
      controller.abort();
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
    };
  }, [scheduleLogout]);

  function login(): Promise<void> {
    return getMyProfile()
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
      });
    // Sin .catch(): los errores de red o credenciales propagation al llamador (LoginPage).
    // No reseteamos user aquí para no desloguear a un usuario ya autenticado por error transitorio.
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, avatarUrl, setAvatarUrl }}
    >
      {children}
    </AuthContext.Provider>
  );
}
