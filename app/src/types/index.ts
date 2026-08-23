export type ExperienceLevel = 'entry' | 'mid' | 'senior' | 'lead' | 'executive';

export type InterviewStatus = 'draft' | 'active' | 'completed';

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
}

export interface CandidateScreeningResult {
  name: string;
  match_score: number;
  strengths: string[];
  summary: string;
  is_selected: boolean;
  cv_filename?: string;
  cv_raw_text?: string;
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
}
