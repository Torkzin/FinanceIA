"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, TokenResponse, User } from "@/lib/api";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const accept = useCallback((payload: TokenResponse) => {
    setToken(payload.access_token);
    setUser(payload.user);
  }, []);

  useEffect(() => {
    apiFetch<TokenResponse>("/api/v1/auth/refresh", null, { method: "POST" })
      .then(accept)
      .catch(() => undefined)
      .finally(() => setReady(true));
  }, [accept]);

  const login = useCallback(async (email: string, password: string) => {
    accept(await apiFetch<TokenResponse>("/api/v1/auth/login", null, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }));
  }, [accept]);

  const logout = useCallback(async () => {
    try {
      await apiFetch("/api/v1/auth/logout", null, { method: "POST" });
    } finally {
      setToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(() => ({ token, user, ready, login, logout }), [token, user, ready, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
