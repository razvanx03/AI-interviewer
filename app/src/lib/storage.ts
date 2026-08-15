import { InterviewSession, CreateInterviewInput, ChatMessage } from '@/types';

const STORAGE_KEY = 'ai_interviewer_sessions_v1';

export function getStoredInterviews(): InterviewSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (err) {
    console.error('Failed to parse interviews from localStorage:', err);
    return [];
  }
}

export function getInterviewById(id: string): InterviewSession | null {
  const sessions = getStoredInterviews();
  return sessions.find((s) => s.id === id) || null;
}

export function saveInterview(session: InterviewSession): void {
  try {
    const sessions = getStoredInterviews();
    const index = sessions.findIndex((s) => s.id === session.id);
    if (index >= 0) {
      sessions[index] = session;
    } else {
      sessions.unshift(session);
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (err) {
    console.error('Failed to save interview to localStorage:', err);
  }
}

export function createNewInterviewSession(input: CreateInterviewInput): InterviewSession {
  // Generate random 8-character ID
  const id = Math.random().toString(36).substring(2, 10);
  const now = new Date().toISOString();

  // Mock extracted CV skills if file or filename exists
  const mockSkills = input.cvFileName
    ? ['React', 'TypeScript', 'Node.js', 'System Architecture', 'REST APIs', 'Cloud/Docker']
    : ['Technical Communication', 'Problem Solving', 'Software Lifecycle'];

  const introText = `Hello ${input.candidateName || 'Candidate'}! I am your AI interviewer for the **${input.jobTitle}** role${input.companyName ? ` at **${input.companyName}**` : ''}.\n\nI've reviewed the job requirements and your resume. When you're ready, could you briefly introduce yourself and share what projects or experience best highlight your readiness for this position?`;

  const initialMessage: ChatMessage = {
    id: Math.random().toString(36).substring(2, 9),
    role: 'assistant',
    content: introText,
    timestamp: now,
    questionNumber: 1,
  };

  const newSession: InterviewSession = {
    id,
    jobTitle: input.jobTitle,
    companyName: input.companyName,
    jobDescription: input.jobDescription,
    experienceLevel: input.experienceLevel,
    candidateName: input.candidateName || 'Candidate',
    cvFileName: input.cvFileName,
    cvSummary: input.cvFileName
      ? 'Experienced Software Engineer with a solid background in building scalable web applications and distributed backends.'
      : undefined,
    cvSkills: mockSkills,
    status: 'active',
    createdAt: now,
    updatedAt: now,
    messages: [initialMessage],
  };

  saveInterview(newSession);
  return newSession;
}
