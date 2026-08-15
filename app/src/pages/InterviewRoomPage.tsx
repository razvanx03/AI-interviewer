import React, { useState, useEffect } from 'react';
import { Bot, AlertCircle, ArrowLeft } from 'lucide-react';
import { InterviewHeader } from '@/components/interview/InterviewHeader';
import { InterviewSidebar } from '@/components/interview/InterviewSidebar';
import { ChatInterface } from '@/components/interview/ChatInterface';
import { Button } from '@/components/ui/button';
import { InterviewSession } from '@/types';
import { getInterviewById, saveInterview } from '@/lib/storage';

interface InterviewRoomPageProps {
  interviewId: string;
  onNavigateHome: () => void;
}

export const InterviewRoomPage: React.FC<InterviewRoomPageProps> = ({
  interviewId,
  onNavigateHome,
}) => {
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loaded = getInterviewById(interviewId);
    setSession(loaded);
    setLoading(false);
  }, [interviewId]);

  const handleSessionUpdate = (updated: InterviewSession) => {
    setSession(updated);
  };

  const handleEndInterview = () => {
    if (!session) return;
    if (confirm('Are you sure you want to end this interview session?')) {
      const updated: InterviewSession = {
        ...session,
        status: 'completed',
        updatedAt: new Date().toISOString(),
      };
      setSession(updated);
      saveInterview(updated);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Bot className="h-6 w-6 animate-pulse text-primary" />
          <span>Loading interview environment...</span>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4 text-center">
        <div className="max-w-md space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-xl font-bold text-foreground">Interview Session Not Found</h2>
          <p className="text-sm text-muted-foreground">
            No active session was found matching ID{' '}
            <span className="font-mono font-medium text-foreground">{interviewId}</span> in this
            browser.
          </p>
          <Button onClick={onNavigateHome} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Return to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <InterviewHeader
        session={session}
        onBackToHome={onNavigateHome}
        onEndInterview={handleEndInterview}
      />

      <main className="flex-1 container mx-auto max-w-6xl px-4 py-6 sm:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-7rem)] min-h-[600px]">
          {/* Main Chat Area */}
          <div className="lg:col-span-8 h-full">
            <ChatInterface session={session} onSessionUpdate={handleSessionUpdate} />
          </div>

          {/* Right Sidebar: Candidate & Job Profile */}
          <div className="hidden lg:block lg:col-span-4 h-full overflow-y-auto pr-1">
            <InterviewSidebar session={session} />
          </div>
        </div>
      </main>
    </div>
  );
};
