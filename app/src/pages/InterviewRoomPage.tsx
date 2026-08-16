import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useOutletContext } from 'react-router-dom';
import { Share2, Check, StopCircle, Bot, Loader2, PanelLeftOpen } from 'lucide-react';
import { ThinkingOrb } from 'thinking-orbs';
import { ChatInterface } from '@/components/interview/ChatInterface';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { DeleteConfirmDialog } from '@/components/dialogs/DeleteConfirmDialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useLanguage } from '@/hooks/use-language';
import { useInterviews } from '@/hooks/use-interviews';
import { AppLayoutContextType } from '@/components/layout/AppLayout';
import { InterviewSession } from '@/types';
import { apiGetInterview, apiCompleteInterview } from '@/lib/api';

export const InterviewRoomPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toggleSidebar } = useOutletContext<AppLayoutContextType>();
  const { updateInterview } = useInterviews();
  const { t } = useLanguage();

  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [showFinishDialog, setShowFinishDialog] = useState(false);
  const [isEnding, setIsEnding] = useState(false);

  useEffect(() => {
    if (!id) {
      setIsNotFound(true);
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setActiveSession(null);

    const loadSession = async () => {
      try {
        const [fresh] = await Promise.all([
          apiGetInterview(id),
          new Promise((resolve) => setTimeout(resolve, 500)),
        ]);

        if (!isMounted) return;

        if (fresh) {
          setActiveSession(fresh);
          setIsNotFound(false);
        } else {
          setIsNotFound(true);
        }
      } catch (err) {
        if (!isMounted) return;
        console.error('Failed to fetch interview session from DB:', err);
        setIsNotFound(true);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadSession();

    return () => {
      isMounted = false;
    };
  }, [id]);

  // Dynamic Browser Title (ChatGPT style: conversation title only)
  useEffect(() => {
    if (activeSession) {
      document.title = activeSession.jobTitle;
    }
  }, [activeSession]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleEndInterview = async () => {
    if (!activeSession) return;
    setIsEnding(true);
    try {
      const updated = await apiCompleteInterview(activeSession.id);
      if (updated) {
        setActiveSession(updated);
        updateInterview(updated);
      } else {
        const fallback: InterviewSession = {
          ...activeSession,
          status: 'completed',
          updatedAt: new Date().toISOString(),
        };
        setActiveSession(fallback);
        updateInterview(fallback);
      }
    } finally {
      setIsEnding(false);
      setShowFinishDialog(false);
    }
  };

  const handleSessionUpdate = (updated: InterviewSession) => {
    setActiveSession(updated);
    updateInterview(updated);
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <ThinkingOrb state="connecting" size={64} />
      </div>
    );
  }

  if (isNotFound || (!activeSession && !isLoading)) {
    return <NotFoundPage onNewInterview={() => navigate('/')} />;
  }

  if (!activeSession) return null;

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

          {/* Active Interview Details */}
          <div className="hidden sm:flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
            <Bot className="h-5 w-5" />
          </div>

          <div className="min-w-0 flex-1">
            <h1 className="truncate text-xs sm:text-base font-bold text-foreground leading-tight">
              {activeSession.jobTitle}
            </h1>
            <p className="truncate text-[11px] sm:text-xs text-muted-foreground flex items-center gap-1 sm:gap-1.5 mt-0.5">
              <span className="truncate">
                <span className="hidden sm:inline">{t.header.candidate}: </span>
                <span className="font-medium text-foreground">{activeSession.candidateName}</span>
              </span>
              {activeSession.companyName && (
                <>
                  <span className="text-muted-foreground/50 shrink-0">•</span>
                  <span className="truncate">
                    <span className="hidden sm:inline">{t.header.company}: </span>
                    <span className="font-medium text-foreground">{activeSession.companyName}</span>
                  </span>
                </>
              )}
            </p>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          {/* Share Link */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyLink}
            className="h-8 px-2 sm:px-3 gap-1.5 text-xs font-medium"
            title={t.header.share}
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-500" />
                <span className="hidden sm:inline">{t.header.copied}</span>
              </>
            ) : (
              <>
                <Share2 className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="hidden sm:inline">{t.header.share}</span>
              </>
            )}
          </Button>

          {/* Finish Button */}
          {activeSession.status !== 'completed' && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowFinishDialog(true)}
              disabled={isEnding}
              className="h-8 px-2 sm:px-3 gap-1.5 text-xs text-destructive hover:bg-destructive/10 cursor-pointer"
              title={t.header.finish}
            >
              {isEnding ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <StopCircle className="h-3.5 w-3.5" />
              )}
              <span className="hidden sm:inline">{t.header.finish}</span>
            </Button>
          )}

          {/* Status Badge: Orange for Live, Green for Completed */}
          {activeSession.status === 'completed' ? (
            <Badge
              variant="outline"
              className="border-emerald-500/30 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 text-[10px] sm:text-xs font-medium px-2 py-0.5 h-7"
            >
              {t.header.completed}
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="border-amber-500/30 bg-amber-500/15 text-amber-600 dark:text-amber-400 text-[10px] sm:text-xs font-medium px-2 py-0.5 h-7"
            >
              {t.header.live}
            </Badge>
          )}
        </div>
      </header>

      {/* Main Chat Interface */}
      <main className="flex-1 overflow-hidden">
        <ChatInterface session={activeSession} onSessionUpdate={handleSessionUpdate} />
      </main>

      {/* Conclude Interview Confirmation Modal */}
      <DeleteConfirmDialog
        open={showFinishDialog}
        onOpenChange={setShowFinishDialog}
        onConfirm={handleEndInterview}
        title={t.header.finishConfirmTitle}
        description={t.header.finishConfirmDesc}
        confirmText={t.header.finishConfirmBtn}
        confirmIcon="stop"
      />
    </div>
  );
};
