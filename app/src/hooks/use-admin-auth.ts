import { useContext } from 'react';
import { AdminAuthContext, AdminAuthContextType } from '@/context/admin-context';

export const useAdminAuth = (): AdminAuthContextType => {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider');
  }
  return context;
};
