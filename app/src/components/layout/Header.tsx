import React from 'react';
import { Bot, Sparkles, PlusCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ModeToggle } from '@/components/mode-toggle';

interface HeaderProps {
  onNavigateHome?: () => void;
  onNewInterview?: () => void;
  showNewButton?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onNavigateHome,
  onNewInterview,
  showNewButton = false,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/60 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-8">
        {/* Brand */}
        <div
          onClick={onNavigateHome}
          className="flex cursor-pointer items-center gap-3 transition-opacity hover:opacity-90"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight">InterviewAI</span>
              <Badge variant="secondary" className="text-[10px] font-medium tracking-wide">
                <Sparkles className="mr-1 h-3 w-3 text-amber-500" />
                BETA
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">Autonomous Job Interviewer</p>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {showNewButton && onNewInterview && (
            <Button onClick={onNewInterview} size="sm" className="gap-2">
              <PlusCircle className="h-4 w-4" />
              New Interview
            </Button>
          )}
          <ModeToggle />
        </div>
      </div>
    </header>
  );
};
