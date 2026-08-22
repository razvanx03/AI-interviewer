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

export async function apiScreenCandidates(
  input: CreateInterviewInput
): Promise<CandidateScreeningResponse> {
  const payload = {
    job_title: input.jobTitle,
    company_name: input.companyName || null,
    job_description: input.jobDescription,
    experience_level: input.experienceLevel,
    candidates: (input.candidates || []).map((c) => ({
      name: c.name,
      cv_filename: c.cvFileName || c.file?.name || null,
      cv_raw_text: c.cvRawText || null,
    })),
  };

  const res = await fetch(`${API_BASE}/interviews/screen`, {
    method: 'POST',
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
  created_at: string;
  updated_at: string;
}

export async function apiListInterviews(ids?: string[]): Promise<InterviewSession[]> {
  try {
    const url =
      ids && ids.length > 0
        ? `${API_BASE}/interviews?ids=${encodeURIComponent(ids.join(','))}`
        : `${API_BASE}/interviews`;
    const res = await fetch(url);
    if (!res.ok) return [];
    const list: ApiInterviewResponse[] = await res.json();
    return list.map((data) => ({
      id: data.id,
      jobTitle: data.job_title,
      companyName: data.company_name || undefined,
      jobDescription: data.job_description,
      experienceLevel: data.experience_level,
      candidateName: data.candidate_name,
      cvFileName: data.cv_filename || undefined,
      cvRawText: data.cv_raw_text || undefined,
      candidatesPool:
        data.candidates?.map((c) => ({
          name: c.name,
          cvFileName: c.cv_filename || undefined,
          cvRawText: c.cv_raw_text || undefined,
        })) ||
        data.candidates_pool?.map((c) => ({
          name: c.name,
          cvFileName: c.cv_filename,
          cvRawText: c.cv_raw_text,
        })),
      screeningResults:
        data.candidates?.map((c) => ({
          name: c.name,
          match_score: c.match_score ?? 0,
          strengths: c.strengths || [],
          summary: c.summary || '',
          is_selected: c.is_selected,
          cv_filename: c.cv_filename || undefined,
        })) ||
        data.screening_results ||
        undefined,
      status: data.status,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
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
    candidates: input.candidates?.map((c) => ({
      name: c.name,
      cv_filename: c.cvFileName || c.file?.name || null,
      cv_raw_text: c.cvRawText || null,
    })),
  };

  const res = await fetch(`${API_BASE}/interviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Failed to create interview: ${res.statusText}`);
  }

  const data: ApiInterviewResponse = await res.json();
  const msgRes = await fetch(`${API_BASE}/interviews/${data.id}/messages`);
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
      data.candidates?.map((c) => ({
        name: c.name,
        cvFileName: c.cv_filename || undefined,
        cvRawText: c.cv_raw_text || undefined,
      })) ||
      data.candidates_pool?.map((c) => ({
        name: c.name,
        cvFileName: c.cv_filename,
        cvRawText: c.cv_raw_text,
      })),
    screeningResults:
      data.candidates?.map((c) => ({
        name: c.name,
        match_score: c.match_score ?? 0,
        strengths: c.strengths || [],
        summary: c.summary || '',
        is_selected: c.is_selected,
        cv_filename: c.cv_filename || undefined,
      })) ||
      data.screening_results ||
      undefined,
    status: data.status,
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
    const res = await fetch(`${API_BASE}/interviews/${id}`);
    if (!res.ok) return null;
    const data: ApiInterviewResponse = await res.json();

    const msgRes = await fetch(`${API_BASE}/interviews/${id}/messages`);
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
        data.candidates?.map((c) => ({
          name: c.name,
          cvFileName: c.cv_filename || undefined,
          cvRawText: c.cv_raw_text || undefined,
        })) ||
        data.candidates_pool?.map((c) => ({
          name: c.name,
          cvFileName: c.cv_filename,
          cvRawText: c.cv_raw_text,
        })),
      screeningResults:
        data.candidates?.map((c) => ({
          name: c.name,
          match_score: c.match_score ?? 0,
          strengths: c.strengths || [],
          summary: c.summary || '',
          is_selected: c.is_selected,
          cv_filename: c.cv_filename || undefined,
        })) ||
        data.screening_results ||
        undefined,
      status: data.status,
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
    console.warn('API error, falling back to local store:', error);
    return null;
  }
}

export async function apiSendMessage(
  interviewId: string,
  content: string
): Promise<{ message: ChatMessage; isComplete: boolean }> {
  const res = await fetch(`${API_BASE}/interviews/${interviewId}/chat`, {
    method: 'POST',
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Failed to stream: ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

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
          if (payload.chunk) {
            onChunk(payload.chunk);
          }
          if (payload.done) {
            onComplete({
              isComplete: payload.is_complete,
              questionNumber: payload.question_number,
              messageId: payload.message_id,
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
    });
    return res.ok;
  } catch (error) {
    console.error('Failed to delete interview from backend:', error);
    return false;
  }
}

// ==============================================================================
// [DEV ONLY - TEMPORARY TESTING FUNCTION TO BE REMOVED LATER]
// ==============================================================================
export async function apiClearEntireDatabase(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/interviews/admin/clear-all`, {
      method: 'DELETE',
    });
    return res.ok;
  } catch (error) {
    console.error('Failed to clear entire database:', error);
    return false;
  }
}
