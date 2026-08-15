# Layout Components (`app/src/components/layout/`)

## 1. `Header.tsx`
- **Purpose**: Global top navigation bar.
- **Elements**:
  - Application brand icon (`Bot`) and logo.
  - "InterviewAI" title and BETA badge.
  - "New Interview" action button.
  - `ModeToggle`: Theme switcher with Light, Dark, and System modes.

## 2. `mode-toggle.tsx` & `theme-provider.tsx`
- Standard shadcn/ui theme provider and switcher.
- Defaults to `dark` mode and stores preference under `ai-interviewer-ui-theme` in `localStorage`.
