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
  useRef,
  useCallback,
  type ReactNode,
} from "react";
import { getToken, setToken, removeToken } from "../utils/token";
import { logoutApi } from "../api/auth";
import { getMyProfile } from "../api/users";

/** Datos del usuario extraídos del token JWT + backend. */
interface AuthUser {
  id: string;
  username: string;
  is_admin: boolean;
}

/** Valor expuesto por el contexto de autenticación. */
interface AuthContextValue {
  user: AuthUser | null;
  login: (token: string) => void;
  logout: () => void;
}

/* eslint-disable react-refresh/only-export-components */
export const AuthContext = createContext<AuthContextValue | null>(null);
/* eslint-enable react-refresh/only-export-components */

/** Decodifica el payload del JWT para extraer datos básicos del usuario. */
function decodeUser(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return {
      id: payload.sub,
      username: payload.username,
      is_admin: false, // Se actualiza via fetch al backend
    };
  } catch {
    return null;
  }
}

/** Extrae la fecha de expiración (en ms) de un token JWT. */
function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/** Verifica si un token JWT ya expiró. */
function isTokenExpired(token: string): boolean {
  const expiry = getTokenExpiry(token);
  return expiry === null || expiry <= Date.now();
}

/**
 * Provider del contexto de autenticación.
 *
 * Inicializa el usuario desde el token en localStorage, y programa
 * un timer para auto-logout cuando el token expire.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getToken();
    if (!token) return null;
    if (isTokenExpired(token)) {
      removeToken();
      return null;
    }
    return decodeUser(token);
  });

  // Ref so the timer callback always calls the current logout without re-scheduling
  const logoutRef = useRef<() => void>(() => {});

  const logout = useCallback(() => {
    void logoutApi().catch(() => {});
    removeToken();
    setUser(null);
  }, []);

  useEffect(() => {
    logoutRef.current = logout;
  }, [logout]);

  // Auto-logout when the current token expires
  useEffect(() => {
    if (!user) return;
    const token = getToken();
    if (!token) return;

    const expiry = getTokenExpiry(token);
    if (expiry === null) return;

    const msUntilExpiry = expiry - Date.now();
    if (msUntilExpiry <= 0) {
      removeToken();
      setUser(null);
      return;
    }

    const timer = window.setTimeout(() => {
      removeToken();
      setUser(null);
    }, msUntilExpiry);

    return () => window.clearTimeout(timer);
  }, [user]);

  // Fetch user profile from backend to get is_admin
  useEffect(() => {
    const token = getToken();
    if (!token || isTokenExpired(token)) return;

    getMyProfile()
      .then((profile) => {
        setUser((prev) =>
          prev
            ? {
                ...prev,
                is_admin: profile.is_admin ?? false,
              }
            : null
        );
      })
      .catch(() => {
        // Silenciar error — si falla, is_admin queda en false
      });
  }, []);

  function login(token: string) {
    setToken(token);
    const basicUser = decodeUser(token);
    setUser(basicUser);

    // Fetch is_admin from backend after login
    if (basicUser) {
      getMyProfile()
        .then((profile) => {
          setUser({
            ...basicUser,
            is_admin: profile.is_admin ?? false,
          });
        })
        .catch(() => {
          // Silenciar error
        });
    }
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
