import {
  CreateInterviewInput,
  InterviewSession,
  ChatMessage,
  ExperienceLevel,
  InterviewStatus,
  CandidateScreeningResult,
  CandidateScreeningResponse,
} from '@/types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Cleanup legacy localStorage tokens if present
try {
  localStorage.removeItem('ai_interviewer_jwt_token');
} catch {
  // ignore in non-browser environments
}

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export async function apiLogin(usernameOrEmail: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username_or_email: usernameOrEmail,
      password: password,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed. Please check credentials.');
  }

  return res.json();
}

export async function apiLogout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch (err) {
    console.error('Logout request failed:', err);
  }
}

export async function apiGetMe(): Promise<UserProfile | null> {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      credentials: 'include',
    });

    if (!res.ok) {
      return null;
    }

    return await res.json();
  } catch {
    return null;
  }
}

export interface ExtractedDocumentItem {
  filename: string;
  file_type: string;
  raw_text: string;
  extracted_name?: string | null;
  file_size: number;
}

export async function apiExtractDocuments(
  files: File[]
): Promise<{ candidates: ExtractedDocumentItem[] }> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const res = await fetch(`${API_BASE}/cv/extract-batch`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to extract text from CV documents');
  }

  return res.json();
}

export async function apiScreenCandidates(
  input: CreateInterviewInput
): Promise<CandidateScreeningResponse> {
  const payload = {
    job_title: input.jobTitle,
    company_name: input.companyName || null,
    job_description: input.jobDescription,
    experience_level: input.experienceLevel,
    candidates: (input.candidates || []).map((c) => ({
      id: c.id || null,
      name: c.name,
      cv_filename: c.cvFileName || c.file?.name || null,
      cv_raw_text: c.cvRawText || null,
    })),
  };

  const res = await fetch(`${API_BASE}/interviews/screen`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to screen candidates');
  }

  return res.json();
}

interface ApiRawMessage {
  id: string;
  role: 'assistant' | 'user' | 'system';
  content: string;
  created_at: string;
  question_number?: number | null;
  feedback?: string | null;
}

interface ApiCandidateResponse {
  id: string;
  interview_id: string;
  name: string;
  cv_filename?: string | null;
  cv_raw_text?: string | null;
  match_score?: number | null;
  strengths?: string[] | null;
  summary?: string | null;
  is_selected: boolean;
  created_at: string;
}

interface ApiInterviewResponse {
  id: string;
  job_title: string;
  company_name: string | null;
  job_description: string;
  experience_level: ExperienceLevel;
  candidate_name: string;
  cv_filename: string | null;
  cv_raw_text?: string | null;
  candidates?: ApiCandidateResponse[];
  candidates_pool?: Array<{ name: string; cv_filename?: string; cv_raw_text?: string }> | null;
  screening_results?: CandidateScreeningResult[] | null;
  status: InterviewStatus;
  active_question_number?: number | null;
  active_question_text?: string | null;
  active_question_status?: string | null;
  topics_plan?: string[] | null;
  assessed_topics?: string[] | null;
  time_limit_minutes?: number | null;
  language?: string;
  conversation_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export async function apiListInterviews(ids?: string[]): Promise<InterviewSession[]> {
  try {
    let url = `${API_BASE}/interviews`;
    if (ids && ids.length > 0) {
      url += `?ids=${encodeURIComponent(ids.join(','))}`;
    }
    const res = await fetch(url, {
      credentials: 'include',
    });
    if (!res.ok) {
      throw new Error(`Failed to list interviews: ${res.statusText}`);
    }
    const data: ApiInterviewResponse[] = await res.json();
    return data.map((item) => ({
      id: item.id,
      jobTitle: item.job_title,
      companyName: item.company_name || undefined,
      jobDescription: item.job_description,
      experienceLevel: item.experience_level,
      candidateName: item.candidate_name,
      cvFileName: item.cv_filename || undefined,
      cvRawText: item.cv_raw_text || undefined,
      candidatesPool:
        item.candidates_pool ||
        item.candidates?.map((c) => ({
          name: c.name,
          cvFileName: c.cv_filename || undefined,
          cvRawText: c.cv_raw_text || undefined,
        })),
      screeningResults: item.screening_results || undefined,
      status: item.status,
      activeQuestionNumber: item.active_question_number ?? undefined,
      activeQuestionText: item.active_question_text || undefined,
      activeQuestionStatus: item.active_question_status || undefined,
      topicsPlan: item.topics_plan || undefined,
      assessedTopics: item.assessed_topics || undefined,
      timeLimitMinutes: item.time_limit_minutes || undefined,
      language: item.language || 'en',
      conversationSummary: item.conversation_summary || undefined,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
      messages: [],
    }));
  } catch (error) {
    console.warn('Failed to list interviews from API:', error);
    return [];
  }
}

export async function apiCreateInterview(input: CreateInterviewInput): Promise<InterviewSession> {
  const payload = {
    job_title: input.jobTitle,
    company_name: input.companyName || null,
    job_description: input.jobDescription,
    experience_level: input.experienceLevel,
    candidate_name: input.candidateName || input.candidates?.[0]?.name || 'Candidate',
    cv_filename: input.cvFileName || input.candidates?.[0]?.cvFileName || null,
    cv_raw_text: input.cvRawText || input.candidates?.[0]?.cvRawText || null,
    time_limit_minutes: input.timeLimitMinutes || null,
    language: input.language || 'en',
    candidates: input.candidates?.map((c) => ({
      name: c.name,
      cv_filename: c.cvFileName || c.file?.name || null,
      cv_raw_text: c.cvRawText || null,
    })),
  };

  const res = await fetch(`${API_BASE}/interviews`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Failed to create interview: ${res.statusText}`);
  }

  const data: ApiInterviewResponse = await res.json();
  const msgRes = await fetch(`${API_BASE}/interviews/${data.id}/messages`, {
    credentials: 'include',
  });
  const rawMessages: ApiRawMessage[] = msgRes.ok ? await msgRes.json() : [];

  return {
    id: data.id,
    jobTitle: data.job_title,
    companyName: data.company_name || undefined,
    jobDescription: data.job_description,
    experienceLevel: data.experience_level,
    candidateName: data.candidate_name,
    cvFileName: data.cv_filename || undefined,
    cvRawText: data.cv_raw_text || undefined,
    candidatesPool:
      data.candidates_pool ||
      data.candidates?.map((c) => ({
        name: c.name,
        cvFileName: c.cv_filename || undefined,
        cvRawText: c.cv_raw_text || undefined,
      })),
    screeningResults: data.screening_results || undefined,
    status: data.status,
    activeQuestionNumber: data.active_question_number ?? undefined,
    activeQuestionText: data.active_question_text || undefined,
    activeQuestionStatus: data.active_question_status || undefined,
    topicsPlan: data.topics_plan || undefined,
    assessedTopics: data.assessed_topics || undefined,
    timeLimitMinutes: data.time_limit_minutes || undefined,
    language: data.language || 'en',
    conversationSummary: data.conversation_summary || undefined,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
    messages: rawMessages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      createdAt: m.created_at,
      timestamp: m.created_at,
      questionNumber: m.question_number ?? undefined,
      feedback: m.feedback ?? undefined,
    })),
  };
}

export async function apiGetInterview(id: string): Promise<InterviewSession | null> {
  try {
    const res = await fetch(`${API_BASE}/interviews/${id}`, {
      credentials: 'include',
    });
    if (!res.ok) return null;
    const data: ApiInterviewResponse = await res.json();

    const msgRes = await fetch(`${API_BASE}/interviews/${id}/messages`, {
      credentials: 'include',
    });
    const rawMessages: ApiRawMessage[] = msgRes.ok ? await msgRes.json() : [];

    return {
      id: data.id,
      jobTitle: data.job_title,
      companyName: data.company_name || undefined,
      jobDescription: data.job_description,
      experienceLevel: data.experience_level,
      candidateName: data.candidate_name,
      cvFileName: data.cv_filename || undefined,
      cvRawText: data.cv_raw_text || undefined,
      candidatesPool:
        data.candidates_pool ||
        data.candidates?.map((c) => ({
          name: c.name,
          cvFileName: c.cv_filename || undefined,
          cvRawText: c.cv_raw_text || undefined,
        })),
      screeningResults: data.screening_results || undefined,
      status: data.status,
      activeQuestionNumber: data.active_question_number ?? undefined,
      activeQuestionText: data.active_question_text || undefined,
      activeQuestionStatus: data.active_question_status || undefined,
      topicsPlan: data.topics_plan || undefined,
      assessedTopics: data.assessed_topics || undefined,
      timeLimitMinutes: data.time_limit_minutes || undefined,
      language: data.language || 'en',
      conversationSummary: data.conversation_summary || undefined,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
      messages: rawMessages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        createdAt: m.created_at,
        timestamp: m.created_at,
        questionNumber: m.question_number ?? undefined,
        feedback: m.feedback ?? undefined,
      })),
    };
  } catch (error) {
    console.error('Failed to get interview from backend:', error);
    return null;
  }
}

export async function apiSendMessage(
  interviewId: string,
  content: string
): Promise<{ message: ChatMessage; isComplete: boolean }> {
  const res = await fetch(`${API_BASE}/interviews/${interviewId}/chat`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });

  if (!res.ok) {
    throw new Error(`Failed to send message: ${res.statusText}`);
  }

  const data = await res.json();
  return {
    message: {
      id: data.message.id,
      role: data.message.role,
      content: data.message.content,
      createdAt: data.message.created_at,
      timestamp: data.message.created_at,
      questionNumber: data.message.question_number ?? undefined,
      feedback: data.message.feedback ?? undefined,
    },
    isComplete: data.is_complete,
  };
}

export async function apiStreamSendMessage(
  interviewId: string,
  content: string,
  onChunk: (chunk: string) => void,
  onComplete: (data: { isComplete: boolean; questionNumber?: number; messageId?: string }) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/interviews/${interviewId}/stream`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Failed to stream: ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let isInterviewComplete = false;
  let finalMsgId: string | undefined;
  let finalQNum: number | undefined;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('data: ')) {
        const jsonStr = trimmed.substring(6);
        try {
          const payload = JSON.parse(jsonStr);
          if (payload.is_complete) {
            isInterviewComplete = true;
          }
          if (payload.message_id) {
            finalMsgId = payload.message_id;
          }
          if (payload.next_question_number !== undefined) {
            finalQNum = payload.next_question_number;
          }

          const rawChunk = payload.chunk || '';
          if (rawChunk.includes('[INTERVIEW_COMPLETE]')) {
            isInterviewComplete = true;
          }
          const cleanChunk = rawChunk.replace(/\[INTERVIEW_COMPLETE\]/g, '');
          if (cleanChunk) {
            onChunk(cleanChunk);
          }

          if (payload.done) {
            isInterviewComplete = isInterviewComplete || Boolean(payload.is_complete);
            onComplete({
              isComplete: isInterviewComplete,
              questionNumber: finalQNum,
              messageId: finalMsgId || payload.message_id,
            });
          }
        } catch {
          // ignore partial JSON parse
        }
      }
    }
  }
}

export async function apiCompleteInterview(id: string): Promise<InterviewSession | null> {
  try {
    const res = await fetch(`${API_BASE}/interviews/${id}/complete`, {
      method: 'POST',
      credentials: 'include',
    });
    if (!res.ok) return null;
    return await apiGetInterview(id);
  } catch (error) {
    console.error('Failed to complete interview on backend:', error);
    return null;
  }
}

export async function apiDeleteInterview(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/interviews/${id}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    return res.ok;
  } catch (error) {
    console.error('Failed to delete interview from backend:', error);
    return false;
  }
}
