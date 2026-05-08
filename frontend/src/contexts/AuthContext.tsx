import { createContext, useState, type ReactNode } from "react";
import { getToken, setToken, removeToken } from "../utils/token";

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

export const AuthContext = createContext<AuthContextValue | null>(null);

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getToken();
    return token ? decodeUser(token) : null;
  });

  function login(token: string) {
    setToken(token);
    setUser(decodeUser(token));
  }

  function logout() {
    removeToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
