import { createContext, useState, useContext, type ReactNode } from "react";
import { getToken } from "../utils/token";

interface AuthUser {
  id: string;
  username: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = getToken();
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return { id: payload.sub, username: payload.username };
    } catch {
      return null;
    }
  });

  function logout() {
    import("../utils/token").then(({ removeToken }) => {
      removeToken();
      setUser(null);
    });
  }

  return (
    <AuthContext.Provider value={{ user, logout }}>
      {children}
    </AuthContext.Provider>
  );
}