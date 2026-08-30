# Layout Components (`app/src/components/layout/`)

## 1. `Sidebar.tsx`
- **Purpose**: Collapsible navigation sidebar for the AI Chat workspace with role-aware modes.
- **Admin View (`isAdmin: true`)**:
  - Top header with logo, title, and `Recruiter Admin` badge.
  - Full-width **`+ New Interview`** primary action button.
  - Search filter accordion and scrollable chronological list of interview sessions.
  - Quick swipeable and modal delete actions.
  - Footer with Admin Profile, Sign Out button, Settings menu, and Collapse toggle.
- **Candidate View (`isAdmin: false`)**:
  - Top header with logo and `Candidate Guest` badge.
  - Clean `Candidate Interview Room` status panel (no access to history or creation buttons).
  - Footer with Theme and Language preferences.
- **Mobile Drawer**: Responsive slide-out drawer with backdrop overlay.

## 2. `Header.tsx`
- **Purpose**: Navigation bar when standalone pages are viewed.

## 3. `mode-toggle.tsx` & `theme-provider.tsx`
- Standard shadcn/ui theme provider and switcher.
- Defaults to `dark` mode and stores preference under `ai-interviewer-ui-theme` in `localStorage`.
