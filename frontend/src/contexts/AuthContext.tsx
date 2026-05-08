import {
  createContext,
  useState,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { getToken, setToken, removeToken } from "../utils/token";
import { logoutApi } from "../api/auth";

interface AuthUser {
  id: string;
  username: string;
  is_admin: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  login: (token: string) => void;
  logout: () => void;
}

/* eslint-disable react-refresh/only-export-components */
export const AuthContext = createContext<AuthContextValue | null>(null);
/* eslint-enable react-refresh/only-export-components */

function decodeUser(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return {
      id: payload.sub,
      username: payload.username,
      is_admin: payload.is_admin ?? false,
    };
  } catch {
    return null;
  }
}

function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

function isTokenExpired(token: string): boolean {
  const expiry = getTokenExpiry(token);
  return expiry === null || expiry <= Date.now();
}

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

  function logout() {
    void logoutApi().catch(() => {});
    removeToken();
    setUser(null);
  }

  logoutRef.current = logout;

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

  function login(token: string) {
    setToken(token);
    setUser(decodeUser(token));
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
