# Mock AI Engine (`app/src/lib/mockAi.ts`)

## 1. Overview
Simulates the contextual AI interviewer responses, asking role-specific technical questions and completing the interview after a 5-question evaluation cycle.

## 2. API
- `generateMockAiResponse(session: InterviewSession, userResponse: string): Promise<{ reply: string; isComplete: boolean }>`
  - Simulates LLM thinking delay (1.1s).
  - Advances through structured question bank.
  - Returns final assessment summary on the 5th question.
