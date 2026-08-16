import { useContext } from 'react';
import { InterviewContext, InterviewContextType } from '@/context/interview-context';

export const useInterviews = (): InterviewContextType => {
  const context = useContext(InterviewContext);
  if (!context) {
    throw new Error('useInterviews must be used within an InterviewProvider');
  }
  return context;
};
