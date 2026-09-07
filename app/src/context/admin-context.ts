import { createContext } from 'react';

export interface AdminAuthContextType {
  isAdmin: boolean;
  adminEmail: string | null;
  isLoading: boolean;
  login: (usernameOrEmail: string, pass: string) => Promise<boolean>;
  logout: () => Promise<void>;
}

export const AdminAuthContext = createContext<AdminAuthContextType | undefined>(undefined);
