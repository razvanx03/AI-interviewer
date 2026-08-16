# Interview Room Page (`app/src/pages/InterviewRoomPage.tsx`)

## 1. Overview
Renders at `/interview/:id`. Fetches the interview session directly from the PostgreSQL backend API (`GET /api/v1/interviews/{id}`).

## 2. Key Features & Animations
- **Thinking Orbs Loading Transition**: When switching between interviews, displays `<ThinkingOrb state="connecting" size={64} />` with a smooth minimum 500ms (0.5s) loading duration (`Promise.all([apiGetInterview(id), timer])`).
- **Header**: Shows Job Title, Candidate name, and Company name (e.g. `Candidate: Alex Morgan • Company: Google`), Share link button, Finish interview modal, and Live/Completed status badge.
- **Dynamic Browser Title**: Automatically updates `document.title` to the conversation's job title.
- **ChatInterface**: Real-time SSE streaming with `<ThinkingOrb state="solving" size={20} />` for AI thought/evaluation states.
- **404 State**: Renders accessible `NotFoundPage` if session is not found.
