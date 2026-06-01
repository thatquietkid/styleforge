"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";

const AuthContext = createContext(null);
const API_URL = process.env.NEXT_PUBLIC_AUTH_API_URL || "http://localhost:8000";

export function AuthProvider({ children }) {
  // Primary source of truth: in-memory state
  const [token, setTokenState] = useState(null);
  const [user, setUserState] = useState(null);
  const [hydrated, setHydrated] = useState(false);

  // On first mount, try to restore from sessionStorage (dev hot-reload / tab refresh)
  useEffect(() => {
    const storedToken = sessionStorage.getItem("access_token");
    const storedUser = sessionStorage.getItem("user");
    if (storedToken) setTokenState(storedToken);
    if (storedUser) {
      try { setUserState(JSON.parse(storedUser)); } catch (_) {}
    }
    setHydrated(true);
  }, []);

  const setToken = useCallback((newToken, newUser = null) => {
    setTokenState(newToken);
    setUserState(newToken ? newUser : null);
    if (newToken) {
      sessionStorage.setItem("access_token", newToken);
      if (newUser) sessionStorage.setItem("user", JSON.stringify(newUser));
      else sessionStorage.removeItem("user");
    } else {
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("user");
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null, null);
  }, [setToken]);

  const updateUser = useCallback((newUser) => {
    setUserState(newUser);
    if (newUser) {
      sessionStorage.setItem("user", JSON.stringify(newUser));
    } else {
      sessionStorage.removeItem("user");
    }
  }, []);

  // Centralized, auto-refreshing fetch wrapper for protected API endpoints
  const authFetch = useCallback(async (url, options = {}) => {
    let currentToken = token || sessionStorage.getItem("access_token");
    
    // Attach authorization header if token exists
    const attachToken = (tok, opts) => {
      const headers = { ...opts.headers };
      if (tok) {
        headers["Authorization"] = `Bearer ${tok}`;
      }
      return { ...opts, headers };
    };

    // Make initial request
    let response = await fetch(url, attachToken(currentToken, options));

    // If unauthorized with a "token_expired" code, silently renew access token!
    if (response.status === 401 && currentToken) {
      try {
        const clonedResponse = response.clone();
        const data = await clonedResponse.json();
        
        if (data.code === "token_expired") {
          console.log("Access token expired. Initiating silent token renewal...");
          
          const refreshRes = await fetch(`${API_URL}/api/v1/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: currentToken }),
          });

          if (refreshRes.ok) {
            const refreshData = await refreshRes.json();
            const newToken = refreshData.access_token;
            const newUser = refreshData.user;
            
            // Save the new token in state + storage
            setToken(newToken, newUser);
            console.log("Silent token renewal completed successfully!");

            // Retry the original request with the freshly minted token
            response = await fetch(url, attachToken(newToken, options));
          } else {
            console.warn("Silent token renewal failed. User session invalidated.");
            logout();
          }
        }
      } catch (err) {
        console.error("Error during automatic silent token renewal:", err);
      }
    }

    return response;
  }, [token, setToken, logout]);

  return (
    <AuthContext.Provider value={{ token, user, setToken, logout, hydrated, updateUser, authFetch }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
