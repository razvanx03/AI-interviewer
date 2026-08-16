import React, { useState, useEffect } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { Sparkles, PanelLeftOpen } from 'lucide-react';
import { CreateInterviewForm } from '@/components/forms/CreateInterviewForm';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/hooks/use-language';
import { useInterviews } from '@/hooks/use-interviews';
import { AppLayoutContextType } from '@/components/layout/AppLayout';
import { CreateInterviewInput } from '@/types';
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

  const handleCreateInterview = async (input: CreateInterviewInput) => {
    setIsCreating(true);
    try {
      const session = await apiCreateInterview(input);
      addInterview(session);
      navigate(`/interview/${session.id}`);
    } catch (err) {
      console.error('Failed to create interview:', err);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top Header */}
      <header className="flex h-14 sm:h-16 shrink-0 items-center justify-between border-b border-border bg-card/60 px-3 sm:px-6 gap-2 backdrop-blur">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
          {/* Mobile Menu / Sidebar Trigger */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground md:hidden"
            title="Expand sidebar"
          >
            <PanelLeftOpen className="h-4.5 w-4.5" />
          </Button>

          <div className="flex items-center gap-2 min-w-0">
            <div className="hidden sm:flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-xs sm:text-base font-bold text-foreground">
                {t.header.createNew}
              </h1>
              <p className="hidden text-xs text-muted-foreground sm:block">
                {t.header.configureSubtitle}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Form */}
      <main className="flex-1 overflow-y-auto p-3 sm:p-6 flex justify-center items-start sm:items-center">
        <div className="w-full max-w-2xl py-2 sm:py-0">
          <CreateInterviewForm onSubmit={handleCreateInterview} isLoading={isCreating} />
        </div>
      </main>
    </div>
  );
};
