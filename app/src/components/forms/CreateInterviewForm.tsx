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
  GripVertical,
  Timer,
  Globe,
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
import { apiScreenCandidates, apiExtractDocuments } from '@/lib/api';

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

  // Step 3 Timer state: optional countdown timer in minutes
  const [enableTimer, setEnableTimer] = useState<boolean>(false);
  const [timerMinutes, setTimerMinutes] = useState<number>(15);

  // Step 3 Spoken Language state: strictly locked to 'en' or 'ro'
  const [interviewLanguage, setInterviewLanguage] = useState<'en' | 'ro'>('en');

  // Step 3 Document Viewer Tab state: 'pdf' (Interactive PDF) or 'text' (AI Extracted Text)
  const [activeDocViewTab, setActiveDocViewTab] = useState<'pdf' | 'text'>('pdf');

  // Step 3 Resizable Splitter state (50/50 default balance)
  const [splitRatio, setSplitRatio] = useState<number>(50); // 50% left, 50% right
  const [isDraggingSplitter, setIsDraggingSplitter] = useState<boolean>(false);
  const splitContainerRef = React.useRef<HTMLDivElement>(null);

  const handleMouseDownSplitter = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingSplitter(true);
  };

  useEffect(() => {
    if (!isDraggingSplitter) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!splitContainerRef.current) return;
      const rect = splitContainerRef.current.getBoundingClientRect();
      const relativeX = e.clientX - rect.left;
      const newPercent = (relativeX / rect.width) * 100;
      // Clamp between 25% and 75%
      const clamped = Math.max(25, Math.min(75, newPercent));
      setSplitRatio(clamped);
    };

    const handleMouseUp = () => {
      setIsDraggingSplitter(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingSplitter]);

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

  const handleAddFiles = async (files: File[]) => {
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
        cvRawText: '',
      };
    });

    setCandidates((prev) => [...prev, ...newItems]);

    // Asynchronously extract real document text and actual candidate names from files
    try {
      const res = await apiExtractDocuments(files);
      if (res?.candidates && res.candidates.length > 0) {
        setCandidates((prev) =>
          prev.map((c) => {
            const extracted = res.candidates.find(
              (item) => item.filename.toLowerCase() === (c.cvFileName || '').toLowerCase()
            );
            if (extracted) {
              const realName =
                (c.name === 'Candidate' || !c.name.trim()) && extracted.extracted_name
                  ? extracted.extracted_name
                  : c.name;
              return {
                ...c,
                name: realName,
                cvRawText: extracted.raw_text,
              };
            }
            return c;
          })
        );
      }
    } catch (err) {
      console.warn('Real-time document text extraction warning:', err);
    }
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

      // Sync names and raw text back to candidates state
      setCandidates((prev) =>
        prev.map((c) => {
          const match = res.screening_results.find(
            (r) => r.cv_filename === c.cvFileName || r.name.toLowerCase() === c.name.toLowerCase()
          );
          if (match) {
            return {
              ...c,
              name: match.name,
              cvRawText: match.cv_raw_text || c.cvRawText,
            };
          }
          return c;
        })
      );

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
        (c) =>
          c.name.toLowerCase() === activeWinner.name.toLowerCase() ||
          c.cvFileName === activeWinner.cv_filename
      );
      if (matchIdx >= 0) {
        const [winner] = orderedCandidates.splice(matchIdx, 1);
        orderedCandidates.unshift({
          ...winner,
          name: activeWinner.name,
          cvRawText: activeWinner.cv_raw_text || winner.cvRawText,
        });
      } else {
        orderedCandidates.unshift({
          id: Math.random().toString(36).substring(2, 9),
          name: activeWinner.name,
          cvFileName: activeWinner.cv_filename,
          cvRawText: activeWinner.cv_raw_text,
        });
      }
    }

    const session = await onCreateSession({
      jobTitle: jobTitle.trim(),
      companyName: companyName.trim() || undefined,
      jobDescription: jobDescription.trim(),
      experienceLevel,
      candidateName: activeWinner ? activeWinner.name : undefined,
      timeLimitMinutes: enableTimer ? timerMinutes : undefined,
      language: interviewLanguage,
      candidates: orderedCandidates,
    });
    setCreatedSession(session);
    return session;
  };

  const handleGenerateSession = async () => {
    if (isStarting || isCopying || isLoading) return;
    setIsStarting(true);
    setFormError(null);
    try {
      const session = await getOrCreateSession();
      const inviteUrl = `${window.location.origin}/interview/${session.id}`;
      try {
        await navigator.clipboard.writeText(inviteUrl);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2500);
      } catch {
        // clipboard auto-copy might fail if window not active
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to generate interview.');
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
      setFormError(err instanceof Error ? err.message : 'Failed to copy invite link.');
    } finally {
      setIsCopying(false);
    }
  };

  const fillSampleJob = () => {
    setFormError(null);
    setJobTitle('Backend Developer');
    setCompanyName('Agile Freaks');
    setExperienceLevel('mid');
    setJobDescription(
      'About the role:\n\n' +
        'As a backend developer, you will contribute to designing, implementing and operating a system that supports the product requested features.\n\n' +
        'We work with: Ruby on Rails, Dry-Rb, Sidekiq, Shoryuken, RSpec/minitest, AWS (S3/SQS/RDS/EKS, etc), Redis, Datadog\n\n' +
        'This is what we need from you:\n' +
        '- Experience with Ruby on Rails or another backend language and willingness to learn Rails\n' +
        '- Technical background (e.g., degree in Computer Science or equivalent experience)\n' +
        '- Understanding of the HTTP protocol\n' +
        '- Basic Git knowledge\n' +
        '- Knowledge of design patterns and SOLID principles\n' +
        '- Experience building APIs with GraphQL\n' +
        '- Experience with Event Sourcing\n' +
        '- Experience with Domain-Driven Design (DDD)\n' +
        '- Experience working in an agile environment\n' +
        '- Excellent communication skills in written and spoken English\n\n' +
        'What we offer:\n' +
        '- Collaboration type: CIM\n' +
        '- Fully remote option (based on experience level)\n' +
        '- We hide nothing! Full disclosure on company information\n' +
        '- Profit Sharing - we share all registered profit between the freaks, based on seniority and level of experience\n' +
        '- Craft Budget (personal budget to improve your craft, buy anything you need, software, hardware, books, conference tickets and such): $2500/year/person\n' +
        '- Access to our startup fund ($120,000) to implement your personal project\n' +
        '- Flexible working hours\n' +
        '- Holiday Bonus (1 salary/year)\n' +
        "- Mold your workplace through AFIP (Agile Freaks Improvement Process). Curious about AFIP? It's the best thing to make yourself heard\n\n" +
        'Salary range:\n' +
        'Brut: 16735 lei - 23600 lei\n\n' +
        'Applicants must be permanent residents in Romania or moving here from an EU country!\n\n' +
        'Locations: Sibiu (Fully Remote)'
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

  const allRankedCandidates =
    screeningResults.length > 0
      ? screeningResults
      : createdSession?.screeningResults || (topCandidate ? [topCandidate] : []);

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
        <div
          ref={splitContainerRef}
          className={`flex flex-col lg:flex-row flex-1 w-full min-h-0 items-stretch relative gap-4 lg:gap-0 ${
            isDraggingSplitter ? 'select-none cursor-col-resize' : ''
          }`}
        >
          {/* Left Column: Selection Card with Bottom Navigation */}
          <div
            className="w-full lg:flex-none flex flex-col gap-4 min-h-0 lg:pr-3"
            style={{ width: undefined }}
            // Apply dynamic width on desktop
            ref={(el) => {
              if (el && window.innerWidth >= 1024) {
                el.style.width = `${splitRatio}%`;
              } else if (el) {
                el.style.width = '100%';
              }
            }}
          >
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

                  {/* Top Candidates Leaderboard (All Ranked Candidates) */}
                  {allRankedCandidates.length > 0 && (
                    <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-2.5">
                      <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <Trophy className="h-3.5 w-3.5 text-amber-500" />
                          <span>
                            {t.form.otherApplicants} ({allRankedCandidates.length})
                          </span>
                        </div>
                        <span className="text-[10px] text-muted-foreground/80">
                          Click to select
                        </span>
                      </div>

                      <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                        {allRankedCandidates.map((cand, idx) => {
                          const isSelected =
                            cand.name.toLowerCase() === activeTopCandidate?.name.toLowerCase();
                          return (
                            <div
                              key={idx}
                              onClick={() => handleSelectCandidate(cand)}
                              className={`group flex items-center justify-between rounded-lg border p-2.5 px-3 text-xs transition-all cursor-pointer select-none gap-2 ${
                                isSelected
                                  ? 'border-primary/80 bg-primary/10 ring-1 ring-primary/30 shadow-2xs'
                                  : 'border-border/70 bg-card hover:bg-accent hover:border-border'
                              }`}
                            >
                              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                                <span
                                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-mono font-bold transition-colors ${
                                    isSelected
                                      ? 'bg-primary text-primary-foreground shadow-2xs'
                                      : 'bg-muted text-muted-foreground group-hover:bg-primary/20 group-hover:text-primary'
                                  }`}
                                >
                                  #{idx + 1}
                                </span>
                                <div className="min-w-0 flex-1 pr-1">
                                  <div className="flex items-center gap-1.5">
                                    <span
                                      className={`font-semibold transition-colors truncate select-none ${
                                        isSelected
                                          ? 'text-foreground font-bold'
                                          : 'text-foreground group-hover:text-foreground'
                                      }`}
                                    >
                                      {cand.name}
                                    </span>
                                    {isSelected && (
                                      <Badge className="bg-primary hover:bg-primary text-primary-foreground text-[9px] px-1.5 py-0 h-4 font-bold uppercase tracking-wider select-none">
                                        Selected
                                      </Badge>
                                    )}
                                  </div>
                                  <span className="text-[11px] text-muted-foreground transition-colors truncate block select-none">
                                    {cand.strengths?.[0] || 'Applicant profile'}
                                  </span>
                                </div>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                <Badge
                                  variant="outline"
                                  className={`text-[11px] font-mono select-none transition-colors px-1.5 py-0.5 ${
                                    isSelected
                                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50 font-bold'
                                      : 'bg-emerald-500/10 group-hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                                  }`}
                                >
                                  {cand.match_score}% Match
                                </Badge>
                                <ChevronRight
                                  className={`h-4 w-4 transition-colors ${
                                    isSelected
                                      ? 'text-primary'
                                      : 'text-muted-foreground group-hover:text-foreground'
                                  }`}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Interview Time Limit (Countdown Timer) */}
                  <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Timer className="h-4 w-4 text-primary" />
                        <div>
                          <div className="text-xs font-semibold text-foreground select-none">
                            Time Limit (Countdown Timer)
                          </div>
                          <p className="text-[10px] text-muted-foreground select-none">
                            {enableTimer
                              ? `Paced technical evaluation (${timerMinutes} min)`
                              : 'Untimed session (unconstrained duration)'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          role="switch"
                          aria-checked={enableTimer}
                          onClick={() => {
                            setEnableTimer((prev) => !prev);
                            setCreatedSession(null);
                          }}
                          className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                            enableTimer ? 'bg-primary' : 'bg-muted-foreground/30'
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-background shadow-lg ring-0 transition duration-200 ease-in-out ${
                              enableTimer ? 'translate-x-4' : 'translate-x-0'
                            }`}
                          />
                        </button>
                      </div>
                    </div>

                    {enableTimer && (
                      <div className="flex items-center justify-between gap-3 pt-2 border-t border-border/40">
                        <span className="text-xs text-muted-foreground select-none">
                          Allocated Duration:
                        </span>
                        <Select
                          value={String(timerMinutes)}
                          onValueChange={(val) => {
                            setTimerMinutes(Number(val));
                            setCreatedSession(null);
                          }}
                        >
                          <SelectTrigger className="w-[145px] h-8 text-xs font-medium bg-background border-border">
                            <SelectValue placeholder="Select duration" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="10">10 minutes</SelectItem>
                            <SelectItem value="15">15 minutes</SelectItem>
                            <SelectItem value="20">20 minutes</SelectItem>
                            <SelectItem value="25">25 minutes</SelectItem>
                            <SelectItem value="30">30 minutes</SelectItem>
                            <SelectItem value="40">40 minutes</SelectItem>
                            <SelectItem value="60">60 minutes</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>

                  {/* Interview Spoken Language */}
                  <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-2">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4 text-primary" />
                        <div>
                          <div className="text-xs font-semibold text-foreground select-none">
                            {t.form.interviewLanguageLabel}
                          </div>
                          <p className="text-[10px] text-muted-foreground select-none">
                            {interviewLanguage === 'ro'
                              ? 'Interviul se va desfășura 100% în limba Română'
                              : 'The interview will be conducted 100% in English'}
                          </p>
                        </div>
                      </div>
                      <Select
                        value={interviewLanguage}
                        onValueChange={(val: 'en' | 'ro') => {
                          setInterviewLanguage(val);
                          setCreatedSession(null);
                        }}
                      >
                        <SelectTrigger className="w-[145px] h-8 text-xs font-medium bg-background border-border">
                          <SelectValue placeholder="Select language" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en">English (EN)</SelectItem>
                          <SelectItem value="ro">Română (RO)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Direct Invite Link */}
                  <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-foreground select-none">
                        Direct Invite Link
                      </span>
                      {createdSession ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-500 select-none">
                          <CheckCircle2 className="h-3 w-3" />
                          Ready to share
                        </span>
                      ) : (
                        <span className="text-[10px] text-muted-foreground select-none">
                          Share with candidate
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Input
                        readOnly
                        value={
                          createdSession
                            ? `${window.location.origin}/interview/${createdSession.id}`
                            : 'Click "Generate Invitation Link" below to initialize session'
                        }
                        className={`h-8.5 text-xs font-mono select-all ${
                          createdSession
                            ? 'bg-background text-foreground font-semibold border-emerald-500/40'
                            : 'bg-muted/40 text-muted-foreground italic'
                        }`}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleCopyLink}
                        disabled={!createdSession || isCopying || isStarting || isLoading}
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

                  {!createdSession ? (
                    <Button
                      type="button"
                      onClick={handleGenerateSession}
                      disabled={isStarting || isCopying || isLoading}
                      size="lg"
                      className="w-full sm:flex-1 gap-2 text-sm font-semibold h-10 sm:h-11 cursor-pointer shadow-sm select-none"
                    >
                      {isStarting ? (
                        <div className="flex items-center gap-2">
                          <ThinkingOrb state="working" size={20} />
                          <span>Preparing AI Context & Link...</span>
                        </div>
                      ) : (
                        <>
                          <Sparkles className="h-4 w-4" />
                          <span>Generate Invitation Link</span>
                        </>
                      )}
                    </Button>
                  ) : (
                    <div className="flex items-center gap-2 w-full sm:flex-1">
                      <Button
                        type="button"
                        onClick={handleCopyLink}
                        size="lg"
                        className="flex-1 gap-2 text-sm font-semibold h-10 sm:h-11 cursor-pointer shadow-sm select-none"
                      >
                        {isCopied ? (
                          <>
                            <Check className="h-4 w-4 text-emerald-300" />
                            <span>Link Copied to Clipboard!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-4 w-4" />
                            <span>Copy Candidate Invite Link</span>
                          </>
                        )}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => onStartInterview(createdSession)}
                        size="lg"
                        className="h-10 sm:h-11 px-3 text-xs gap-1.5 cursor-pointer shadow-2xs select-none"
                        title="Observe Live Room as Admin (Read Only)"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        <span className="hidden sm:inline">Observe Room</span>
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Desktop Draggable Splitter Divider */}
          <div
            onMouseDown={handleMouseDownSplitter}
            className="hidden lg:flex w-4 items-center justify-center cursor-col-resize group z-20 shrink-0 select-none py-2 hover:opacity-100"
            title="Drag left or right to resize panels"
          >
            <div
              className={`h-full w-[2px] rounded-full transition-all flex items-center justify-center ${
                isDraggingSplitter
                  ? 'bg-primary w-[3px]'
                  : 'bg-border/80 group-hover:bg-primary/70 group-hover:w-[3px]'
              }`}
            >
              <div
                className={`p-1 rounded-sm shadow-xs transition-all ${
                  isDraggingSplitter
                    ? 'bg-primary text-primary-foreground scale-110'
                    : 'bg-card border border-border text-muted-foreground group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary'
                }`}
              >
                <GripVertical className="h-3.5 w-3.5" />
              </div>
            </div>
          </div>

          {/* Right Column: Separate Dedicated High-Resolution Document Reader */}
          <div
            className="w-full lg:flex-none flex flex-col min-h-0 lg:pl-3"
            style={{ width: undefined }}
            ref={(el) => {
              if (el && window.innerWidth >= 1024) {
                el.style.width = `${100 - splitRatio}%`;
              } else if (el) {
                el.style.width = '100%';
              }
            }}
          >
            <div className="rounded-xl border border-border bg-card shadow-xs overflow-hidden flex flex-col flex-1 h-full min-h-[500px] lg:min-h-0 relative">
              {/* Transparent drag shield over iframe to prevent mouse capturing while dragging */}
              {isDraggingSplitter && (
                <div className="absolute inset-0 z-30 bg-transparent cursor-col-resize select-none" />
              )}
              {/* Document Header Ribbon */}
              <div className="flex items-center justify-between p-3 sm:p-3.5 px-4 border-b border-border/80 bg-muted/40 shrink-0 gap-2 flex-wrap">
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
                      {activePdfUrl ? 'Live Document & AI Ingestion' : 'Parsed Resume Profile'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  {/* Toggle between PDF & AI Extracted Text */}
                  {activePdfUrl && (
                    <div className="flex items-center rounded-lg border border-border bg-background/80 p-0.5 text-xs font-medium">
                      <button
                        type="button"
                        onClick={() => setActiveDocViewTab('pdf')}
                        className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer select-none text-xs ${
                          activeDocViewTab === 'pdf'
                            ? 'bg-primary text-primary-foreground font-semibold shadow-2xs'
                            : 'text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        PDF View
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveDocViewTab('text')}
                        className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer select-none text-xs ${
                          activeDocViewTab === 'text'
                            ? 'bg-primary text-primary-foreground font-semibold shadow-2xs'
                            : 'text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        AI Extracted Text
                      </button>
                    </div>
                  )}

                  {activePdfUrl && (
                    <a
                      href={activePdfUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-medium text-blue-500 hover:text-blue-400 hover:underline px-2 py-1 rounded-md hover:bg-blue-500/10 transition-colors cursor-pointer select-none"
                      title="Open in full browser tab"
                    >
                      <span>Full Tab</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </div>

              {/* Document Reader Frame */}
              <div className="flex-1 overflow-hidden bg-zinc-950/20">
                {activePdfUrl && activeDocViewTab === 'pdf' ? (
                  <iframe
                    src={`${activePdfUrl}#navpanes=0&pagemode=none&toolbar=1&view=FitH`}
                    title={`${activeTopCandidate.name} CV Document`}
                    className="w-full h-full border-none bg-white dark:bg-zinc-900 rounded-b-xl"
                  />
                ) : (
                  <div className="p-5 sm:p-6 h-full overflow-y-auto space-y-5 select-text text-card-foreground">
                    <div className="border-b border-border/60 pb-4 flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-bold text-foreground">
                            {activeTopCandidate.name}
                          </h3>
                          <Badge className="bg-primary/20 text-primary border-primary/30 text-[10px] font-mono">
                            AI Extracted Profile
                          </Badge>
                        </div>
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
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                          Exact Extracted Resume Text (Ingested by AI)
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {activeTopCandidate.cv_raw_text
                            ? `${activeTopCandidate.cv_raw_text.length} characters extracted`
                            : '0 characters'}
                        </span>
                      </div>
                      <div className="rounded-lg bg-muted/40 p-4 text-xs text-foreground leading-relaxed whitespace-pre-wrap font-mono border border-border/60 shadow-inner max-h-[500px] overflow-y-auto">
                        {activeTopCandidate.cv_raw_text ||
                          'No raw text extracted for this profile.'}
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
