# Frontend (`app/`) Architecture

## 1. Overview
The `app/` directory houses the frontend Single Page Application (SPA) built with **React 19**, **Vite**, **TypeScript**, and **shadcn/ui**.

## 2. Directory Structure Mirror
- [`components/`](components/)
  - [`forms.md`](components/forms.md): `CreateInterviewForm.tsx`, `CVUploader.tsx`
  - [`history.md`](components/history.md): `PreviousInterviewsList.tsx`
  - [`interview.md`](components/interview.md): `ChatInterface.tsx`, `InterviewHeader.tsx`, `InterviewSidebar.tsx`
  - [`layout.md`](components/layout.md): `Header.tsx`
  - [`ui.md`](components/ui.md): shadcn/ui primitives (`button`, `card`, `input`, `dialog`, etc.)
- [`lib/`](lib/)
  - [`storage.md`](lib/storage.md): LocalStorage persistence layer
  - [`mock_ai.md`](lib/mock_ai.md): Context-aware mock question engine
  - [`utils.md`](lib/utils.md): Tailwind styling class utilities
- [`pages/`](pages/)
  - [`home_page.md`](pages/home_page.md): `HomePage.tsx`
  - [`interview_room_page.md`](pages/interview_room_page.md): `InterviewRoomPage.tsx`
  - [`login_page.md`](pages/login_page.md): `LoginPage.tsx`
- [`types/`](types/)
  - [`index.md`](types/index.md): TypeScript data models & DTOs

## 3. Strict Quality Standards
- **shadcn/ui Primitives**: Only accessible Radix UI primitives with shadcn design tokens. No raw CSS.
- **ESLint & Prettier**: Checked with `npm run lint` and `npm run format:check`.
