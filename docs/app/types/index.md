# TypeScript Types (`app/src/types/index.ts`)

## 1. Core Interfaces
- `ExperienceLevel`: `'entry' | 'mid' | 'senior' | 'lead' | 'executive'`
- `InterviewStatus`: `'draft' | 'active' | 'finishing' | 'completed'`
- `ChatMessage`: `{ id, role, content, timestamp, questionNumber }`
- `InterviewSession`: `{ id, jobTitle, companyName, jobDescription, experienceLevel, candidateName, cvFileName, cvSummary, cvSkills, status, createdAt, updatedAt, messages, score }`
- `CandidateScreeningResult`: `{ name, match_score, strengths, gaps, matched_chunks, summary, is_selected, cv_filename, cv_raw_text, experience_years, timeline_summary, tech_tenure, work_history }`
- `CreateInterviewInput`: Data passed from `CreateInterviewForm` to `storage.ts`.

