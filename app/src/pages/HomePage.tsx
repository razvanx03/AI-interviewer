import React, { useState, useEffect } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { Sparkles, PanelLeftOpen } from 'lucide-react';
import { CreateInterviewForm } from '@/components/forms/CreateInterviewForm';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/hooks/use-language';
import { useInterviews } from '@/hooks/use-interviews';
import { AppLayoutContextType } from '@/components/layout/AppLayout';
import { CreateInterviewInput, InterviewSession } from '@/types';
import { apiCreateInterview } from '@/lib/api';

export const HomePage: React.FC = () => {
  const [isCreating, setIsCreating] = useState(false);
  const { addInterview } = useInterviews();
  const { toggleSidebar } = useOutletContext<AppLayoutContextType>();
  const navigate = useNavigate();
  const { t } = useLanguage();

  useEffect(() => {
    document.title = `${t.brand.name} - ${t.brand.subtitle}`;
  }, [t]);

  const handleCreateSession = async (input: CreateInterviewInput): Promise<InterviewSession> => {
    setIsCreating(true);
    try {
      const session = await apiCreateInterview(input);
      addInterview(session);
      return session;
    } catch (err) {
      console.error('Failed to create interview session:', err);
      throw err;
    } finally {
      setIsCreating(false);
    }
  };

  const handleStartInterview = (session: InterviewSession) => {
    navigate(`/interview/${session.id}`);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top Header */}
      <header className="flex h-11 sm:h-12 shrink-0 items-center justify-between border-b border-border bg-card/60 px-3 sm:px-5 gap-2 backdrop-blur">
        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
          {/* Mobile Menu / Sidebar Trigger */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground md:hidden"
            title="Expand sidebar"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </Button>

          <div className="flex items-center gap-2 min-w-0">
            <div className="hidden sm:flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-500/15 text-blue-500 dark:text-blue-400 border border-blue-500/30 shadow-2xs">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-xs sm:text-sm font-bold text-foreground">
                {t.header.createNew}
              </h1>
              <p className="hidden text-[11px] text-muted-foreground sm:block leading-tight">
                {t.header.configureSubtitle}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Form - Fullscreen 3-Step Wizard */}
      <main className="flex-1 flex flex-col min-h-0 overflow-y-auto pt-2 sm:pt-2.5 px-2.5 sm:px-4 pb-2.5 sm:pb-4 w-full">
        <div className="w-full flex-1 flex flex-col min-h-0">
          <CreateInterviewForm
            onCreateSession={handleCreateSession}
            onStartInterview={handleStartInterview}
            isLoading={isCreating}
          />
        </div>
      </main>
    </div>
  );
};
