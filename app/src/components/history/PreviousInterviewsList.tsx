import React from 'react';
import {
  History,
  Calendar,
  User,
  FileText,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Trash2,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { InterviewSession } from '@/types';

interface PreviousInterviewsListProps {
  interviews: InterviewSession[];
  onOpenInterview: (id: string) => void;
  onClearHistory?: () => void;
}

export const PreviousInterviewsList: React.FC<PreviousInterviewsListProps> = ({
  interviews,
  onOpenInterview,
  onClearHistory,
}) => {
  if (interviews.length === 0) {
    return null;
  }

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <Card className="border-border/80 bg-card shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
              <History className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold">Previous Interviews</CardTitle>
              <CardDescription className="text-xs">
                Stored locally on this device ({interviews.length} session
                {interviews.length > 1 ? 's' : ''})
              </CardDescription>
            </div>
          </div>
          {onClearHistory && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearHistory}
              className="text-xs text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="mr-1.5 h-3.5 w-3.5" />
              Clear
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {interviews.map((session) => (
            <div
              key={session.id}
              onClick={() => onOpenInterview(session.id)}
              className="group relative flex cursor-pointer flex-col justify-between rounded-xl border border-border/80 bg-background/50 p-4 transition-all hover:border-primary/50 hover:bg-muted/40 hover:shadow-sm"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-semibold text-foreground transition-colors group-hover:text-primary">
                      {session.jobTitle}
                    </h4>
                    {session.companyName && (
                      <p className="text-xs font-medium text-muted-foreground">
                        {session.companyName}
                      </p>
                    )}
                  </div>
                  <Badge
                    variant={session.status === 'completed' ? 'success' : 'secondary'}
                    className="text-[10px] capitalize"
                  >
                    {session.status === 'completed' ? (
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Done
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        In Progress
                      </span>
                    )}
                  </Badge>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-y-1.5 gap-x-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {session.candidateName}
                  </span>
                  {session.cvFileName && (
                    <span className="flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      {session.cvFileName}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {formatDate(session.createdAt)}
                  </span>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-border/50 pt-3">
                <span className="font-mono text-[11px] text-muted-foreground">
                  /interview/{session.id}
                </span>
                <span className="flex items-center gap-1 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                  Open Chat
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
