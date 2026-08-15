# Interview Room Page (`app/src/pages/InterviewRoomPage.tsx`)

## 1. Overview
Renders at `/interview/:id` (or `#/interview/:id`).

## 2. Structure
- `InterviewHeader`: Shareable URL copy tool, status badge, exit button.
- `ChatInterface`: Primary message conversation container.
- `InterviewSidebar`: Position requirements and detected CV skill tags.
- Fallback 404 state if session ID is not found in browser storage.
