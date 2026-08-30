# Interview Room Page (`app/src/pages/InterviewRoomPage.tsx`)

## 1. Overview
Renders at `/interview/:id`. Fetches the interview session directly from the PostgreSQL backend API (`GET /api/v1/interviews/{id}`).

## 2. Key Features & Animations
- **Thinking Orbs Loading Transition**: When switching between interviews, displays `<ThinkingOrb state="connecting" size={64} />` with a smooth minimum 500ms (0.5s) loading duration (`Promise.all([apiGetInterview(id), timer])`).
- **Header**: Shows Job Title, Candidate name, and Company name (e.g. `Candidate: Alex Morgan • Company: Google`), Share link button, Finish interview modal, Live countdown timer with auto-completion guards (`isEndingRef`), and Live / Finishing / Completed status badges. Synchronizes language selector (`RO` / `EN`) with session language directly.
- **State-Machine Finishing Guard**: Transitions to `finishing` instantly when Finish is clicked, immediately disabling and hiding the finish action across concurrent requests and page refreshes, and polling until `completed`.
- **Dynamic Browser Title**: Automatically updates `document.title` to the conversation's job title.
- **ChatInterface**: Real-time SSE streaming with `<ThinkingOrb state="solving" size={20} />` for AI thought/evaluation states. Automatically filters `[INTERVIEW_COMPLETE]` token from chat bubbles and cleanly transitions to completed state.
- **Admin Evaluation Card**: When an admin reviews a completed interview session, the application automatically loads and renders the comprehensive hiring evaluation report with criteria scoring, strengths, and weakness breakdown.
- **404 State**: Renders accessible `NotFoundPage` if session is not found.
