# Form Components (`app/src/components/forms/`)

## 1. `CreateInterviewForm.tsx`
- **Purpose**: Fullscreen 3-step setup and screening wizard for technical interviews.
- **Route Synchronization & Redirect Guards**:
  - Wizard steps are synchronized with URL search params (`?step=1`, `?step=2`, `?step=3`).
  - **Redirect Guards**: If `?step=2` or `?step=3` is refreshed or navigated to directly without required prerequisites (valid job info / evaluated candidates), the guard automatically replaces the URL and falls back safely to Step 1 or Step 2.
  - Native browser back/forward buttons work seamlessly across wizard steps.
- **Step 1 (Job Info)**: `jobTitle`, `companyName`, `experienceLevel`, `jobDescription` with expanding textarea filling viewport height.
- **Step 2 (Candidate Pool & CV Ingestion)**: Multi-CV upload integration via `CVUploader` (PDF/DOCX) or sample candidate prefill.
- **Step 3 (Screening Hub & Candidate Selection)**:
  - **Fullscreen 2-Column Layout**: Left column displays candidate identity, executive summary, pool switcher, and bottom action bar; right column renders a dedicated full-height high-resolution PDF document viewer.
  - **Live Switching**: Selecting any candidate in the left applicant pool immediately switches the candidate and swaps their full PDF on the right in real time.
  - **Thinking Orbs Integration**: Renders hand-tuned particle animations (`ThinkingOrb` from `thinking-orbs`) for all async generation and streaming states.
  - **Spam & Selection Guards**: All interactive buttons, cards, and badges use `select-none` to prevent accidental text highlighting on rapid clicking.

## 2. `CVUploader.tsx`
- **Purpose**: Drag & drop multi-file upload zone supporting candidate resumes.
- **Accepted Formats**: `.pdf`, `.docx`, `.doc`, `.txt` (Max 10MB each).
- **Features**: 
  - Visual dropzone indicator, active drag feedback.
  - **Inline Name Editor**: Every uploaded candidate row features an editable input field allowing direct customization of the candidate's name (e.g. changing fallback `"Candidate"` to `"Ander Razvan"`).
  - Responsive multi-column candidate queue grid (`grid-cols-1 md:grid-cols-2 xl:grid-cols-3`).
  - Download and removal actions per candidate.
