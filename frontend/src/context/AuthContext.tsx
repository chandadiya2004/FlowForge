"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { api, clearTokens, getAccessToken, setTokens } from "@/lib/api";
import { User } from "@/lib/types";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchCurrentUser = async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const userData = await api.get<User>("/auth/me");
      setUser(userData);
    } catch (err) {
      console.warn("Failed to fetch current user session:", err);
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;
    const initAuth = async () => {
      const token = getAccessToken();
      if (!token) {
        if (mounted) {
          setUser(null);
          setLoading(false);
        }
        return;
      }
      try {
        const userData = await api.get<User>("/auth/me");
        if (mounted) setUser(userData);
      } catch {
        clearTokens();
        if (mounted) setUser(null);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    initAuth();
    return () => {
      mounted = false;
    };
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.post<{ access_token: string; refresh_token: string }>("/auth/login", {
      email,
      password,
    });
    setTokens(res.access_token, res.refresh_token);
    const userData = await api.get<User>("/auth/me");
    setUser(userData);
  };

  const register = async (email: string, password: string) => {
    await api.post("/auth/register", { email, password });
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser: fetchCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
