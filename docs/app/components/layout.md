# Layout Components (`app/src/components/layout/`)

## 1. `Sidebar.tsx`
- **Purpose**: Collapsible navigation sidebar for the AI Chat workspace.
- **Elements**:
  - Top header with logo and "AI Interviewer" title.
  - Full-width **`+ New Interview`** primary action button.
  - Scrollable chronological list of interview sessions:
    - Active session highlight.
    - Job role title and company / candidate subtitle.
    - Status indicators (active vs. completed).
    - Quick delete button on hover.
  - Footer with theme toggle (`ModeToggle`).
  - Mobile drawer support with backdrop overlay.

## 2. `Header.tsx`
- **Purpose**: Navigation bar when standalone pages are viewed.

## 3. `mode-toggle.tsx` & `theme-provider.tsx`
- Standard shadcn/ui theme provider and switcher.
- Defaults to `dark` mode and stores preference under `ai-interviewer-ui-theme` in `localStorage`.
