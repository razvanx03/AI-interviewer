import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { HomePage } from '@/pages/HomePage';
import { InterviewRoomPage } from '@/pages/InterviewRoomPage';
import { LoginPage } from '@/pages/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ThinkingOrb } from 'thinking-orbs';
import { InterviewProvider } from '@/components/interview-provider';
import { AdminAuthProvider } from '@/components/admin-provider';
import { useAdminAuth } from '@/hooks/use-admin-auth';

const AdminProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAdmin, isLoading } = useAdminAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <ThinkingOrb state="connecting" size={64} />
      </div>
    );
  }

  if (!isAdmin) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export function App() {
  return (
    <AdminAuthProvider>
      <InterviewProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AppLayout />}>
            <Route
              path="/"
              element={
                <AdminProtectedRoute>
                  <HomePage />
                </AdminProtectedRoute>
              }
            />
            <Route path="/interview/:id" element={<InterviewRoomPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </InterviewProvider>
    </AdminAuthProvider>
  );
}

export default App;
