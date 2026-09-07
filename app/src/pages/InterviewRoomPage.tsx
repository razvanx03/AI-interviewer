import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, useOutletContext } from 'react-router-dom';
import { Share2, Check, StopCircle, Bot, PanelLeftOpen, Timer, Globe } from 'lucide-react';
import { ThinkingOrb } from 'thinking-orbs';
import { ChatInterface } from '@/components/interview/ChatInterface';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { DeleteConfirmDialog } from '@/components/dialogs/DeleteConfirmDialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ModeToggle } from '@/components/mode-toggle';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useLanguage } from '@/hooks/use-language';
import { useInterviews } from '@/hooks/use-interviews';
import { useAdminAuth } from '@/hooks/use-admin-auth';
import { AppLayoutContextType } from '@/components/layout/AppLayout';
import { InterviewSession } from '@/types';
import { apiGetInterview, apiCompleteInterview } from '@/lib/api';

export const InterviewRoomPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const outletCtx = useOutletContext<AppLayoutContextType | null>();
  const { updateInterview } = useInterviews();
  const { isAdmin } = useAdminAuth();
  const { language, setLanguage, t } = useLanguage();

  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [showFinishDialog, setShowFinishDialog] = useState(false);
  const [endingSessionId, setEndingSessionId] = useState<string | null>(null);
  const endingSessionIdRef = useRef<string | null>(null);
  const isCurrentSessionEnding = Boolean(activeSession && endingSessionId === activeSession.id);
  const hasInitializedLangRef = useRef<string | null>(null);
  const autoEvaluatedSessionsRef = useRef<Set<string>>(new Set());
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);

  const handleLanguageChange = (lang: 'en' | 'ro') => {
    setLanguage(lang);
    if (activeSession && activeSession.language !== lang) {
      const updated: InterviewSession = { ...activeSession, language: lang };
      setActiveSession(updated);
      updateInterview(updated);
    }
  };

  const handleEndInterview = useCallback(async () => {
    if (
      !activeSession ||
      activeSession.status === 'completed' ||
      activeSession.status === 'finishing' ||
      endingSessionIdRef.current === activeSession.id
    )
      return;
    const targetSessionId = activeSession.id;
    endingSessionIdRef.current = targetSessionId;
    setEndingSessionId(targetSessionId);

    // Optimistically update status to 'finishing' so Finish button disappears immediately!
    const optimistic: InterviewSession = {
      ...activeSession,
      status: 'finishing',
      updatedAt: new Date().toISOString(),
    };
    autoEvaluatedSessionsRef.current.add(targetSessionId);
    setActiveSession(optimistic);
    updateInterview(optimistic);

    try {
      const updated = await apiCompleteInterview(targetSessionId);
      if (updated) {
        setActiveSession((prev) => (prev && prev.id === targetSessionId ? updated : prev));
        updateInterview(updated);
      }
    } catch (err) {
      console.error('Failed to complete interview:', err);
    } finally {
      if (endingSessionIdRef.current === targetSessionId) {
        endingSessionIdRef.current = null;
        setEndingSessionId(null);
      }
      setShowFinishDialog(false);
    }
  }, [activeSession, updateInterview]);

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
          if (
            hasInitializedLangRef.current !== fresh.id &&
            fresh.language &&
            (fresh.language === 'ro' || fresh.language === 'en')
          ) {
            hasInitializedLangRef.current = fresh.id;
            setLanguage(fresh.language);
          }
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
  }, [id, setLanguage]);

  // Live Timer Countdown Effect
  useEffect(() => {
    if (
      !activeSession?.timeLimitMinutes ||
      activeSession.status === 'completed' ||
      activeSession.status === 'finishing'
    ) {
      setRemainingSeconds(null);
      return;
    }

    const calcRemaining = () => {
      const createdAtMs = new Date(activeSession.createdAt).getTime();
      const durationMs = activeSession.timeLimitMinutes! * 60 * 1000;
      const endMs = createdAtMs + durationMs;
      const rem = Math.max(0, Math.floor((endMs - Date.now()) / 1000));
      return rem;
    };

    const initialRem = calcRemaining();
    setRemainingSeconds(initialRem);

    if (initialRem <= 0) {
      if (endingSessionIdRef.current !== activeSession.id) {
        handleEndInterview();
      }
      return;
    }

    const interval = setInterval(() => {
      const rem = calcRemaining();
      setRemainingSeconds(rem);

      if (rem <= 0) {
        clearInterval(interval);
        if (endingSessionIdRef.current !== activeSession.id) {
          handleEndInterview();
        }
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [
    activeSession?.createdAt,
    activeSession?.timeLimitMinutes,
    activeSession?.status,
    handleEndInterview,
  ]);

  const formatTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  // Intelligent Polling for Finishing / Completed Sessions without evaluation
  useEffect(() => {
    if (
      !id ||
      !activeSession ||
      (activeSession.status !== 'finishing' && activeSession.status !== 'completed')
    ) {
      return;
    }

    const hasEval = activeSession.messages.some((m) => {
      if (m.role !== 'assistant') return false;
      const c = m.content.toLowerCase();
      return (
        c.includes('overall ai assessment') ||
        c.includes('evaluare general') ||
        c.includes('recruiter evaluation report') ||
        c.includes('arii de îmbunătățire') ||
        c.includes('arii de imbunatatire') ||
        c.includes('areas for improvement')
      );
    });

    if (activeSession.status === 'completed' && hasEval) {
      return;
    }

    // If session is finishing/completed without eval, trigger complete if not already requested
    if (
      !hasEval &&
      !autoEvaluatedSessionsRef.current.has(activeSession.id) &&
      endingSessionIdRef.current !== activeSession.id
    ) {
      const targetSessionId = activeSession.id;
      autoEvaluatedSessionsRef.current.add(targetSessionId);
      endingSessionIdRef.current = targetSessionId;
      setEndingSessionId(targetSessionId);
      apiCompleteInterview(targetSessionId)
        .then((updated) => {
          if (updated) {
            setActiveSession((prev) => (prev && prev.id === targetSessionId ? updated : prev));
            updateInterview(updated);
          }
        })
        .finally(() => {
          if (endingSessionIdRef.current === targetSessionId) {
            endingSessionIdRef.current = null;
            setEndingSessionId(null);
          }
        });
    }

    let isPolling = true;
    const interval = setInterval(async () => {
      try {
        const fresh = await apiGetInterview(id);
        if (!isPolling || !fresh) return;
        const freshHasEval = fresh.messages.some((m) => {
          if (m.role !== 'assistant') return false;
          const c = m.content.toLowerCase();
          return (
            c.includes('overall ai assessment') ||
            c.includes('evaluare general') ||
            c.includes('recruiter evaluation report')
          );
        });

        if (fresh.status === 'completed' && freshHasEval) {
          setActiveSession(fresh);
          updateInterview(fresh);
          if (endingSessionIdRef.current === id) {
            endingSessionIdRef.current = null;
            setEndingSessionId(null);
          }
          clearInterval(interval);
        } else if (
          fresh.status !== activeSession.status ||
          fresh.messages.length !== activeSession.messages.length
        ) {
          setActiveSession(fresh);
          updateInterview(fresh);
        }
      } catch (err) {
        console.error('Polling for completed evaluation report failed:', err);
      }
    }, 2500);

    return () => {
      isPolling = false;
      clearInterval(interval);
    };
  }, [id, isAdmin, activeSession, updateInterview]);

  // Dynamic Browser Title
  useEffect(() => {
    if (activeSession) {
      document.title = activeSession.jobTitle;
    }
  }, [activeSession]);

  // Intelligent Background Polling for Live Admin Observation (Option 1)
  useEffect(() => {
    // Only poll if user is Admin, session is active and loaded
    if (!isAdmin || !id || !activeSession || activeSession.status === 'completed') {
      return;
    }

    let isPollingActive = true;

    const pollSession = async () => {
      try {
        const fresh = await apiGetInterview(id);
        if (!isPollingActive || !fresh) return;

        setActiveSession((prev) => {
          if (!prev) return fresh;

          const prevMsgCount = prev.messages?.length || 0;
          const freshMsgCount = fresh.messages?.length || 0;
          const statusChanged = prev.status !== fresh.status;

          const lastPrevMsg = prev.messages?.[prevMsgCount - 1];
          const lastFreshMsg = fresh.messages?.[freshMsgCount - 1];
          const lastMsgChanged =
            lastPrevMsg?.id !== lastFreshMsg?.id || lastPrevMsg?.content !== lastFreshMsg?.content;

          if (prevMsgCount !== freshMsgCount || statusChanged || lastMsgChanged) {
            updateInterview(fresh);
            return fresh;
          }
          return prev;
        });
      } catch (err) {
        console.warn('Live background polling check failed:', err);
      }
    };

    const interval = setInterval(pollSession, 2000);

    return () => {
      isPollingActive = false;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, id, activeSession?.status, updateInterview]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
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
    return <NotFoundPage onNewInterview={() => navigate(isAdmin ? '/' : '/login')} />;
  }

  if (!activeSession) return null;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top Header */}
      <header className="flex h-14 sm:h-16 shrink-0 items-center justify-between border-b border-border bg-card/60 px-3 sm:px-6 gap-2 backdrop-blur">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
          {/* Mobile Menu / Sidebar Trigger (Admin only) */}
          {isAdmin && outletCtx?.toggleSidebar && (
            <Button
              variant="ghost"
              size="icon"
              onClick={outletCtx.toggleSidebar}
              className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground md:hidden"
              title="Expand sidebar"
            >
              <PanelLeftOpen className="h-4.5 w-4.5" />
            </Button>
          )}

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
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Live Countdown Timer Badge */}
          {remainingSeconds !== null && activeSession.status !== 'completed' && (
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-mono text-xs select-none transition-colors ${
                remainingSeconds < 60
                  ? 'bg-red-500/15 text-red-500 border-red-500/40 animate-pulse font-bold'
                  : remainingSeconds < 180
                    ? 'bg-amber-500/15 text-amber-500 border-amber-500/30 font-semibold'
                    : 'bg-muted/50 text-foreground border-border/80'
              }`}
              title={`Allocated duration: ${activeSession.timeLimitMinutes} minutes`}
            >
              <Timer className="h-3.5 w-3.5" />
              <span>{formatTimer(remainingSeconds)}</span>
            </div>
          )}

          {/* Share Link (ADMIN ONLY) */}
          {isAdmin && (
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
          )}

          {/* Language Switcher & Theme Toggle (CANDIDATE ONLY - Admin has settings cog in sidebar) */}
          {!isAdmin && (
            <>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 gap-1.5 px-2.5 text-xs font-medium bg-card/60 backdrop-blur"
                  >
                    <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>{language === 'ro' ? 'RO' : 'EN'}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-36">
                  <DropdownMenuItem
                    onClick={() => handleLanguageChange('en')}
                    className="flex items-center justify-between text-xs cursor-pointer"
                  >
                    <span>English</span>
                    {language === 'en' && <Check className="h-3.5 w-3.5 text-primary" />}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => handleLanguageChange('ro')}
                    className="flex items-center justify-between text-xs cursor-pointer"
                  >
                    <span>Română</span>
                    {language === 'ro' && <Check className="h-3.5 w-3.5 text-primary" />}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              <ModeToggle />
            </>
          )}

          {/* Finish Button */}
          {activeSession.status === 'active' && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowFinishDialog(true)}
              disabled={isCurrentSessionEnding}
              className="h-8 px-2 sm:px-3 gap-1.5 text-xs text-destructive hover:bg-destructive/10 cursor-pointer"
              title={t.header.finish}
            >
              {isCurrentSessionEnding ? (
                <ThinkingOrb state="working" size={20} />
              ) : (
                <StopCircle className="h-3.5 w-3.5" />
              )}
              <span className="hidden sm:inline">{t.header.finish}</span>
            </Button>
          )}

          {/* Status Badge */}
          {activeSession.status === 'completed' ? (
            <Badge
              variant="outline"
              className="border-emerald-500/30 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 text-[10px] sm:text-xs font-medium px-2 py-0.5 h-8"
            >
              {t.header.completed}
            </Badge>
          ) : activeSession.status === 'finishing' ? (
            <Badge
              variant="outline"
              className="border-amber-500/30 bg-amber-500/15 text-amber-600 dark:text-amber-400 text-[10px] sm:text-xs font-medium px-2 py-0.5 h-8 gap-1.5"
            >
              <ThinkingOrb state="working" size={20} />
              <span>{language === 'ro' ? 'Finalizare...' : 'Finishing...'}</span>
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="border-emerald-500/30 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 text-[10px] sm:text-xs font-medium px-2 py-0.5 h-8 gap-1.5"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>{t.header.live}</span>
            </Badge>
          )}
        </div>
      </header>

      {/* Main Chat Interface */}
      <main className="flex-1 overflow-hidden">
        <ChatInterface
          session={activeSession}
          onSessionUpdate={handleSessionUpdate}
          isEnding={isCurrentSessionEnding}
        />
      </main>

      {/* Conclude Interview Confirmation Modal */}
      <DeleteConfirmDialog
        open={showFinishDialog}
        onOpenChange={setShowFinishDialog}
        onConfirm={handleEndInterview}
        title={t.header.finishConfirmTitle}
        description={t.header.finishConfirmDesc}
        confirmText={t.header.finishConfirmBtn || t.header.finish}
        confirmIcon="stop"
      />
    </div>
  );
};
