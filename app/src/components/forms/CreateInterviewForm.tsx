import React, { useState } from 'react';
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
  Award,
  ChevronRight,
  ExternalLink,
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
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
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
  const [isCopied, setIsCopied] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const { t } = useLanguage();

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

  const handleNextStep1 = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobTitle.trim() || !jobDescription.trim()) {
      setFormError(t.form.validationError);
      return;
    }
    setFormError(null);
    setCurrentStep(2);
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
      setCurrentStep(3);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to screen candidates.');
    } finally {
      setIsScreening(false);
    }
  };

  // Helper to ensure database session is created only when needed (on Start or on Copy Link)
  const getOrCreateSession = async (): Promise<InterviewSession> => {
    if (createdSession) return createdSession;
    const session = await onCreateSession({
      jobTitle: jobTitle.trim(),
      companyName: companyName.trim() || undefined,
      jobDescription: jobDescription.trim(),
      experienceLevel,
      candidates,
    });
    setCreatedSession(session);
    return session;
  };

  const handleStartLiveInterview = async () => {
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
    setFormError(null);
    try {
      const session = await getOrCreateSession();
      const inviteUrl = `${window.location.origin}/interview/${session.id}`;
      navigator.clipboard.writeText(inviteUrl);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2500);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to generate invite link.');
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

  return (
    <div className="w-full space-y-4">
      {/* 3-Step Wizard Progress Stepper */}
      <div className="grid grid-cols-3 gap-1.5 sm:gap-2 rounded-xl border border-border bg-card/70 p-1.5 sm:p-2.5 backdrop-blur">
        {/* Step 1 Button */}
        <button
          type="button"
          onClick={() => setCurrentStep(1)}
          className={`flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 rounded-lg px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium transition-all cursor-pointer ${
            currentStep === 1
              ? 'bg-primary text-primary-foreground shadow-xs font-semibold'
              : 'text-muted-foreground hover:bg-accent/40 hover:text-foreground'
          }`}
        >
          <div
            className={`flex h-5 w-5 sm:h-6 sm:w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
              currentStep === 1
                ? 'bg-primary-foreground text-primary'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            {jobTitle.trim() && jobDescription.trim() ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              '1'
            )}
          </div>
          <span className="truncate hidden sm:inline">{t.form.step1Title}</span>
          <span className="truncate sm:hidden">1. Job</span>
        </button>

        {/* Step 2 Button */}
        <button
          type="button"
          onClick={() => {
            if (jobTitle.trim() && jobDescription.trim()) {
              setCurrentStep(2);
            } else {
              setFormError(t.form.validationError);
            }
          }}
          className={`flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 rounded-lg px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium transition-all cursor-pointer ${
            currentStep === 2
              ? 'bg-primary text-primary-foreground shadow-xs font-semibold'
              : 'text-muted-foreground hover:bg-accent/40 hover:text-foreground'
          }`}
        >
          <div
            className={`flex h-5 w-5 sm:h-6 sm:w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
              currentStep === 2
                ? 'bg-primary-foreground text-primary'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            {candidates.length > 0 ? (
              <Badge variant="secondary" className="h-4 px-1 text-[10px] p-0 font-mono">
                {candidates.length}
              </Badge>
            ) : (
              '2'
            )}
          </div>
          <span className="truncate hidden sm:inline">{t.form.step2Title}</span>
          <span className="truncate sm:hidden">2. CVs</span>
        </button>

        {/* Step 3 Button */}
        <button
          type="button"
          disabled={!activeTopCandidate && !createdSession}
          onClick={() => {
            if (activeTopCandidate || createdSession) setCurrentStep(3);
          }}
          className={`flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 rounded-lg px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
            !activeTopCandidate && !createdSession
              ? 'opacity-40 cursor-not-allowed text-muted-foreground'
              : currentStep === 3
                ? 'bg-primary text-primary-foreground shadow-xs font-semibold cursor-pointer'
                : 'text-muted-foreground hover:bg-accent/40 hover:text-foreground cursor-pointer'
          }`}
        >
          <div
            className={`flex h-5 w-5 sm:h-6 sm:w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
              currentStep === 3
                ? 'bg-primary-foreground text-primary'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            {activeTopCandidate || createdSession ? <Trophy className="h-3.5 w-3.5" /> : '3'}
          </div>
          <span className="truncate hidden sm:inline">{t.form.step3Title}</span>
          <span className="truncate sm:hidden">3. Selection</span>
        </button>
      </div>

      {/* Main Wizard Card */}
      <Card className="w-full border-border bg-card shadow-xs">
        {/* STEP 1: JOB SPECIFICATION */}
        {currentStep === 1 && (
          <>
            <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Briefcase className="h-4 w-4" />
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
                  className="h-8 text-xs font-medium text-foreground hover:text-primary hover:border-primary/50 shrink-0 px-2.5 sm:px-3 shadow-2xs cursor-pointer"
                >
                  <Sparkles className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
                  <span>{t.form.fillJobSample}</span>
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0">
              <form onSubmit={handleNextStep1} className="space-y-4">
                {formError && (
                  <div className="flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{formError}</span>
                  </div>
                )}

                {/* Job Title & Company */}
                <div className="grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-2">
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
                </div>

                {/* Seniority Level */}
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

                {/* Job Description / Requirements */}
                <div className="space-y-1.5">
                  <Label
                    htmlFor="jobDescription"
                    className="flex items-center gap-1.5 text-xs sm:text-sm"
                  >
                    {t.form.jobDescLabel} <span className="text-destructive">*</span>
                  </Label>
                  <Textarea
                    id="jobDescription"
                    placeholder={t.form.jobDescPlaceholder}
                    rows={8}
                    value={jobDescription}
                    onChange={(e) => setJobDescription(e.target.value)}
                    className="min-h-[220px] sm:min-h-[260px] max-h-[440px] resize-y text-sm"
                    required
                  />
                </div>

                {/* Navigation Button */}
                <div className="pt-2">
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
          </>
        )}

        {/* STEP 2: CANDIDATE POOL & CVs */}
        {currentStep === 2 && (
          <>
            <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Users className="h-4 w-4" />
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
                  className="h-8 text-xs font-medium text-foreground hover:text-primary hover:border-primary/50 shrink-0 px-2.5 sm:px-3 shadow-2xs cursor-pointer"
                >
                  <Sparkles className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
                  <span>{t.form.loadSample}</span>
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0">
              <form onSubmit={handleStep2Screen} className="space-y-4">
                {formError && (
                  <div className="flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{formError}</span>
                  </div>
                )}

                {/* Job Summary Banner */}
                <div className="flex items-center justify-between rounded-lg border border-border/80 bg-muted/40 p-2.5 px-3.5 text-xs">
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
                <CVUploader
                  candidates={candidates}
                  onAddFiles={handleAddFiles}
                  onRemoveCandidate={handleRemoveCandidate}
                />

                {/* Step 2 Actions */}
                <div className="pt-3 flex flex-col-reverse sm:flex-row items-stretch justify-between gap-2.5">
                  <Button
                    type="button"
                    variant="outline"
                    size="lg"
                    onClick={() => setCurrentStep(1)}
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
          </>
        )}

        {/* STEP 3: AI SCREENING SELECTION & INVITATION HUB */}
        {currentStep === 3 && activeTopCandidate && (
          <>
            <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-4">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Trophy className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <CardTitle className="text-base sm:text-lg font-bold truncate">
                    {t.form.step3Title}
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground mt-0.5">
                    {t.form.step3Subtitle}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>

            <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0 space-y-4">
              {formError && (
                <div className="flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Winning Selected Candidate Card */}
              <div className="rounded-xl border-2 border-primary/50 bg-primary/5 p-4 sm:p-4.5 shadow-sm space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                      <Trophy className="h-4.5 w-4.5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm sm:text-base font-bold text-foreground">
                          {activeTopCandidate.name}
                        </h4>
                        <Badge className="bg-primary hover:bg-primary text-[10px] uppercase font-bold tracking-wider px-1.5 h-4.5">
                          {t.form.selectedBadge}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {activeTopCandidate.summary}
                      </p>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-base sm:text-lg font-extrabold text-primary">
                      {activeTopCandidate.match_score}%
                    </div>
                    <span className="text-[10px] text-muted-foreground uppercase font-semibold">
                      {t.screeningModal.matchScore}
                    </span>
                  </div>
                </div>

                {/* Match Progress Bar */}
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-700 ease-out"
                    style={{ width: `${activeTopCandidate.match_score}%` }}
                  />
                </div>

                {/* Identified Strengths */}
                {activeTopCandidate.strengths && activeTopCandidate.strengths.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-0.5">
                    {activeTopCandidate.strengths.map((str, i) => (
                      <Badge
                        key={i}
                        variant="secondary"
                        className="text-[11px] font-normal gap-1 bg-background/80 border border-border/60"
                      >
                        <CheckCircle2 className="h-2.5 w-2.5 text-emerald-500" />
                        {str}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              {/* Other Evaluated Candidates List */}
              {activeOtherCandidates.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground px-1">
                    <Award className="h-3.5 w-3.5" />
                    <span>
                      {t.form.otherApplicants} ({activeOtherCandidates.length})
                    </span>
                  </div>

                  <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    {activeOtherCandidates.map((cand, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between rounded-lg border border-border/70 bg-card/60 p-2 px-3 text-xs"
                      >
                        <div className="min-w-0 flex-1 pr-2">
                          <span className="font-medium text-foreground">{cand.name}</span>
                          <p className="text-[11px] text-muted-foreground truncate">
                            {cand.summary}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Badge variant="outline" className="text-[11px] font-mono">
                            {cand.match_score}%
                          </Badge>
                          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Shareable Link Box */}
              <div className="rounded-xl border border-border bg-muted/40 p-3 sm:p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-foreground">
                    Candidate Invite Link (Direct Access)
                  </span>
                  <span className="text-[10px] text-muted-foreground hidden sm:inline">
                    No login required
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    readOnly
                    value={
                      createdSession
                        ? `${window.location.origin}/interview/${createdSession.id}`
                        : `${window.location.origin}/interview/invite-link`
                    }
                    className="h-9 text-xs font-mono bg-background text-muted-foreground select-all"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleCopyLink}
                    className="h-9 gap-1.5 text-xs shrink-0 cursor-pointer shadow-2xs"
                  >
                    {isCopied ? (
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
                <p className="text-[11px] text-muted-foreground">{t.form.shareLinkTip}</p>
              </div>

              {/* Step 3 Action Navigation */}
              <div className="pt-2 flex flex-col-reverse sm:flex-row items-stretch justify-between gap-2.5">
                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  onClick={() => setCurrentStep(2)}
                  className="w-full sm:w-auto gap-2 text-sm font-semibold h-11 sm:h-12 px-5 cursor-pointer"
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span>{t.form.reviseCandidates}</span>
                </Button>

                <Button
                  type="button"
                  onClick={handleStartLiveInterview}
                  disabled={isStarting || isLoading}
                  size="lg"
                  className="w-full sm:flex-1 gap-2 text-sm sm:text-base font-semibold h-11 sm:h-12 cursor-pointer shadow-sm"
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
          </>
        )}
      </Card>
    </div>
  );
};
