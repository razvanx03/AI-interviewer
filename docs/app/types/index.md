# TypeScript Types (`app/src/types/index.ts`)

## 1. Core Interfaces
- `ExperienceLevel`: `'entry' | 'mid' | 'senior' | 'lead' | 'executive'`
- `InterviewStatus`: `'draft' | 'active' | 'completed'`
- `ChatMessage`: `{ id, role, content, timestamp, questionNumber }`
- `InterviewSession`: `{ id, jobTitle, companyName, jobDescription, experienceLevel, candidateName, cvFileName, cvSummary, cvSkills, status, createdAt, updatedAt, messages, score }`
- `CreateInterviewInput`: Data passed from `CreateInterviewForm` to `storage.ts`.
