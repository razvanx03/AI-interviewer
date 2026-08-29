import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Briefcase,
  Building2,
  FileSpreadsheet,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  AlertCircle,
  Users,
  CheckCircle2,
  Trophy,
  Copy,
  Check,
  ChevronRight,
  ExternalLink,
  FileText,
} from 'lucide-react';
import { ThinkingOrb } from 'thinking-orbs';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CVUploader } from '@/components/forms/CVUploader';
import { useLanguage } from '@/hooks/use-language';
import {
  CreateInterviewInput,
  ExperienceLevel,
  CandidateItem,
  InterviewSession,
  CandidateScreeningResult,
} from '@/types';
import { apiScreenCandidates } from '@/lib/api';

interface CreateInterviewFormProps {
  onCreateSession: (data: CreateInterviewInput) => Promise<InterviewSession>;
  onStartInterview: (session: InterviewSession) => void;
  isLoading?: boolean;
}

export const CreateInterviewForm: React.FC<CreateInterviewFormProps> = ({
  onCreateSession,
  onStartInterview,
  isLoading = false,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const rawStep = searchParams.get('step');
  const targetStep = rawStep === '2' ? 2 : rawStep === '3' ? 3 : 1;

  const [jobTitle, setJobTitle] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>('senior');
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);

  // Screening & Session state
  const [screeningResults, setScreeningResults] = useState<CandidateScreeningResult[]>([]);
  const [topCandidate, setTopCandidate] = useState<CandidateScreeningResult | null>(null);
  const [createdSession, setCreatedSession] = useState<InterviewSession | null>(null);

  const [isScreening, setIsScreening] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [isCopying, setIsCopying] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const { t } = useLanguage();

  // Helper to change step and update URL route
  const goToStep = (step: 1 | 2 | 3) => {
    setSearchParams({ step: String(step) });
  };

  // Redirect Guard: Validate step prerequisites on URL change / page refresh
  useEffect(() => {
    // Guard 1: Step 2 requires valid jobTitle and jobDescription
    if (targetStep === 2 && (!jobTitle.trim() || !jobDescription.trim())) {
      setSearchParams({ step: '1' }, { replace: true });
      return;
    }

    // Guard 2: Step 3 requires screened candidate or active session
    if (targetStep === 3) {
      if (!topCandidate && !createdSession) {
        if (jobTitle.trim() && jobDescription.trim()) {
          setSearchParams({ step: '2' }, { replace: true });
        } else {
          setSearchParams({ step: '1' }, { replace: true });
        }
      }
    }
  }, [targetStep, jobTitle, jobDescription, topCandidate, createdSession, setSearchParams]);

  // Derived current step based on valid state
  const currentStep: 1 | 2 | 3 =
    targetStep === 2 && jobTitle.trim() && jobDescription.trim()
      ? 2
      : targetStep === 3 && (topCandidate || createdSession)
        ? 3
        : 1;

  const handleAddFiles = (files: File[]) => {
    setFormError(null);
    const newItems: CandidateItem[] = files.map((file) => {
      const cleanName = file.name
        .replace(/\.(pdf|docx|doc|txt)$/i, '')
        .replace(/[-_]/g, ' ')
        .replace(/\bcv\b|\bresume\b/gi, '')
        .trim();

      const formattedName = cleanName
        ? cleanName
            .split(' ')
            .filter(Boolean)
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
            .join(' ')
        : 'Candidate';

      const sizeFormatted = `${(file.size / (1024 * 1024)).toFixed(1)} MB`;

      return {
        id: Math.random().toString(36).substring(2, 9),
        name: formattedName,
        cvFileName: file.name,
        file,
        fileSizeFormatted: sizeFormatted,
        cvRawText: `Candidate ${formattedName} resume file ${file.name}`,
      };
    });

    setCandidates((prev) => [...prev, ...newItems]);
  };

  const handleRemoveCandidate = (index: number) => {
    setCandidates((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateCandidateName = (index: number, name: string) => {
    setCandidates((prev) => prev.map((c, i) => (i === index ? { ...c, name } : c)));
  };

  const handleNextStep1 = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobTitle.trim() || !jobDescription.trim()) {
      setFormError(t.form.validationError);
      return;
    }
    setFormError(null);
    goToStep(2);
  };

  // Step 2 -> 3: Pure Screening evaluation (Does NOT start or save active interview in history yet)
  const handleStep2Screen = async (e: React.FormEvent) => {
    e.preventDefault();
    if (candidates.length === 0) {
      setFormError(t.form.noCandidatesError);
      return;
    }
    setFormError(null);
    setIsScreening(true);

    try {
      const res = await apiScreenCandidates({
        jobTitle: jobTitle.trim(),
        companyName: companyName.trim() || undefined,
        jobDescription: jobDescription.trim(),
        experienceLevel,
        candidates,
      });
      setTopCandidate(res.top_candidate);
      setScreeningResults(res.screening_results);
      setCreatedSession(null);
      goToStep(3);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to screen candidates.');
    } finally {
      setIsScreening(false);
    }
  };

  const handleSelectCandidate = (candidate: CandidateScreeningResult) => {
    setTopCandidate(candidate);
    setCreatedSession(null); // Reset session to ensure new session uses this selected candidate
    setScreeningResults((prev) =>
      prev.map((c) => ({
        ...c,
        is_selected: c.name.toLowerCase() === candidate.name.toLowerCase(),
      }))
    );
  };

  // Helper to ensure database session is created only when needed (on Start or on Copy Link)
  const getOrCreateSession = async (): Promise<InterviewSession> => {
    if (createdSession) return createdSession;

    // Order candidates so the active selected winner is first in the list
    const activeWinner =
      topCandidate || screeningResults.find((r) => r.is_selected) || screeningResults[0];
    const orderedCandidates = [...candidates];
    if (activeWinner) {
      const matchIdx = orderedCandidates.findIndex(
        (c) => c.name.toLowerCase() === activeWinner.name.toLowerCase()
      );
      if (matchIdx > 0) {
        const [winner] = orderedCandidates.splice(matchIdx, 1);
        orderedCandidates.unshift(winner);
      }
    }

    const session = await onCreateSession({
      jobTitle: jobTitle.trim(),
      companyName: companyName.trim() || undefined,
      jobDescription: jobDescription.trim(),
      experienceLevel,
      candidates: orderedCandidates,
    });
    setCreatedSession(session);
    return session;
  };

  const handleStartLiveInterview = async () => {
    if (isStarting || isCopying || isLoading) return;
    setIsStarting(true);
    setFormError(null);
    try {
      const session = await getOrCreateSession();
      onStartInterview(session);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to start interview.');
    } finally {
      setIsStarting(false);
    }
  };

  const handleCopyLink = async () => {
    if (isCopying || isStarting || isLoading) return;
    setIsCopying(true);
    setFormError(null);
    try {
      const session = await getOrCreateSession();
      const inviteUrl = `${window.location.origin}/interview/${session.id}`;
      await navigator.clipboard.writeText(inviteUrl);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2500);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to generate invite link.');
    } finally {
      setIsCopying(false);
    }
  };

  const fillSampleJob = () => {
    setFormError(null);
    setJobTitle('Senior Full Stack Engineer');
    setCompanyName('Google');
    setExperienceLevel('senior');
    setJobDescription(
      'We are looking for a Senior Full Stack Engineer to lead architecture for our scalable web applications.\n\n' +
        'Core Requirements:\n' +
        '- 5+ years building modern React, TypeScript, and Node.js applications.\n' +
        '- Strong experience with Python (FastAPI/Django) and REST/GraphQL APIs.\n' +
        '- Expertise in PostgreSQL database optimization, indexing, and pgvector embeddings.\n' +
        '- Proficiency in Docker containerization and CI/CD pipelines.\n' +
        '- Strong architectural decision-making and pair programming communication.'
    );
  };

  const fillSampleCandidates = () => {
    setFormError(null);
    setCandidates([
      {
        id: 'sample-1',
        name: 'Alex Morgan',
        cvFileName: 'Alex_Morgan_Senior_FullStack.pdf',
        fileSizeFormatted: '1.8 MB (Top Match)',
        cvRawText:
          'Alex Morgan - Senior Full Stack Engineer (8 years experience).\n' +
          'Tech Stack: React 19, TypeScript, Node.js, Python, FastAPI, PostgreSQL, Docker, Kubernetes, Redis, AWS.\n' +
          'Experience: Led engineering team building high-scale distributed SaaS platforms with real-time SSE & WebSockets. Optimized PostgreSQL queries by 45%. Strong CI/CD & microservices expertise.',
      },
      {
        id: 'sample-2',
        name: 'Sarah Chen',
        cvFileName: 'Sarah_Chen_Backend_Dev.pdf',
        fileSizeFormatted: '1.2 MB (Mid Match)',
        cvRawText:
          'Sarah Chen - Backend Software Engineer (4 years experience).\n' +
          'Tech Stack: Python, Django, FastAPI, PostgreSQL, AWS, Docker, REST APIs.\n' +
          'Experience: Designed data ingestion pipelines and REST endpoints. Solid database fundamentals. Limited frontend React experience.',
      },
      {
        id: 'sample-3',
        name: 'David Miller',
        cvFileName: 'David_Miller_Frontend_CV.pdf',
        fileSizeFormatted: '950 KB (Junior Match)',
        cvRawText:
          'David Miller - Junior Frontend Developer (2 years experience).\n' +
          'Tech Stack: React, JavaScript, HTML5, CSS3, Tailwind CSS, Vite, Figma.\n' +
          'Experience: Built landing pages and responsive UI components. Seeking to expand into backend & cloud infrastructure.',
      },
    ]);
  };

  const activeTopCandidate =
    topCandidate ||
    createdSession?.screeningResults?.find((r) => r.is_selected) ||
    createdSession?.screeningResults?.[0];

  const activeOtherCandidates =
    screeningResults.length > 0
      ? screeningResults.filter((r) => r.name !== activeTopCandidate?.name)
      : createdSession?.screeningResults?.filter((r) => r !== activeTopCandidate) || [];

  const activeCandidateFile = useMemo(() => {
    if (!activeTopCandidate) return null;
    const match = candidates.find(
      (c) =>
        c.name.toLowerCase() === activeTopCandidate.name.toLowerCase() ||
        c.cvFileName === activeTopCandidate.cv_filename
    );
    return match?.file || null;
  }, [activeTopCandidate, candidates]);

  const activePdfUrl = useMemo(() => {
    if (!activeCandidateFile) return null;
    if (
      activeCandidateFile.type === 'application/pdf' ||
      activeCandidateFile.name.toLowerCase().endsWith('.pdf')
    ) {
      return URL.createObjectURL(activeCandidateFile);
    }
    return null;
  }, [activeCandidateFile]);

  useEffect(() => {
    return () => {
      if (activePdfUrl) {
        URL.revokeObjectURL(activePdfUrl);
      }
    };
  }, [activePdfUrl]);

  return (
    <div className="w-full flex-1 flex flex-col gap-3 sm:gap-4 min-h-0">
      {/* 3-Step Wizard Progress Stepper */}
      <div className="w-full grid grid-cols-3 gap-1.5 sm:gap-2 rounded-xl border border-border/80 bg-card/90 p-1.5 sm:p-2 backdrop-blur shadow-xs shrink-0">
        {/* Step 1 Button */}
        <button
          type="button"
          onClick={() => goToStep(1)}
          className={`flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 rounded-lg px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium transition-all cursor-pointer select-none ${
            currentStep === 1
              ? 'bg-primary text-primary-foreground shadow-sm font-semibold'
              : 'text-foreground hover:bg-accent/60 hover:text-foreground'
          }`}
        >
          <div
            className={`flex h-5 w-5 sm:h-6 sm:w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold select-none ${
              currentStep === 1
                ? 'bg-primary-foreground text-primary'
                : jobTitle.trim() && jobDescription.trim()
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : 'bg-muted text-muted-foreground'
            }`}
          >
            {jobTitle.trim() && jobDescription.trim() && currentStep !== 1 ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              '1'
            )}
          </div>
          <span className="truncate hidden sm:inline font-medium">{t.form.step1Title}</span>
          <span className="truncate sm:hidden font-medium">Job</span>
        </button>

        {/* Step 2 Button */}
        <button
          type="button"
          onClick={() => {
            if (jobTitle.trim() && jobDescription.trim()) {
              goToStep(2);
            } else {
              setFormError(t.form.validationError);
            }
          }}
          className={`flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 rounded-lg px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium transition-all cursor-pointer select-none ${
            currentStep === 2
              ? 'bg-primary text-primary-foreground shadow-sm font-semibold'
              : 'text-foreground hover:bg-accent/60 hover:text-foreground'
          }`}
        >
          <div
            className={`flex h-5 w-5 sm:h-6 sm:w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold select-none ${
              currentStep === 2
                ? 'bg-primary-foreground text-primary'
                : currentStep > 2 && candidates.length > 0
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : 'bg-muted text-muted-foreground'
            }`}
          >
            {currentStep > 2 && candidates.length > 0 ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              '2'
            )}
          </div>
          <span className="truncate hidden sm:inline font-medium">{t.form.step2Title}</span>
          <span className="truncate sm:hidden font-medium">CVs</span>
        </button>

        {/* Step 3 Button */}
        <button
          type="button"
          disabled={!activeTopCandidate && !createdSession}
          onClick={() => {
            if (activeTopCandidate || createdSession) goToStep(3);
          }}
          className={`flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 rounded-lg px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium transition-all select-none ${
            !activeTopCandidate && !createdSession
              ? 'opacity-40 cursor-not-allowed text-muted-foreground'
              : currentStep === 3
                ? 'bg-primary text-primary-foreground shadow-sm font-semibold cursor-pointer'
                : 'text-foreground hover:bg-accent/60 hover:text-foreground cursor-pointer'
          }`}
        >
          <div
            className={`flex h-5 w-5 sm:h-6 sm:w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
              currentStep === 3
                ? 'bg-amber-400 text-amber-950 shadow-2xs'
                : activeTopCandidate || createdSession
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                  : 'bg-muted text-muted-foreground border border-border/50'
            }`}
          >
            {activeTopCandidate || createdSession ? (
              <Trophy
                className={`h-3.5 w-3.5 ${
                  currentStep === 3
                    ? 'text-amber-950 fill-amber-950'
                    : 'text-amber-400 fill-amber-400/40'
                }`}
              />
            ) : (
              '3'
            )}
          </div>
          <span className="truncate hidden sm:inline font-medium">{t.form.step3Title}</span>
          <span className="truncate sm:hidden font-medium">Selection</span>
        </button>
      </div>

      {/* STEP 1: JOB SPECIFICATION */}
      {currentStep === 1 && (
        <Card className="w-full flex-1 flex flex-col border-border bg-card shadow-xs min-h-0">
          <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-3 shrink-0">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-xl bg-blue-500/15 text-blue-500 dark:text-blue-400 border border-blue-500/30 shadow-2xs">
                  <Briefcase className="h-4 w-4 sm:h-4.5 sm:w-4.5" />
                </div>
                <div className="min-w-0">
                  <CardTitle className="text-base sm:text-lg font-bold truncate">
                    {t.form.step1Title}
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground mt-0.5">
                    {t.form.step1Subtitle}
                  </CardDescription>
                </div>
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={fillSampleJob}
                className="h-8 text-xs font-medium text-foreground hover:bg-accent hover:border-border shrink-0 px-2.5 sm:px-3 shadow-2xs cursor-pointer"
              >
                <Sparkles className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
                <span>{t.form.fillJobSample}</span>
              </Button>
            </div>
          </CardHeader>

          <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0 flex-1 flex flex-col min-h-0">
            <form
              onSubmit={handleNextStep1}
              className="flex-1 flex flex-col justify-between gap-4 min-h-0"
            >
              {formError && (
                <div className="flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive shrink-0">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Top Row: Job Title, Company, Seniority Level (3 columns on desktop) */}
              <div className="grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-3 shrink-0">
                <div className="space-y-1.5">
                  <Label
                    htmlFor="jobTitle"
                    className="flex items-center gap-1.5 text-xs sm:text-sm"
                  >
                    <Briefcase className="h-3.5 w-3.5 text-muted-foreground" />
                    {t.form.jobTitleLabel} <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="jobTitle"
                    placeholder={t.form.jobTitlePlaceholder}
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    required
                    className="h-9 sm:h-10 text-sm"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label
                    htmlFor="companyName"
                    className="flex items-center gap-1.5 text-xs sm:text-sm"
                  >
                    <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
                    {t.form.companyLabel}
                  </Label>
                  <Input
                    id="companyName"
                    placeholder={t.form.companyPlaceholder}
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="h-9 sm:h-10 text-sm"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label
                    htmlFor="experienceLevel"
                    className="flex items-center gap-1.5 text-xs sm:text-sm"
                  >
                    <FileSpreadsheet className="h-3.5 w-3.5 text-muted-foreground" />
                    {t.form.seniorityLabel}
                  </Label>
                  <Select
                    value={experienceLevel}
                    onValueChange={(val) => setExperienceLevel(val as ExperienceLevel)}
                  >
                    <SelectTrigger id="experienceLevel" className="h-9 sm:h-10 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="entry">{t.form.seniorityEntry}</SelectItem>
                      <SelectItem value="mid">{t.form.seniorityMid}</SelectItem>
                      <SelectItem value="senior">{t.form.senioritySenior}</SelectItem>
                      <SelectItem value="lead">{t.form.seniorityLead}</SelectItem>
                      <SelectItem value="executive">{t.form.seniorityExecutive}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Job Description / Requirements (Fullscreen flex growth) */}
              <div className="space-y-1.5 flex-1 flex flex-col min-h-0">
                <Label
                  htmlFor="jobDescription"
                  className="flex items-center gap-1.5 text-xs sm:text-sm shrink-0"
                >
                  {t.form.jobDescLabel} <span className="text-destructive">*</span>
                </Label>
                <Textarea
                  id="jobDescription"
                  placeholder={t.form.jobDescPlaceholder}
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  className="flex-1 w-full min-h-[220px] sm:min-h-[280px] lg:min-h-[340px] resize-y text-sm leading-relaxed"
                  required
                />
              </div>

              {/* Navigation Button */}
              <div className="pt-2 shrink-0">
                <Button
                  type="submit"
                  size="lg"
                  className="w-full gap-2 text-sm sm:text-base font-semibold h-11 sm:h-12 cursor-pointer shadow-sm"
                >
                  <span>{t.form.nextStep}</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* STEP 2: CANDIDATE POOL & CVs */}
      {currentStep === 2 && (
        <Card className="w-full flex-1 flex flex-col border-border bg-card shadow-xs min-h-0">
          <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-3 shrink-0">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-500 dark:text-indigo-400 border border-indigo-500/30 shadow-2xs">
                  <Users className="h-4 w-4 sm:h-4.5 sm:w-4.5" />
                </div>
                <div className="min-w-0">
                  <CardTitle className="text-base sm:text-lg font-bold truncate">
                    {t.form.step2Title}
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground mt-0.5">
                    {t.form.step2Subtitle}
                  </CardDescription>
                </div>
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={fillSampleCandidates}
                className="h-8 text-xs font-medium text-foreground hover:bg-accent hover:border-border shrink-0 px-2.5 sm:px-3 shadow-2xs cursor-pointer"
              >
                <Sparkles className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
                <span>{t.form.loadSample}</span>
              </Button>
            </div>
          </CardHeader>

          <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0 flex-1 flex flex-col min-h-0">
            <form
              onSubmit={handleStep2Screen}
              className="flex-1 flex flex-col justify-between gap-4 min-h-0"
            >
              {formError && (
                <div className="flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive shrink-0">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="flex-1 flex flex-col gap-3 min-h-0">
                {/* Job Summary Banner */}
                <div className="flex items-center justify-between rounded-lg border border-border/80 bg-muted/40 p-2.5 px-3.5 text-xs shrink-0">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-semibold text-foreground truncate">{jobTitle}</span>
                    {companyName && (
                      <span className="text-muted-foreground truncate hidden sm:inline">
                        at {companyName}
                      </span>
                    )}
                  </div>
                  <Badge variant="outline" className="text-[10px] capitalize shrink-0">
                    {experienceLevel}
                  </Badge>
                </div>

                {/* Multi-CV Upload Dropzone & Queue */}
                <div className="flex-1 flex flex-col min-h-0">
                  <CVUploader
                    candidates={candidates}
                    onAddFiles={handleAddFiles}
                    onRemoveCandidate={handleRemoveCandidate}
                    onUpdateCandidateName={handleUpdateCandidateName}
                  />
                </div>
              </div>

              {/* Step 2 Actions */}
              <div className="pt-3 shrink-0 flex flex-col-reverse sm:flex-row items-stretch justify-between gap-2.5">
                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  onClick={() => goToStep(1)}
                  className="w-full sm:w-auto gap-2 text-sm font-semibold h-11 sm:h-12 px-5 cursor-pointer"
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>{t.form.prevStep}</span>
                </Button>

                <Button
                  type="submit"
                  disabled={isScreening || candidates.length === 0}
                  size="lg"
                  className="w-full sm:flex-1 gap-2 text-sm sm:text-base font-semibold h-11 sm:h-12 cursor-pointer shadow-sm"
                >
                  {isScreening ? (
                    <div className="flex items-center gap-2">
                      <ThinkingOrb state="working" size={20} />
                      <span>{t.form.generatingButton}</span>
                    </div>
                  ) : (
                    <>
                      <span>{t.form.screenAndReview}</span>
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* STEP 3: AI SCREENING SELECTION & INVITATION HUB */}
      {currentStep === 3 && activeTopCandidate && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 flex-1 w-full min-h-0 items-stretch">
          {/* Left Column (5 cols): Selection Card with Bottom Navigation */}
          <div className="lg:col-span-5 flex flex-col gap-4 min-h-0">
            <Card className="border-border bg-card shadow-xs flex-1 flex flex-col min-h-0">
              <CardContent className="p-4 sm:p-6 flex-1 flex flex-col justify-between space-y-4 min-h-0 overflow-y-auto">
                <div className="space-y-4">
                  {formError && (
                    <div className="flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive shrink-0">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>{formError}</span>
                    </div>
                  )}

                  {/* Candidate Identity Hero */}
                  <div className="flex items-start justify-between gap-3 border-b border-border/60 pb-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground font-bold text-base shadow-sm">
                        {activeTopCandidate.name.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-base sm:text-lg font-bold text-foreground truncate">
                            {activeTopCandidate.name}
                          </h3>
                          <Badge className="bg-primary hover:bg-primary text-[10px] uppercase font-bold tracking-wider px-1.5 h-4.5 select-none">
                            {t.form.selectedBadge}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">
                          {jobTitle} • {companyName || 'Technical Role'}
                        </p>
                      </div>
                    </div>

                    <Badge
                      variant="outline"
                      className="bg-emerald-500/15 text-emerald-400 border-emerald-500/40 text-xs sm:text-sm font-bold font-mono px-2.5 py-0.5 shrink-0 select-none"
                    >
                      {activeTopCandidate.match_score}% Match
                    </Badge>
                  </div>

                  {/* Executive Screening Summary */}
                  <div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1.5">
                      Executive AI Screening Summary
                    </span>
                    <div className="rounded-lg bg-muted/40 p-3.5 border border-border/50 text-xs text-foreground leading-relaxed">
                      {activeTopCandidate.summary}
                    </div>
                  </div>

                  {/* Other Evaluated Applicants Pool */}
                  {activeOtherCandidates.length > 0 && (
                    <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-2.5">
                      <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <Trophy className="h-3.5 w-3.5 text-amber-500" />
                          <span>
                            {t.form.otherApplicants} ({activeOtherCandidates.length})
                          </span>
                        </div>
                        <span className="text-[10px] text-muted-foreground/80">
                          Click to switch
                        </span>
                      </div>

                      <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                        {activeOtherCandidates.map((cand, idx) => (
                          <div
                            key={idx}
                            onClick={() => handleSelectCandidate(cand)}
                            className="group flex items-center justify-between rounded-lg border border-border/70 bg-card hover:bg-accent hover:border-border p-2.5 px-3 text-xs transition-all cursor-pointer select-none gap-2"
                          >
                            <div className="flex items-center gap-2.5 min-w-0 flex-1">
                              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-mono font-bold text-muted-foreground group-hover:bg-primary/20 group-hover:text-primary transition-colors">
                                #{idx + 2}
                              </span>
                              <div className="min-w-0 flex-1 pr-1">
                                <span className="font-semibold text-foreground group-hover:text-foreground transition-colors block truncate select-none">
                                  {cand.name}
                                </span>
                                <span className="text-[11px] text-muted-foreground transition-colors truncate block select-none">
                                  {cand.strengths?.[0] || 'Applicant profile'}
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <Badge
                                variant="outline"
                                className="bg-emerald-500/10 group-hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-[11px] font-mono select-none transition-colors px-1.5 py-0.5"
                              >
                                {cand.match_score}% Match
                              </Badge>
                              <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Direct Invite Link */}
                  <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-foreground select-none">
                        Direct Invite Link
                      </span>
                      <span className="text-[10px] text-muted-foreground select-none">
                        Share with candidate
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Input
                        readOnly
                        value={
                          createdSession
                            ? `${window.location.origin}/interview/${createdSession.id}`
                            : `${window.location.origin}/interview/invite-link`
                        }
                        className="h-8.5 text-xs font-mono bg-background text-muted-foreground select-all"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleCopyLink}
                        disabled={isCopying || isStarting || isLoading}
                        className="h-8.5 px-3 gap-1.5 text-xs shrink-0 cursor-pointer shadow-2xs min-w-[70px] select-none"
                      >
                        {isCopying ? (
                          <div className="flex items-center gap-1.5">
                            <ThinkingOrb state="connecting" size={20} />
                            <span>Generating...</span>
                          </div>
                        ) : isCopied ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-500" />
                            <span className="text-emerald-500 font-medium">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            <span>Copy</span>
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Navigation Actions (Bottom bar matching Step 1 & 2 pattern) */}
                <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-3 pt-4 border-t border-border mt-4 shrink-0">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => goToStep(2)}
                    disabled={isStarting || isCopying || isLoading}
                    className="w-full sm:w-auto gap-2 text-xs sm:text-sm h-10 cursor-pointer shadow-2xs select-none"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    <span>{t.form.reviseCandidates}</span>
                  </Button>

                  <Button
                    type="button"
                    onClick={handleStartLiveInterview}
                    disabled={isStarting || isCopying || isLoading}
                    size="lg"
                    className="w-full sm:flex-1 gap-2 text-sm sm:text-base font-semibold h-11 sm:h-12 cursor-pointer shadow-sm select-none"
                  >
                    {isStarting ? (
                      <div className="flex items-center gap-2">
                        <ThinkingOrb state="working" size={20} />
                        <span>{t.form.generatingButton}</span>
                      </div>
                    ) : (
                      <>
                        <span>{t.form.startInterviewNow}</span>
                        <ExternalLink className="h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column (7 cols): Separate Dedicated High-Resolution Document Reader */}
          <div className="lg:col-span-7 flex flex-col min-h-0">
            <div className="rounded-xl border border-border bg-card shadow-xs overflow-hidden flex flex-col flex-1 h-full min-h-[500px] lg:min-h-0">
              {/* Document Header Ribbon */}
              <div className="flex items-center justify-between p-3.5 px-4 border-b border-border/80 bg-muted/40 shrink-0">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-500/15 text-blue-400 border border-blue-500/30">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-xs sm:text-sm font-bold text-foreground truncate">
                      {activeTopCandidate.cv_filename ||
                        `${activeTopCandidate.name} - Candidate Resume`}
                    </h4>
                    <p className="text-[10px] text-muted-foreground truncate">
                      {activePdfUrl ? 'Live Interactive PDF Document' : 'Parsed Resume Profile'}
                    </p>
                  </div>
                </div>

                {activePdfUrl && (
                  <a
                    href={activePdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-500 hover:text-blue-400 hover:underline px-2.5 py-1.5 rounded-md hover:bg-blue-500/10 transition-colors cursor-pointer select-none"
                    title="Open in full browser tab"
                  >
                    <span>Full Tab</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>

              {/* Document Reader Frame */}
              <div className="flex-1 overflow-hidden bg-zinc-950/20">
                {activePdfUrl ? (
                  <iframe
                    src={`${activePdfUrl}#navpanes=0&pagemode=none&toolbar=1&view=FitH`}
                    title={`${activeTopCandidate.name} CV Document`}
                    className="w-full h-full border-none bg-white dark:bg-zinc-900 rounded-b-xl"
                  />
                ) : (
                  <div className="p-5 sm:p-6 h-full overflow-y-auto space-y-5 select-text text-card-foreground">
                    <div className="border-b border-border/60 pb-4 flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-bold text-foreground">
                          {activeTopCandidate.name}
                        </h3>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {jobTitle} • {companyName || 'Technical Applicant Profile'}
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className="bg-emerald-500/15 text-emerald-400 border-emerald-500/40 font-mono text-xs font-semibold px-2.5 py-0.5 select-none"
                      >
                        {activeTopCandidate.match_score}% Match
                      </Badge>
                    </div>

                    <div className="space-y-1.5">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Executive Screening Evaluation
                      </span>
                      <p className="text-xs text-foreground leading-relaxed bg-muted/30 p-3.5 rounded-lg border border-border/60">
                        {activeTopCandidate.summary}
                      </p>
                    </div>

                    <div className="space-y-2 pt-1">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Extracted Resume Content
                      </span>
                      <div className="rounded-lg bg-muted/40 p-4 text-xs text-foreground leading-relaxed whitespace-pre-wrap font-sans border border-border/60 shadow-inner">
                        {activeTopCandidate.cv_raw_text || 'No raw text available.'}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
