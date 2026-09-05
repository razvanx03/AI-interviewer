# Interview Schemas (`api/schemas/interview.py`)

## 1. Pydantic Models
- `ExperienceLevel`: Enum (`entry`, `mid`, `senior`, `lead`, `executive`)
- `InterviewStatus`: Enum (`draft`, `active`, `finishing`, `completed`)
- `InterviewCreate`:
  - `job_title` (str, required)
  - `company_name` (Optional[str])
  - `job_description` (str, required)
  - `experience_level` (ExperienceLevel, default: `mid`)
  - `candidate_name` (Optional[str], default: `"Candidate"`)
  - `cv_filename` (Optional[str])
  - `cv_raw_text` (Optional[str])
- `InterviewResponse`: Complete session payload with `id`, `created_at`, `total_questions`, and `status`.
- `CandidateScreeningResult`:
  - `name` (str)
  - `match_score` (int, 0-100)
  - `strengths` (List[str])
  - `gaps` (Optional[List[str]])
  - `matched_chunks` (Optional[List[str]])
  - `summary` (str)
  - `is_selected` (bool)
  - `cv_filename` (Optional[str])
  - `cv_raw_text` (Optional[str])
  - `experience_years` (Optional[float], verified non-inflated career duration)
  - `timeline_summary` (Optional[str])
  - `tech_tenure` (Optional[Dict[str, float]])
  - `work_history` (Optional[List[Dict[str, Any]]])
- `CandidateScreeningRequest`:
  - `job_title` (str, required)
  - `company_name` (Optional[str])
  - `job_description` (str, required)
  - `experience_level` (ExperienceLevel, default: `mid`)
  - `candidates` (List[CandidateItem], min_length: 1, max_length: 150)
- `CandidateScreeningResponse`: `{ top_candidate, screening_results }`

