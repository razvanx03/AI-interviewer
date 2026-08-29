import React, { useState, useEffect } from 'react';
import { ArrowLeft, Check, Share2, Bot, StopCircle, Timer } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ModeToggle } from '@/components/mode-toggle';
import { useAdminAuth } from '@/hooks/use-admin-auth';
import { InterviewSession } from '@/types';

interface InterviewHeaderProps {
  session: InterviewSession;
  onBackToHome: () => void;
  onEndInterview: () => void;
}

export const InterviewHeader: React.FC<InterviewHeaderProps> = ({
  session,
  onBackToHome,
  onEndInterview,
}) => {
  const { isAdmin } = useAdminAuth();
  const [copied, setCopied] = useState(false);

  // Time remaining in seconds
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(() => {
    if (!session.timeLimitMinutes || session.status === 'completed') return null;
    const createdAtMs = new Date(session.createdAt).getTime();
    const durationMs = session.timeLimitMinutes * 60 * 1000;
    const endMs = createdAtMs + durationMs;
    return Math.max(0, Math.floor((endMs - Date.now()) / 1000));
  });

  useEffect(() => {
    if (!session.timeLimitMinutes || session.status === 'completed') {
      setRemainingSeconds(null);
      return;
    }

    const interval = setInterval(() => {
      const createdAtMs = new Date(session.createdAt).getTime();
      const durationMs = session.timeLimitMinutes! * 60 * 1000;
      const endMs = createdAtMs + durationMs;
      const rem = Math.max(0, Math.floor((endMs - Date.now()) / 1000));

      setRemainingSeconds(rem);

      if (rem <= 0) {
        clearInterval(interval);
        onEndInterview();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [session.createdAt, session.timeLimitMinutes, session.status, onEndInterview]);

  const formatTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/95 backdrop-blur">
      <div className="container mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-8">
        {/* Left: Back & Title */}
        <div className="flex items-center gap-3">
          {isAdmin && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onBackToHome}
              className="h-9 w-9 text-muted-foreground hover:text-foreground"
              title="Return to Dashboard"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          )}

          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm sm:text-base font-bold text-foreground line-clamp-1">
                  {session.jobTitle}
                </h1>
                {session.companyName && (
                  <Badge variant="outline" className="hidden sm:inline-flex text-[11px]">
                    {session.companyName}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                Candidate:{' '}
                <span className="font-medium text-foreground">{session.candidateName}</span>
              </p>
            </div>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Live Countdown Timer Badge */}
          {remainingSeconds !== null && session.status !== 'completed' && (
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-mono text-xs select-none transition-colors ${
                remainingSeconds < 60
                  ? 'bg-red-500/15 text-red-500 border-red-500/40 animate-pulse font-bold'
                  : remainingSeconds < 180
                    ? 'bg-amber-500/15 text-amber-500 border-amber-500/30 font-semibold'
                    : 'bg-muted/50 text-foreground border-border/80'
              }`}
              title={`Allocated duration: ${session.timeLimitMinutes} minutes`}
            >
              <Timer className="h-3.5 w-3.5" />
              <span>{formatTimer(remainingSeconds)}</span>
            </div>
          )}

          {/* Shareable Link Copier */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyLink}
            className="gap-1.5 text-xs font-medium"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-500" />
                <span className="hidden sm:inline">Copied URL</span>
              </>
            ) : (
              <>
                <Share2 className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="hidden sm:inline">Share Link</span>
              </>
            )}
          </Button>

          {/* End Interview */}
          {session.status !== 'completed' && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onEndInterview}
              className="gap-1.5 text-xs text-destructive hover:bg-destructive/10 cursor-pointer"
            >
              <StopCircle className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Finish</span>
            </Button>
          )}

          <Badge
            variant={session.status === 'completed' ? 'success' : 'default'}
            className="text-xs capitalize select-none"
          >
            {session.status === 'completed' ? 'Completed' : 'Live Interview'}
          </Badge>

          <ModeToggle />
        </div>
      </div>
    </header>
  );
};
