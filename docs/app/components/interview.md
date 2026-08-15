# Interview Room Components (`app/src/components/interview/`)

## 1. `ChatInterface.tsx`
- **Purpose**: Real-time interactive conversation timeline between candidate and AI interviewer.
- **Features**:
  - Message bubble distinction (AI on left with avatar, Candidate on right with primary accent).
  - Question sequence badges (`Question #1`, `Question #2`, etc.).
  - AI thinking and evaluation indicator with spinner.
  - Auto-scroll to latest message on update.
  - Candidate input box with `Enter` submit and `Shift+Enter` multi-line support.
  - Confetti celebration effect (`canvas-confetti`) on interview completion with structured assessment summary.

## 2. `InterviewHeader.tsx`
- **Purpose**: Top navigation and status bar for the interview room.
- **Features**:
  - Return to dashboard button (`←`).
  - Job title and company badge.
  - One-click shareable URL copier with tooltip feedback.
  - "Finish" button to conclude interview session early.
  - Live status indicator badge.

## 3. `InterviewSidebar.tsx`
- **Purpose**: Collapsible / desktop panel providing candidate profile and target job context.
- **Features**:
  - Position requirements viewer.
  - Resume attachment badge.
  - Detected skill badges (e.g. React, TypeScript, Python, Architecture).
