# Form Components (`app/src/components/forms/`)

## 1. `CreateInterviewForm.tsx`
- **Purpose**: Collects interview configuration data from candidate or recruiter.
- **Fields**:
  - `jobTitle`: Target job position (required)
  - `companyName`: Target company name (optional)
  - `candidateName`: Candidate's full name (optional, defaults to "Candidate")
  - `experienceLevel`: Seniority dropdown (`entry`, `mid`, `senior`, `lead`, `executive`)
  - `jobDescription`: Multi-line text for responsibilities and requirements (required)
  - `cvFile`: File upload integration via `CVUploader`
- **Features**: "Load Sample Data" action populating realistic test inputs in 1 click.

## 2. `CVUploader.tsx`
- **Purpose**: Drag & drop file upload zone supporting candidate resumes.
- **Accepted Formats**: `.pdf`, `.docx`, `.doc`, `.txt` (up to 10MB).
- **Features**: Visual dropzone indicator, active drag feedback, file preview badge with file removal action.
