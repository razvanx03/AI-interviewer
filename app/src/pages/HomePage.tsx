import React, { useState, useEffect } from 'react';
import { Sparkles, Shield, Cpu } from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { CreateInterviewForm } from '@/components/forms/CreateInterviewForm';
import { PreviousInterviewsList } from '@/components/history/PreviousInterviewsList';
import { CreateInterviewInput, InterviewSession } from '@/types';
import { getStoredInterviews, createNewInterviewSession } from '@/lib/storage';

interface HomePageProps {
  onNavigateToInterview: (id: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigateToInterview }) => {
  const [interviews, setInterviews] = useState<InterviewSession[]>([]);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    setInterviews(getStoredInterviews());
  }, []);

  const handleCreateInterview = (input: CreateInterviewInput) => {
    setIsCreating(true);
    try {
      const newSession = createNewInterviewSession(input);
      // Immediately open the created interview room
      onNavigateToInterview(newSession.id);
    } catch (err) {
      console.error('Failed to create interview session:', err);
      setIsCreating(false);
    }
  };

  const handleClearHistory = () => {
    if (confirm('Are you sure you want to clear all interview history from this browser?')) {
      localStorage.removeItem('ai_interviewer_sessions_v1');
      setInterviews([]);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Header />

      <main className="flex-1 container mx-auto max-w-6xl px-4 py-8 sm:px-8 space-y-10">
        {/* Hero Section */}
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            AI-Driven Technical Screening
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Practice & Run Specialized Job Interviews
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
            Upload your resume, specify the role and requirements, and let our specialized AI
            conduct a full-context technical interview.
          </p>
        </div>

        {/* Main Grid: Form and History */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Create Interview Form */}
          <div className="lg:col-span-7">
            <CreateInterviewForm onSubmit={handleCreateInterview} isLoading={isCreating} />
          </div>

          {/* Side Column: Previous Interviews & Platform Benefits */}
          <div className="lg:col-span-5 space-y-6">
            <PreviousInterviewsList
              interviews={interviews}
              onOpenInterview={onNavigateToInterview}
              onClearHistory={handleClearHistory}
            />

            {/* Platform Feature Badges */}
            <div className="rounded-xl border border-border/70 bg-card/40 p-5 space-y-4 text-xs">
              <h3 className="font-semibold text-foreground text-sm flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" />
                How It Works
              </h3>
              <div className="space-y-2.5 text-muted-foreground">
                <div className="flex gap-2.5">
                  <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-[10px]">
                    1
                  </div>
                  <p>
                    <strong className="text-foreground">Job Context:</strong> We analyze the target
                    role and key competencies.
                  </p>
                </div>
                <div className="flex gap-2.5">
                  <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-[10px]">
                    2
                  </div>
                  <p>
                    <strong className="text-foreground">Resume Parsing:</strong> We match questions
                    directly to your career history.
                  </p>
                </div>
                <div className="flex gap-2.5">
                  <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-[10px]">
                    3
                  </div>
                  <p>
                    <strong className="text-foreground">Adaptive AI:</strong> Follow-up questions
                    dynamically probe depth and edge cases.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
                <Shield className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                <span>100% Client-side local prototype. No account required.</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
