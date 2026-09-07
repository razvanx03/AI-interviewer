export type ExperienceLevel = 'entry' | 'mid' | 'senior' | 'lead' | 'executive';

export type InterviewStatus = 'draft' | 'active' | 'finishing' | 'completed';

export interface ChatMessage {
  id: string;
  role: 'assistant' | 'user' | 'system';
  content: string;
  timestamp?: string;
  createdAt?: string;
  questionNumber?: number;
  feedback?: string;
}

export interface CandidateItem {
  id?: string;
  name: string;
  cvFileName?: string;
  cvRawText?: string;
  file?: File | null;
  fileSizeFormatted?: string;
  isExtracting?: boolean;
}

export interface CandidateScreeningResult {
  id?: string;
  name: string;
  match_score: number;
  strengths: string[];
  gaps?: string[];
  matched_chunks?: string[];
  summary: string;
  is_selected: boolean;
  cv_filename?: string;
  cv_raw_text?: string;
  experience_years?: number;
  timeline_summary?: string;
  tech_tenure?: Record<string, number>;
  work_history?: Array<{
    role?: string;
    interval?: string;
    duration_formatted?: string;
    duration_months?: number;
    technologies?: string[];
    is_work?: boolean;
  }>;
}

export interface CandidateScreeningResponse {
  top_candidate: CandidateScreeningResult;
  screening_results: CandidateScreeningResult[];
}

export interface InterviewSession {
  id: string;
  jobTitle: string;
  companyName?: string;
  jobDescription: string;
  experienceLevel: ExperienceLevel;
  candidateName: string;
  cvFileName?: string;
  cvRawText?: string;
  candidatesPool?: CandidateItem[];
  screeningResults?: CandidateScreeningResult[];
  status: InterviewStatus;
  activeQuestionNumber?: number | null;
  activeQuestionText?: string | null;
  activeQuestionStatus?: string;
  topicsPlan?: string[];
  assessedTopics?: string[];
  timeLimitMinutes?: number | null;
  language?: string;
  conversationSummary?: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  score?: number;
}

export interface CreateInterviewInput {
  jobTitle: string;
  companyName?: string;
  jobDescription: string;
  experienceLevel: ExperienceLevel;
  candidates?: CandidateItem[];
  candidateName?: string;
  cvFile?: File | null;
  cvFileName?: string;
  cvRawText?: string;
  timeLimitMinutes?: number | null;
  language?: string;
}
