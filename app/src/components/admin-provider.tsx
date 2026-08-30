import React, { useState, useEffect, useCallback } from 'react';
import { AdminAuthContext } from '@/context/admin-context';
import { apiLogin, apiLogout, apiGetMe } from '@/lib/api';

const ADMIN_AUTH_KEY = 'ai_interviewer_admin_auth';

export const AdminAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAdmin, setIsAdmin] = useState<boolean>(() => {
    const saved = localStorage.getItem(ADMIN_AUTH_KEY);
    return saved === 'true';
  });

  const [adminEmail, setAdminEmail] = useState<string | null>(() => {
    return (
      localStorage.getItem(`${ADMIN_AUTH_KEY}_email`) ||
      (isAdmin ? 'admin@ai-interviewer.com' : null)
    );
  });

  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Validate active HttpOnly cookie session on mount
  useEffect(() => {
    let isMounted = true;

    const verifySession = async () => {
      try {
        const user = await apiGetMe();
        if (!isMounted) return;
        if (user && user.role === 'admin') {
          setIsAdmin(true);
          setAdminEmail(user.email);
        } else {
          setIsAdmin(false);
          setAdminEmail(null);
        }
      } catch {
        if (isMounted) {
          setIsAdmin(false);
          setAdminEmail(null);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    verifySession();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(ADMIN_AUTH_KEY, String(isAdmin));
    if (adminEmail) {
      localStorage.setItem(`${ADMIN_AUTH_KEY}_email`, adminEmail);
    } else {
      localStorage.removeItem(`${ADMIN_AUTH_KEY}_email`);
    }
  }, [isAdmin, adminEmail]);

  const login = useCallback(async (usernameOrEmail: string, pass: string): Promise<boolean> => {
    try {
      const res = await apiLogin(usernameOrEmail, pass);
      if (res && res.user && res.user.role === 'admin') {
        setIsAdmin(true);
        setAdminEmail(res.user.email);
        return true;
      }
      return false;
    } catch (err) {
      console.error('Login error:', err);
      return false;
    }
  }, []);

  const logout = useCallback(async () => {
    setIsAdmin(false);
    setAdminEmail(null);
    localStorage.removeItem(ADMIN_AUTH_KEY);
    localStorage.removeItem(`${ADMIN_AUTH_KEY}_email`);
    await apiLogout();
  }, []);

  return (
    <AdminAuthContext.Provider value={{ isAdmin, adminEmail, isLoading, login, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
};
