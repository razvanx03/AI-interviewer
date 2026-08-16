import { createContext } from 'react';
import { InterviewSession } from '@/types';

export interface InterviewContextType {
  interviews: InterviewSession[];
  refreshInterviews: () => Promise<void>;
  addInterview: (session: InterviewSession) => void;
  updateInterview: (session: InterviewSession) => void;
  deleteInterview: (id: string) => Promise<void>;
  isLoading: boolean;
}

export const InterviewContext = createContext<InterviewContextType | undefined>(undefined);
