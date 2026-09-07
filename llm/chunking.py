from typing import List, Dict, Any, Tuple, Optional
import re
from datetime import datetime

MONTH_MAP: Dict[str, int] = {
    # English
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
    # Romanian
    "ian": 1, "ianuarie": 1,
    "februarie": 2,
    "martie": 3,
    "aprilie": 4,
    "mai": 5,
    "iun": 6, "iunie": 6,
    "iul": 7, "iulie": 7,
    "august": 8,
    "septembrie": 9,
    "octombrie": 10,
    "noiembrie": 11,
    "decembrie": 12,
}

DATE_RANGE_REGEX = re.compile(
    r'(?i)\b('
    r'(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|ian(?:uarie)?|martie|aprilie|mai|iun(?:ie)?|iul(?:ie)?|septembrie|octombrie|noiembrie|decembrie)[a-z]*\.?\s+\d{4}|\b\d{1,2}[./\-]\d{4}\b|\b\d{4}\b)'
    r'\s*(?:–|—|-|to|until|până\s+în|pana\s+in)\s*'
    r'(present|current|now|prezent|actual|\d{4}|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|ian(?:uarie)?|martie|aprilie|mai|iun(?:ie)?|iul(?:ie)?|septembrie|octombrie|noiembrie|decembrie)[a-z]*\.?\s+\d{4}|\b\d{1,2}[./\-]\d{4}\b)'
    r')\b'
)

DEFAULT_TECH_CATALOGUE = [
    ".NET", "C#", "React", "React.js", "TypeScript", "JavaScript", "Python", "FastAPI",
    "Django", "Node.js", "PostgreSQL", "MySQL", "MariaDB", "MongoDB", "Redis",
    "SQL Server", "Docker", "Kubernetes", "AWS", "Azure", "Azure DevOps", "GCP",
    "GraphQL", "REST", "CI/CD", "Tailwind", "Next.js", "Vue", "Angular", "Java",
    "Spring Boot", "Go", "Rust", "Git", "Ruby", "Rails", "Ruby on Rails"
]

SECTION_PATTERNS = [
    ("EDUCATION", re.compile(r"(?i)^\s*(?:EDUCATION|STUDII|EDUCATIE|EDUCAȚIE|ACADEMIC|QUALIFICATIONS)\b")),
    ("PROJECTS", re.compile(r"(?i)^\s*(?:PROJECTS|PROIECTE|PERSONAL PROJECTS|PORTFOLIO|ACADEMIC PROJECTS|KEY PROJECTS|SIDE PROJECTS)\b")),
    ("SKILLS", re.compile(r"(?i)^\s*(?:SKILLS|TECHNICAL SKILLS|SKILLS & TOOLS|COMPETENTE|COMPETENȚE|PROGRAMMING LANGUAGES|TEHNOLOGII ȘI INSTRUMENTE)\s*[:—\-]?\s*$")),
    ("EXPERIENCE", re.compile(r"(?i)^\s*(?:EXPERIENCE|WORK EXPERIENCE|EXPERIENTA|EXPERIENȚĂ|EMPLOYMENT|WORK HISTORY|PROFESSIONAL EXPERIENCE)\b")),
]

EDUCATION_KEYWORDS_REGEX = re.compile(
    r"(?i)\b(?:b\.?sc|m\.?sc|bachelor|master|phd|licenta|licență|masterat|doctorat|college|liceu|high school|facultate|university|universitate|infor?matics|cybersecurity|electronics)\b"
)
PROJECT_KEYWORDS_REGEX = re.compile(
    r"(?i)\b(?:"
    r"personal\s+projects?|proiect(?:e)?\s+personal(?:e)?|side\s+projects?|"
    r"pet\s+projects?|hobby\s+projects?|academic\s+projects?|proiect(?:e)?\s+academic(?:e)?|"
    r"proiect\s+(?:de\s+)?licen[tț]?[aă]|proiect\s+(?:de\s+)?diserta[tț]i[eie]|"
    r"proiect\s+(?:de\s+)?diplom[aă]|diploma\s+project|bachelor\s+thesis|master\s+thesis|"
    r"independent\s+projects?|proiect\s+individual|proiect\s+studen[tț]esc|portfolio\s+projects?"
    r")\b"
)
VOLUNTEER_KEYWORDS_REGEX = re.compile(
    r"(?i)\b(?:club(?:ul)?\s+studen|asocia[tț\?]?i[a-z]*|student\s+club|voluntar|volunteering|volunteer|cse\b)\b"
)
COURSE_KEYWORDS_REGEX = re.compile(
    r"(?i)\b(?:design essentials|introduction to|curs|training course|workshop)\b"
)


class TimelineExtractor:
    """
    Extracts employment periods, job headers, and duration from CV text.
    Accurately isolates employment tenure from education and projects, preventing inflated years.
    """

    @staticmethod
    def parse_date_point(s: str, is_end: bool = False) -> Optional[Tuple[int, int]]:
        s = s.strip().lower()
        if s in ("present", "current", "now", "prezent", "actual"):
            now = datetime.now()
            return now.year, now.month

        # Month Year (e.g. 'Oct 2025' or 'October 2025')
        m = re.search(r"([a-z]+)[.\s]+(\d{4})", s)
        if m:
            m_name = m.group(1)[:3]
            year = int(m.group(2))
            month = MONTH_MAP.get(m_name, 6 if not is_end else 12)
            return year, month

        # Numeric Month/Year (e.g. '05/2024' or '5-2024')
        m2 = re.search(r"(\d{1,2})[./\-](\d{4})", s)
        if m2:
            month = max(1, min(12, int(m2.group(1))))
            year = int(m2.group(2))
            return year, month

        # Year only (e.g. '2024')
        m3 = re.search(r"\b(\d{4})\b", s)
        if m3:
            year = int(m3.group(1))
            month = 1 if not is_end else 12
            return year, month

        return None

    @classmethod
    def calculate_months(cls, interval_str: str) -> int:
        parts = re.split(r"\s*(?:–|—|-|to|until|până\s+în|pana\s+in)\s*", interval_str, flags=re.IGNORECASE)
        if len(parts) != 2:
            return 6
        st = cls.parse_date_point(parts[0], is_end=False)
        en = cls.parse_date_point(parts[1], is_end=True)
        if not st or not en:
            return 6
        y1, m1 = st
        y2, m2 = en
        months = (y2 - y1) * 12 + (m2 - m1) + 1
        return max(1, months)

    @classmethod
    def format_duration(cls, months: int) -> str:
        if months <= 0:
            return "0 mo"
        if months < 12:
            return f"~{months} mo" if months == 1 else f"~{months} mos"
        years = months // 12
        rem = months % 12
        if rem >= 2:
            return f"~{years} yrs {rem} mos"
        return f"~{years} yrs" if years > 1 else "~1 yr"

    @classmethod
    def extract_technologies(cls, text: str, tech_catalogue: Optional[List[str]] = None) -> List[str]:
        if not text:
            return []
        catalogue = tech_catalogue or DEFAULT_TECH_CATALOGUE
        found = []
        for tech in catalogue:
            pattern = r"(?i)(?:\b|(?<=[^a-zA-Z0-9]))" + re.escape(tech) + r"(?:\b|(?=[^a-zA-Z0-9]))"
            if re.search(pattern, text):
                found.append(tech)
        return found

    @classmethod
    def parse_cv_blocks(
        cls,
        cv_text: str,
        tech_catalogue: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
        if not lines:
            return []

        current_section = "GENERAL"
        raw_blocks: List[Dict[str, Any]] = []
        current_role: Optional[str] = None
        current_interval: Optional[str] = None
        current_lines: List[str] = []

        for i, line in enumerate(lines):
            # 1. Detect section boundary
            detected_sec = None
            for sec_name, sec_regex in SECTION_PATTERNS:
                if sec_regex.search(line):
                    detected_sec = sec_name
                    break

            if detected_sec and detected_sec != current_section:
                if current_role or current_lines:
                    raw_blocks.append({
                        "section": current_section,
                        "role": current_role,
                        "interval": current_interval,
                        "body": "\n".join(current_lines).strip(),
                    })
                    current_role = None
                    current_interval = None
                    current_lines = []
                current_section = detected_sec
                # If line is only the section header, advance to next line
                rem = re.sub(
                    r"(?i)^\s*(?:EDUCATION|STUDII|EDUCATIE|EDUCAȚIE|EXPERIENCE|WORK EXPERIENCE|EXPERIENTA|EXPERIENȚĂ|PROJECTS|PROIECTE|SKILLS|TECHNICAL SKILLS|SKILLS & TOOLS|COMPETENTE|COMPETENȚE)\s*[:—\-]?\s*",
                    "",
                    line,
                ).strip()
                if not rem:
                    continue
                line = rem

            # 2. Check for date range
            m = DATE_RANGE_REGEX.search(line)
            if m:
                interval_str = m.group(0)
                remainder = line.replace(interval_str, "").strip(" —|-–\t")

                if len(remainder) >= 3:
                    role = remainder
                else:
                    prev_line = lines[i - 1] if i > 0 else ""
                    if (
                        prev_line
                        and len(prev_line) < 70
                        and not DATE_RANGE_REGEX.search(prev_line)
                        and prev_line.lower() not in ("experience", "work experience", "experienta", "experiență")
                    ):
                        role = prev_line
                    else:
                        role = "Role" if current_section == "EXPERIENCE" else current_section.title()

                if current_role or current_lines:
                    body = [l for l in current_lines if l != role]
                    raw_blocks.append({
                        "section": current_section,
                        "role": current_role,
                        "interval": current_interval,
                        "body": "\n".join(body).strip(),
                    })
                    current_lines = []

                current_role = role
                current_interval = interval_str
            else:
                current_lines.append(line)

        if current_role or current_lines:
            body = [l for l in current_lines if l != current_role]
            raw_blocks.append({
                "section": current_section,
                "role": current_role,
                "interval": current_interval,
                "body": "\n".join(body).strip(),
            })

        # Enrich blocks with classification: is_work vs is_education vs is_project/skills
        enriched_blocks: List[Dict[str, Any]] = []
        for b in raw_blocks:
            sec = b.get("section", "EXPERIENCE")
            role = b.get("role")
            interval = b.get("interval")
            body = b.get("body", "")

            is_education = (sec == "EDUCATION") or bool(role and EDUCATION_KEYWORDS_REGEX.search(role)) or bool(body and EDUCATION_KEYWORDS_REGEX.search(body[:150]))
            is_project = (sec == "PROJECTS") or bool(role and PROJECT_KEYWORDS_REGEX.search(role)) or bool(body and PROJECT_KEYWORDS_REGEX.search(body[:150]))
            is_volunteer = bool(role and VOLUNTEER_KEYWORDS_REGEX.search(role)) or bool(body and VOLUNTEER_KEYWORDS_REGEX.search(body[:120]))
            is_course = bool(role and COURSE_KEYWORDS_REGEX.search(role)) or bool(body and COURSE_KEYWORDS_REGEX.search(body[:80]))
            
            # Genuine date interval that is NOT education, personal project, volunteering, or training course is verified employment
            is_work = bool(interval and not is_education and not is_volunteer and not is_course and not is_project)

            if interval:
                months = cls.calculate_months(interval)
                duration_str = cls.format_duration(months)
            else:
                months = 0
                duration_str = ""

            full_block_text = f"{role or ''}\n{body}".strip()
            techs = cls.extract_technologies(full_block_text, tech_catalogue)

            enriched_blocks.append({
                "section": sec,
                "is_work": is_work,
                "is_education": is_education,
                "is_project": is_project,
                "role": role,
                "interval": interval,
                "duration_months": months,
                "duration_formatted": duration_str,
                "technologies": techs,
                "body": body,
            })

        return enriched_blocks

    @classmethod
    def calculate_total_work_experience(cls, blocks: List[Dict[str, Any]]) -> Tuple[float, int]:
        """
        Calculate total verified professional employment duration, merging overlapping date intervals.
        Returns:
            (total_years, total_months)
        """
        work_blocks = [b for b in blocks if b.get("is_work", True) and b.get("interval")]
        if not work_blocks:
            return 0.0, 0

        active_months = set()
        fallback_months = 0

        for b in work_blocks:
            interval = b.get("interval", "")
            parts = re.split(r"\s*(?:–|—|-|to|until|până\s+în|pana\s+in)\s*", interval, flags=re.IGNORECASE)
            if len(parts) == 2:
                st = cls.parse_date_point(parts[0], is_end=False)
                en = cls.parse_date_point(parts[1], is_end=True)
                if st and en:
                    y1, m1 = st
                    y2, m2 = en
                    cur_y, cur_m = y1, m1
                    while (cur_y < y2) or (cur_y == y2 and cur_m <= m2):
                        active_months.add((cur_y, cur_m))
                        cur_m += 1
                        if cur_m > 12:
                            cur_m = 1
                            cur_y += 1
                    continue
            fallback_months += b.get("duration_months", 0)

        total_months = len(active_months) if active_months else fallback_months
        total_years = round(total_months / 12.0, 1)
        return total_years, total_months

    @classmethod
    def build_timeline_summary(cls, blocks: List[Dict[str, Any]]) -> str:
        work_blocks = [b for b in blocks if b.get("is_work", True) and b.get("interval") and b.get("duration_months", 0) > 0]
        if not work_blocks:
            return ""

        summary_lines = ["Detected Employment Timeline & Experience Duration:"]
        for b in work_blocks:
            role = b.get("role") or "Role"
            interval = b.get("interval")
            dur = b.get("duration_formatted")
            techs = b.get("technologies", [])
            tech_str = f" [Stack: {', '.join(techs)}]" if techs else ""
            summary_lines.append(f"- {role}: {interval} ({dur}){tech_str}")

        total_years, total_months = cls.calculate_total_work_experience(blocks)
        total_dur_str = cls.format_duration(total_months)
        summary_lines.append(f"Total Professional Experience: {total_dur_str} (~{total_years} yrs)")
        return "\n".join(summary_lines)

    @classmethod
    def calculate_tech_tenure(cls, blocks: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate cumulative tenure in years for each detected technology across verified employment roles only."""
        tech_tenure: Dict[str, float] = {}
        for b in blocks:
            if not b.get("is_work", True):
                continue
            months = b.get("duration_months", 0)
            if months <= 0:
                continue
            years = months / 12.0
            for tech in b.get("technologies", []):
                t_lower = tech.lower()
                tech_tenure[t_lower] = round(tech_tenure.get(t_lower, 0.0) + years, 2)
        return tech_tenure

from langchain_text_splitters import RecursiveCharacterTextSplitter

class SemanticTextSplitter:
    """
    Splits text into chunks using LangChain's RecursiveCharacterTextSplitter.
    Preserves structural and semantic boundaries (paragraphs, bullet points, sentences)
    while enforcing bounded chunk sizes with overlap for robust vector retrieval.
    Also provides context-preserving chunking with employment timeline headers.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "; ", ", ", " "]
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
        )

    def split_text(self, text: str) -> List[str]:
        """Split input text into bounded, overlapping chunks using LangChain RecursiveCharacterTextSplitter."""
        if not text or not text.strip():
            return []
        return self._splitter.split_text(text.strip())

    def split_cv_with_timeline(
        self,
        cv_text: str,
        tech_catalogue: Optional[List[str]] = None,
    ) -> Tuple[List[str], str, Dict[str, float], List[Dict[str, Any]], float]:
        """
        Segment CV into employment blocks, preserve job & date headers on each chunk,
        and generate a structured timeline summary, tech tenure weights, verified work history,
        and non-inflated total experience in years.
        Returns:
            (chunks, timeline_summary, tech_tenure_years, work_history, experience_years)
        """
        if not cv_text or not cv_text.strip():
            return [], "", {}, [], 0.0

        blocks = TimelineExtractor.parse_cv_blocks(cv_text, tech_catalogue)
        job_blocks_exist = any(b.get("interval") for b in blocks)

        if not job_blocks_exist:
            # Fallback to standard chunking
            chunks = self.split_text(cv_text)
            return chunks, "", {}, [], 0.0

        all_chunks: List[str] = []
        for b in blocks:
            role = b.get("role")
            interval = b.get("interval")
            dur = b.get("duration_formatted")
            body = b.get("body", "").strip()
            if not body:
                continue

            if role and interval:
                header_prefix = f"[{role} ({interval}, {dur})]: "
                # Account for header prefix length in chunk budget
                sub_splitter = SemanticTextSplitter(
                    chunk_size=max(200, self.chunk_size - len(header_prefix)),
                    chunk_overlap=self.chunk_overlap,
                    separators=self.separators,
                )
                sub_chunks = sub_splitter.split_text(body)
                for sc in sub_chunks:
                    all_chunks.append(f"{header_prefix}{sc}")
            else:
                sub_chunks = self.split_text(body)
                all_chunks.extend(sub_chunks)

        timeline_summary = TimelineExtractor.build_timeline_summary(blocks)
        tech_tenure = TimelineExtractor.calculate_tech_tenure(blocks)
        exp_years, _ = TimelineExtractor.calculate_total_work_experience(blocks)
        work_history = [
            {
                "role": b.get("role") or "Role",
                "interval": b.get("interval"),
                "duration_formatted": b.get("duration_formatted"),
                "duration_months": b.get("duration_months", 0),
                "technologies": b.get("technologies", []),
                "is_work": True,
            }
            for b in blocks
            if b.get("is_work", True) and b.get("interval")
        ]
        return all_chunks, timeline_summary, tech_tenure, work_history, exp_years



