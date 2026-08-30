import React from 'react';
import { FileText, Award, Layers, CheckCircle2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { InterviewSession } from '@/types';

interface InterviewSidebarProps {
  session: InterviewSession;
}

export const InterviewSidebar: React.FC<InterviewSidebarProps> = ({ session }) => {
  return (
    <div className="space-y-4">
      {/* Job Profile */}
      <Card className="border-border/80 bg-card/60">
        <CardHeader className="pb-3 pt-4">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <Layers className="h-4 w-4 text-primary" />
            Position Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div>
            <p className="text-muted-foreground">Target Role</p>
            <p className="font-medium text-foreground">{session.jobTitle}</p>
          </div>
          {session.companyName && (
            <div>
              <p className="text-muted-foreground">Company</p>
              <p className="font-medium text-foreground">{session.companyName}</p>
            </div>
          )}
          <div>
            <p className="text-muted-foreground">Experience Level</p>
            <Badge variant="secondary" className="mt-1 text-[11px] capitalize">
              {session.experienceLevel} Level
            </Badge>
          </div>
          <Separator />
          <div>
            <p className="mb-1 text-muted-foreground">Job Requirements</p>
            <div className="max-h-36 overflow-y-auto whitespace-pre-wrap rounded-md bg-muted/40 p-2 text-[11px] leading-relaxed text-foreground">
              {session.jobDescription}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Candidate CV Profile */}
      <Card className="border-border/80 bg-card/60">
        <CardHeader className="pb-3 pt-4">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <FileText className="h-4 w-4 text-primary" />
            Resume Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          {session.cvFileName ? (
            <div className="flex items-center gap-2 rounded-md bg-muted/50 border border-border p-2 text-foreground">
              <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
              <span className="truncate font-medium">{session.cvFileName}</span>
            </div>
          ) : (
            <p className="italic text-muted-foreground">No CV file attached (General profile)</p>
          )}

          {/* Detected Candidate Strengths from Screening */}
          {(() => {
            const topResult =
              session.screeningResults?.find((r) => r.is_selected) || session.screeningResults?.[0];
            const strengths = topResult?.strengths;
            if (!strengths || strengths.length === 0) return null;
            return (
              <div>
                <p className="mb-1.5 flex items-center gap-1 text-muted-foreground">
                  <Award className="h-3.5 w-3.5 text-amber-500" />
                  Detected Skills & Competencies
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {strengths.map((skill, i) => (
                    <Badge key={i} variant="outline" className="text-[10px]">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            );
          })()}
        </CardContent>
      </Card>
    </div>
  );
};
