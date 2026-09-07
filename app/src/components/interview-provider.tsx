import React, { useState, useEffect, useCallback } from 'react';
import { InterviewSession } from '@/types';
import { apiListInterviews, apiDeleteInterview } from '@/lib/api';
import { getStoredInterviewIds, saveInterviewId, removeInterviewId } from '@/lib/storage';
import { InterviewContext } from '@/context/interview-context';
import { useAdminAuth } from '@/hooks/use-admin-auth';

export const InterviewProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAdmin, isLoading: isAuthLoading } = useAdminAuth();
  const [interviews, setInterviews] = useState<InterviewSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refreshInterviews = useCallback(async () => {
    if (isAuthLoading) return;

    if (!isAdmin) {
      const storedIds = getStoredInterviewIds();
      if (storedIds.length === 0) {
        setInterviews([]);
        setIsLoading(false);
        return;
      }
      try {
        const apiSessions = await apiListInterviews(storedIds);
        apiSessions.sort(
          (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );
        setInterviews(apiSessions);
      } catch (err) {
        console.warn('Failed to load interviews from API:', err);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // When Admin is authenticated: Fetch ALL interview sessions from database
    try {
      const apiSessions = await apiListInterviews();
      apiSessions.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      setInterviews(apiSessions);
    } catch (err) {
      console.warn('Failed to load full admin interview history:', err);
    } finally {
      setIsLoading(false);
    }
  }, [isAdmin, isAuthLoading]);

  useEffect(() => {
    refreshInterviews();
  }, [refreshInterviews]);

  const addInterview = (session: InterviewSession) => {
    saveInterviewId(session.id);
    setInterviews((prev) => [session, ...prev.filter((i) => i.id !== session.id)]);
  };

  const updateInterview = useCallback((session: InterviewSession) => {
    setInterviews((prev) => prev.map((i) => (i.id === session.id ? session : i)));
  }, []);

  const deleteInterview = async (id: string) => {
    await apiDeleteInterview(id);
    removeInterviewId(id);
    setInterviews((prev) => prev.filter((i) => i.id !== id));
  };

  return (
    <InterviewContext.Provider
      value={{
        interviews,
        refreshInterviews,
        addInterview,
        updateInterview,
        deleteInterview,
        isLoading,
      }}
    >
      {children}
    </InterviewContext.Provider>
  );
};
