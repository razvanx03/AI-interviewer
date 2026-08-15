# Storage Library (`app/src/lib/storage.ts`)

## 1. LocalStorage Key
`ai_interviewer_sessions_v1`

## 2. API Functions
- `getStoredInterviews(): InterviewSession[]`: Reads and parses all saved sessions from `localStorage`.
- `getInterviewById(id: string): InterviewSession | null`: Finds session matching 8-character ID.
- `saveInterview(session: InterviewSession): void`: Upserts session in storage.
- `createNewInterviewSession(input: CreateInterviewInput): InterviewSession`: Generates new session, random 8-character ID, welcome question, initial metadata, and persists to storage.
