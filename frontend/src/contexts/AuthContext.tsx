/**
 * Contexto de autenticación para la aplicación.
 *
 * Gestiona el estado del usuario autenticado, decodifica el JWT,
 * y programa auto-logout cuando el token expira.
 */

import {
  createContext,
  useReducer,
  useEffect,
  useCallback,
  useMemo,
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

// ---------------------------------------------------------------------------
// Auth reducer — groups user, loading, avatarUrl; prevents cascading setState
// ---------------------------------------------------------------------------

type AuthState = {
  user: AuthUser | null;
  loading: boolean;
  avatarUrl: string | null;
};

type AuthAction =
  | { type: "INIT_SUCCESS"; user: AuthUser }
  | { type: "INIT_FAIL" }
  | { type: "SET_AVATAR"; url: string | null }
  | { type: "LOGOUT" };

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "INIT_SUCCESS":
      return { ...state, user: action.user, loading: false };
    case "INIT_FAIL":
      return { ...state, user: null, loading: false };
    case "SET_AVATAR":
      return { ...state, avatarUrl: action.url };
    case "LOGOUT":
      return { user: null, loading: false, avatarUrl: null };
  }
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
  const [state, dispatch] = useReducer(authReducer, {
    user: null,
    loading: true,
    avatarUrl: null,
  });
  const { user, loading, avatarUrl } = state;
  const logoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Wrapper que mantiene la firma setAvatarUrl(url) para los consumidores del contexto.
  const setAvatarUrl = useCallback((url: string | null) => {
    dispatch({ type: "SET_AVATAR", url });
  }, []);

  const logout = useCallback(
    async ({ force = false }: { force?: boolean } = {}) => {
      if (logoutTimerRef.current) {
        clearTimeout(logoutTimerRef.current);
        logoutTimerRef.current = null;
      }
      if (!force) {
        await logoutApi(); // lanza si falla; el llamador decide qué mostrar
      }
      dispatch({ type: "LOGOUT" });
    },
    [],
  );

  const scheduleLogout = useCallback(
    (expiresAt: string | null | undefined) => {
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
      if (!expiresAt) return;
      const ms = new Date(expiresAt).getTime() - Date.now();
      if (ms <= 0) return;
      // force=true: la sesión ya expiró cuando dispara el timer, no necesita confirmación backend
      logoutTimerRef.current = setTimeout(() => {
        void logout({ force: true });
      }, ms);
    },
    [logout],
  );

  // Verifica la sesión activa al montar (lee la cookie HttpOnly automáticamente).
  // AbortController cancela la petición si el componente desmonta (Strict Mode safe).
  // loading baja a false en cuanto el perfil resuelve; el avatar carga después sin bloquear.
  useEffect(() => {
    const controller = new AbortController();

    getMyProfile({ signal: controller.signal })
      .then((profile) => {
        dispatch({
          type: "INIT_SUCCESS",
          user: {
            id: profile.id,
            username: profile.username,
            is_admin: profile.is_admin ?? false,
          },
        });
        scheduleLogout(profile.expires_at);
        return getMyAvatar({ signal: controller.signal })
          .then((r) =>
            dispatch({ type: "SET_AVATAR", url: r.avatar_url ?? null }),
          )
          .catch(() => {});
      })
      .catch((err) => {
        if (err instanceof ApiAbortError) return;
        dispatch({ type: "INIT_FAIL" });
      });

    return () => {
      controller.abort();
      const timer = logoutTimerRef.current;
      if (timer) clearTimeout(timer);
    };
  }, [scheduleLogout]);

  const login = useCallback((): Promise<void> => {
    return getMyProfile().then((profile) => {
      dispatch({
        type: "INIT_SUCCESS",
        user: {
          id: profile.id,
          username: profile.username,
          is_admin: profile.is_admin ?? false,
        },
      });
      scheduleLogout(profile.expires_at);
      return getMyAvatar()
        .then((r) =>
          dispatch({ type: "SET_AVATAR", url: r.avatar_url ?? null }),
        )
        .catch(() => {});
    });
    // Sin .catch(): los errores de red o credenciales se propagan al llamador (LoginPage).
  }, [scheduleLogout]);

  const contextValue = useMemo(
    () => ({ user, loading, login, logout, avatarUrl, setAvatarUrl }),
    [user, loading, login, logout, avatarUrl, setAvatarUrl],
  );

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}
