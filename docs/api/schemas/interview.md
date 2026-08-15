# Interview Schemas (`api/schemas/interview.py`)

## 1. Pydantic Models
- `ExperienceLevel`: Enum (`entry`, `mid`, `senior`, `lead`, `executive`)
- `InterviewStatus`: Enum (`draft`, `active`, `completed`)
- `InterviewCreate`:
  - `job_title` (str, required)
  - `company_name` (Optional[str])
  - `job_description` (str, required)
  - `experience_level` (ExperienceLevel, default: `mid`)
  - `candidate_name` (Optional[str], default: `"Candidate"`)
  - `cv_filename` (Optional[str])
  - `cv_raw_text` (Optional[str])
- `InterviewResponse`: Complete session payload with `id`, `created_at`, `total_questions`, and `status`.
