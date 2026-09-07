# Form Components (`app/src/components/forms/`)

## 1. `CreateInterviewForm.tsx`
- **Purpose**: Fullscreen 3-step setup and screening wizard for technical interviews.
- **Route Synchronization & Redirect Guards**:
  - Wizard steps are synchronized with URL search params (`?step=1`, `?step=2`, `?step=3`).
  - **Redirect Guards**: If `?step=2` or `?step=3` is refreshed or navigated to directly without required prerequisites (valid job info / evaluated candidates), the guard automatically replaces the URL and falls back safely to Step 1 or Step 2.
  - Native browser back/forward buttons work seamlessly across wizard steps.
- **Step 1 (Job Info)**: `jobTitle`, `companyName`, `experienceLevel`, `jobDescription` with expanding textarea filling viewport height. Supports "Prefill Sample Role" using a purely fictional modern Backend Engineer profile at "Apex Cloud Technologies".
- **Step 2 (Candidate Pool & CV Ingestion)**: Multi-CV upload integration via `CVUploader` (PDF/DOCX) with real-time in-memory document text extraction and automatic candidate name recognition. Also includes an optional "Load Sample Candidates (15)" quick-demo button that loads 15 completely fictional, AI-generated synthetic engineer profiles (covering top matches, adjacent backend stacks, full stack, junior, data, devops, frontend, mobile, embedded, and QA) with zero overlap or ties to real-world personal data.
  - **Asynchronous Extraction & Next Guard**: While CV documents are being parsed in the background (`apiExtractDocuments`), an `isExtracting` state disables the "Screen Candidates & Review Selection" submit button, rendering a loading spinner and status indicator (`t.form.extractingCVs`). This prevents the recruiter from proceeding prematurely before the candidate names and document texts are parsed.
- **Step 3 (Screening Hub & Candidate Selection)**:
  - **Fullscreen 2-Column Layout with Resizable Splitter**: Left column displays candidate identity, match score, executive summary, persistent leaderboard pool, and bottom action bar; right column renders a dedicated full-height high-resolution PDF document viewer.
  - **Permanent Dual Viewer Mode (PDF View & AI Extracted Text)**: Unconditional switcher in document ribbon allowing the user to seamlessly toggle between the interactive PDF document and the verbatim raw text extracted and analyzed by the AI model. Persistent `blobUrlsRef` caching guarantees that candidate PDF previews are preserved throughout candidate switching without premature revocation.
  - **Strict Per-Candidate File Binding**: The PDF preview is strictly bound only to the exact candidate owning that uploaded file (matched by ID, exact filename, or exact candidate name). Candidates without an uploaded PDF file (such as the predefined 15 synthetic sample profiles) display a clear `(N/A)` badge and an informative empty state with a direct one-click toggle to "AI Extracted Text", preventing silent cross-candidate PDF leaking.
  - **Interview Time Limit (Countdown Timer)**: Configurable switch allowing recruiters to set an optional interview duration (`5, 10, 15, 20, 25, 30, 40, 60 min`, default disabled / 15 min), which dynamically scales the planned technical topics count and activates live pacing.
  - **Live Switching**: Selecting any candidate in the left applicant pool immediately highlights them as `SELECTED` and displays their document and AI extraction on the right in real time.
  - **Thinking Orbs Integration**: Renders hand-tuned particle animations (`ThinkingOrb` from `thinking-orbs`) for all async generation and streaming states.
  - **Spam & Selection Guards**: All interactive buttons, cards, and badges use `select-none` to prevent accidental text highlighting on rapid clicking.

## 2. `CVUploader.tsx`
- **Purpose**: Drag & drop multi-file upload zone supporting candidate resumes.
- **Accepted Formats**: `.pdf`, `.docx`, `.doc`, `.txt` (Max 10MB each).
- **Features**: 
  - Visual compact dropzone indicator with centered prompts and active drag feedback.
  - **Inline Name Editor**: Every uploaded candidate row features an editable input field allowing direct customization of the candidate's name.
  - **Automatic Name Extraction & Loading Indicators**: When files like `CV.pdf` or `Resume.pdf` are uploaded, the backend extraction engine automatically parses the candidate's actual name from the document header. During this extraction period, the candidate input and status line display an animated pulse and extraction spinner (`t.cvUploader.extractingName`), switching cleanly to the detected name and verified text size upon resolution.
  - Responsive multi-column candidate queue grid (`grid-cols-1 md:grid-cols-2 xl:grid-cols-3`).
  - **Batch & Per-Candidate Removal**: Individual delete buttons per candidate as well as a one-click "Clear All" action in the queue header that cleans all staged CVs, revokes active Blob preview URLs, and clears candidate error states.

