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

export interface InterviewSession {
  id: string;
  jobTitle: string;
  companyName?: string;
  jobDescription: string;
  experienceLevel: ExperienceLevel;
  candidateName: string;
  cvFileName?: string;
  cvSummary?: string;
  cvSkills?: string[];
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
  candidateName: string;
  cvFile?: File | null;
  cvFileName?: string;
  cvRawText?: string;
}
