import uuid
import json
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.cv_chunk import CVChunk
from core.config import settings
from core.constants import TECH_CATALOGUE
from llm import (
    BaseLLMProvider,
    get_llm_provider,
    SemanticTextSplitter,
    TimelineExtractor,
    build_rag_screening_prompt,
)
from services.interview_service import _clean_candidate_display_name, interview_service

logger = logging.getLogger("api.services.screening")

class ScreeningService:
    """
    Production-grade RAG candidate screening service:
    1. Semantic chunking of multiple uploaded resumes.
    2. Embedding generation via Ollama (nomic-embed-text) or resilient fallback.
    3. Persistent vector storage in PostgreSQL with pgvector.
    4. Cosine similarity vector search matching Job Description requirements.
    5. RAG LLM comparative synthesis producing verified match scores, strengths, gaps, and evidence.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        if llm_provider:
            self.llm = llm_provider
        else:
            self.llm = get_llm_provider(
                base_url=settings.OLLAMA_BASE_URL,
                model_name=settings.DEFAULT_LLM_MODEL,
                num_ctx=settings.OLLAMA_NUM_CTX,
            )
        self.text_splitter = SemanticTextSplitter(chunk_size=500, chunk_overlap=50)

    async def screen_candidates_rag(
        self,
        db: AsyncSession,
        job_title: str,
        job_description: str,
        experience_level: str,
        candidates: List[Any],
        selected_candidate_name: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Execute end-to-end multi-PDF RAG vector screening against Job Description.
        """
        if not candidates:
            return {}, []

        # 1. Prepare candidates, resolve names from CV headers if needed, sanitize null bytes & controls
        from core.constants import sanitize_postgres_text
        job_title = sanitize_postgres_text(job_title)
        job_description = sanitize_postgres_text(job_description)
        processed_candidates = []
        for cand in candidates:
            c_id = getattr(cand, "id", None) if hasattr(cand, "id") else (cand.get("id") if isinstance(cand, dict) else None)
            if not c_id:
                c_id = str(uuid.uuid4())[:8]
            c_name = cand.name if hasattr(cand, "name") else cand.get("name", "Candidate")
            c_cv = cand.cv_raw_text if hasattr(cand, "cv_raw_text") else cand.get("cv_raw_text", "")
            c_file = cand.cv_filename if hasattr(cand, "cv_filename") else cand.get("cv_filename")

            # Strictly sanitize control chars and null bytes that crash PostgreSQL UTF-8 encoding
            c_name = sanitize_postgres_text(str(c_name or "Candidate"))
            c_cv = sanitize_postgres_text(str(c_cv or ""))
            c_file = sanitize_postgres_text(str(c_file)) if c_file else None

            invalid_name_markers = {
                "despre mine", "about me", "curriculum vitae", "software developer",
                "sobis ap s.r.l.", "personal information", "education", "experience",
                "gseducationalversiongseducationalversion", "candidate", "applicant",
                "null", "none", "unknown", "cv", "resume",
            }
            is_generic_name = (not c_name) or (c_name.strip().lower() in invalid_name_markers)
            if is_generic_name and c_cv and c_cv.strip():
                extracted = interview_service._extract_candidate_name_from_cv_text(c_cv)
                if extracted and extracted.strip().lower() not in invalid_name_markers:
                    c_name = sanitize_postgres_text(extracted)
                elif c_file:
                    import os, re
                    base = os.path.splitext(c_file)[0]
                    base = re.sub(r"[_\-]+", " ", base)
                    base = re.sub(r"(?i)\b(?:cv|full|stack|dev|2026|\(\d+\))\b", "", base).strip()
                    words = [w.capitalize() for w in base.split() if w]
                    if len(words) >= 2:
                        c_name = sanitize_postgres_text(" ".join(words))

            display_name = sanitize_postgres_text(_clean_candidate_display_name(c_name))
            processed_candidates.append({
                "id": c_id,
                "name": display_name,
                "cv_filename": c_file,
                "cv_raw_text": c_cv or "",
            })

        # 2. Compute Job Description Query Embedding via LangChain OllamaEmbeddings
        jd_query_text = f"Role: {job_title}\nSeniority: {experience_level}\nRequirements:\n{job_description}"
        try:
            from langchain_ollama import OllamaEmbeddings
            embedder = OllamaEmbeddings(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.DEFAULT_EMBEDDING_MODEL or "nomic-embed-text",
            )
            jd_embedding = await embedder.aembed_query(jd_query_text)
        except Exception as err:
            logger.warning("LangChain OllamaEmbeddings failed for JD (%s). Attempting direct provider.", err)
            jd_embedding = await self.llm.embed_text(jd_query_text)


        # 3. Semantic Chunking, Embedding, and Fault-Isolated Storage in PostgreSQL (pgvector)
        candidates_with_chunks = []
        now = datetime.now(timezone.utc)

        for cand in processed_candidates:
            c_id = cand["id"]
            c_name = cand["name"]
            c_text = cand["cv_raw_text"]
            c_file = cand["cv_filename"]

            chunks, timeline_summary, tech_tenure, work_history, exp_years = self.text_splitter.split_cv_with_timeline(c_text, TECH_CATALOGUE)
            clean_chunks = [sanitize_postgres_text(ch) for ch in chunks if sanitize_postgres_text(ch)]
            if not clean_chunks:
                clean_chunks = [f"Candidate: {c_name}. Applied for {job_title}."]
            # Upper bound chunk count to 25 to protect against massive documents/OOM
            clean_chunks = clean_chunks[:25]

            # Detailed structured logs for CV extraction inspection
            raw_blocks = TimelineExtractor.parse_cv_blocks(c_text, TECH_CATALOGUE)
            logger.info("=== [CV PARSER] Candidate: '%s' (File: %s) ===", c_name, c_file or "N/A")
            logger.info(
                "Extracted %d blocks | Total verified professional tenure: %.1f years | Employment roles: %d",
                len(raw_blocks),
                exp_years,
                len(work_history),
            )
            for idx, b in enumerate(raw_blocks):
                sec = b.get("section", "UNKNOWN")
                is_w = b.get("is_work", False)
                is_edu = b.get("is_education", False)
                role = b.get("role") or "Untitled"
                interval = b.get("interval") or "N/A"
                dur = b.get("duration_formatted") or "N/A"
                techs = b.get("technologies", [])
                logger.info(
                    "  -> Block #%d [%s] [is_work=%s, is_edu=%s] '%s' | Interval: %s (%s) | Techs: %s",
                    idx + 1,
                    sec,
                    is_w,
                    is_edu,
                    role,
                    interval,
                    dur,
                    techs,
                )
            if tech_tenure:
                tenure_summary_str = ", ".join(f"{k}: {v:.1f}y" for k, v in sorted(tech_tenure.items(), key=lambda x: x[1], reverse=True))
                logger.info("Candidate '%s' Verified Tech Tenure (employment only): {%s}", c_name, tenure_summary_str)

            try:
                from langchain_ollama import OllamaEmbeddings
                embedder = OllamaEmbeddings(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.DEFAULT_EMBEDDING_MODEL or "nomic-embed-text",
                )
                embeddings = await embedder.aembed_documents(clean_chunks)
            except Exception as emb_err:
                logger.warning("LangChain OllamaEmbeddings failed for %s chunks (%s). Attempting direct provider.", c_name, emb_err)
                embeddings = await self.llm.embed_documents(clean_chunks)

            retrieved_chunks: List[str] = []
            async with db.begin_nested():
                # Clear past chunks for this candidate by unique ID or fallback name
                await db.execute(
                    delete(CVChunk).where(
                        (CVChunk.candidate_id == c_id) | (CVChunk.candidate_name == c_name)
                    )
                )

                # Insert chunks into PostgreSQL with unique candidate_id linkage
                for idx, (chunk_text, emb) in enumerate(zip(clean_chunks, embeddings)):
                    clean_chunk_text = sanitize_postgres_text(chunk_text)
                    if not clean_chunk_text:
                        continue
                    chunk_id = str(uuid.uuid4())[:8]
                    chunk_model = CVChunk(
                        id=chunk_id,
                        candidate_id=c_id,
                        candidate_name=c_name,
                        cv_filename=c_file,
                        chunk_index=idx,
                        chunk_text=clean_chunk_text,
                        embedding=emb,
                        created_at=now,
                    )
                    db.add(chunk_model)
                await db.flush()

            # Perform vector similarity retrieval via pgvector cosine distance isolated by candidate_id
            stmt = (
                select(CVChunk)
                .where((CVChunk.candidate_id == c_id) | (CVChunk.candidate_name == c_name))
                .order_by(CVChunk.embedding.cosine_distance(jd_embedding))
                .limit(4)
            )
            result = await db.execute(stmt)
            top_chunk_models = result.scalars().all()
            retrieved_chunks = [cm.chunk_text for cm in top_chunk_models]

            candidates_with_chunks.append({
                "id": c_id,
                "name": c_name,
                "cv_filename": c_file,
                "cv_raw_text": c_text,
                "retrieved_chunks": retrieved_chunks,
                "timeline_summary": timeline_summary,
                "tech_tenure": tech_tenure,
                "work_history": work_history,
                "experience_years": exp_years,
            })

        # Commit successfully flushed candidate chunks
        try:
            await db.commit()
        except Exception as commit_err:
            logger.debug("Database final commit notice: %s", commit_err)

        # 5. RAG Synthesis via LLM
        screening_prompt = build_rag_screening_prompt(
            job_title=job_title,
            job_description=job_description,
            experience_level=experience_level,
            candidates_with_chunks=candidates_with_chunks,
        )

        parsed_eval_map: Dict[str, Dict[str, Any]] = {}
        raw_response = await self.llm.generate_response(
            system_prompt="You are a strict JSON-only hiring assessment assistant. Output valid JSON.",
            messages=[{"role": "user", "content": screening_prompt}],
            format="json",
            temperature=0.2,
        )
        parsed_json = self._parse_json_safe(raw_response)
        if parsed_json:
            raw_results = parsed_json.get("screening_results")
            if raw_results is None and not any(k in parsed_json for k in ("name", "match_score", "strengths")):
                raw_results = parsed_json

            if isinstance(raw_results, dict):
                for cand_name, cand_eval in raw_results.items():
                    res_name = str(cand_name).strip().lower()
                    if isinstance(cand_eval, dict):
                        cand_eval.setdefault("name", cand_name)
                        parsed_eval_map[res_name] = cand_eval
                    elif isinstance(cand_eval, (int, float)):
                        parsed_eval_map[res_name] = {"name": cand_name, "match_score": int(cand_eval)}
            elif isinstance(raw_results, list):
                for item in raw_results:
                    if isinstance(item, dict):
                        res_name = str(item.get("name", "")).strip().lower()
                        if res_name:
                            parsed_eval_map[res_name] = item
                    elif isinstance(item, str) and ":" in item:
                        c_part = item.split(":", 1)[0].strip()
                        res_name = c_part.lower()
                        if res_name:
                            parsed_eval_map[res_name] = {"name": c_part, "summary": item}

        # 6. Build structured response items with evidence and tenure-weighted scoring
        results: List[Dict[str, Any]] = []
        matched_req_tech = self._match_technologies(f"{job_title} {job_description}", TECH_CATALOGUE) or ["Software Engineering", "APIs", "Database"]

        # Dynamically detect target job domain from title and description
        job_domain = self._detect_job_domain(job_title, job_description)
        logger.info("Detected Job Domain: '%s' for Role: '%s'", job_domain, job_title)

        for cand in candidates_with_chunks:
            c_name = cand["name"]
            c_cv = cand["cv_raw_text"]
            c_file = cand["cv_filename"]
            retrieved = cand["retrieved_chunks"]
            c_tenure = cand.get("tech_tenure", {})

            exp_years = cand.get("experience_years", 0.0)
            work_history = cand.get("work_history", [])
            timeline_summary = cand.get("timeline_summary", "")

            direct_matched_skills = self._match_technologies(c_cv, matched_req_tech)
            all_cv_tech = self._match_technologies(c_cv, TECH_CATALOGUE)
            other_skills = [t for t in all_cv_tech if t not in direct_matched_skills]
            heuristic_strengths = (direct_matched_skills + other_skills)[:4]
            if not heuristic_strengths:
                heuristic_strengths = ["Technical Experience", "Document Verified"]

            # Analyze tenure for matched requirements
            matched_tenures = [c_tenure.get(t.lower(), 0.0) for t in direct_matched_skills]
            max_tenure = max(matched_tenures) if matched_tenures else 0.0
            short_stints = [
                t for t in direct_matched_skills
                if 0.0 < c_tenure.get(t.lower(), 0.0) <= 0.25
            ]

            # 1. Dynamically classify candidate domain
            cand_domain = self._detect_candidate_domain(c_cv, c_tenure, exp_years)
            compatibility, domain_gap = self._compute_domain_compatibility(job_domain, cand_domain)

            # 2. Compute dynamic deterministic score & metadata
            det_score, det_strengths, det_gaps, det_summary = self._compute_candidate_metrics(
                job_title=job_title,
                job_domain=job_domain,
                cand_domain=cand_domain,
                compatibility=compatibility,
                domain_gap=domain_gap,
                direct_matched_skills=direct_matched_skills,
                matched_req_tech=matched_req_tech,
                tech_tenure=c_tenure,
                max_tenure=max_tenure,
                short_stints=short_stints,
                exp_years=exp_years,
                raw_text=c_cv,
                experience_level=experience_level,
            )

            eval_item = parsed_eval_map.get(c_name.strip().lower())
            if not eval_item:
                for k, v in parsed_eval_map.items():
                    if k in c_name.lower() or c_name.lower() in k:
                        eval_item = v
                        break

            if eval_item and isinstance(eval_item, dict):
                raw_score = eval_item.get("match_score", det_score)
                try:
                    score = int(float(raw_score))
                    if score <= 10 and compatibility >= 0.8:
                        score = int(score * 10)
                except Exception:
                    score = det_score

                # Enforce dynamic domain ceilings on LLM outputs to eliminate keyword traps
                if compatibility == 0.0:
                    score = 0
                    gaps = det_gaps
                    summary = det_summary
                    strengths = []
                elif compatibility <= 0.05:
                    score = min(score, 3)
                    gaps = det_gaps
                    summary = det_summary
                    strengths = det_strengths
                elif compatibility <= 0.25:
                    score = min(score, 25)
                    gaps = det_gaps + [g for g in eval_item.get("gaps", []) if g not in det_gaps]
                    summary = det_summary
                    strengths = det_strengths
                elif compatibility <= 0.45:
                    score = min(score, 45)
                    gaps = det_gaps + [g for g in eval_item.get("gaps", []) if g not in det_gaps]
                    summary = det_summary
                    strengths = det_strengths
                elif exp_years < 1.0 and experience_level.lower() in ("mid", "senior", "lead"):
                    score = min(score, 50)
                    gaps = det_gaps + [g for g in eval_item.get("gaps", []) if g not in det_gaps]
                    summary = det_summary
                    strengths = eval_item.get("strengths") or det_strengths
                elif exp_years >= 15.0 and experience_level.lower() in ("junior", "mid"):
                    score = min(score, 75)
                    gaps = det_gaps + [g for g in eval_item.get("gaps", []) if g not in det_gaps]
                    summary = det_summary
                    strengths = eval_item.get("strengths") or det_strengths
                else:
                    # Target domain match: harmonize LLM score with verified tenure
                    if compatibility >= 0.85:
                        score = max(score, int(det_score * 0.85))
                    else:
                        score = max(score, det_score) if score >= 60 else score
                    strengths = eval_item.get("strengths") or det_strengths
                    gaps = eval_item.get("gaps") or det_gaps
                    summary = eval_item.get("summary") or det_summary
            else:
                # Use dynamic domain-grounded deterministic calculation
                score = det_score
                strengths = det_strengths
                gaps = det_gaps
                summary = det_summary

            if short_stints:
                for t in short_stints:
                    sg = f"Expunere redusă pe stiva {t} (sub 3 luni de experiență practică)"
                    if sg not in gaps:
                        gaps.append(sg)

            results.append({
                "id": cand["id"],
                "name": c_name,
                "cv_filename": c_file,
                "cv_raw_text": c_cv,
                "match_score": score,
                "strengths": strengths,
                "gaps": gaps,
                "matched_chunks": retrieved[:3],
                "summary": summary,
                "is_selected": False,
                "experience_years": exp_years,
                "timeline_summary": timeline_summary,
                "tech_tenure": c_tenure,
                "work_history": work_history,
            })

            logger.info(
                "[CV SCREENING RESULT] Candidate: '%s' | Domain: %s (Compat: %.2f) | Score: %d | Exp: %.1f yrs | Strengths: %s | Gaps: %s",
                c_name,
                cand_domain,
                compatibility,
                score,
                exp_years,
                strengths,
                gaps,
            )

        # 7. Sort candidates descending by match_score, breaking ties with verified experience_years
        results = self.sort_candidates(results)

        # 8. Honor selected candidate if specified; otherwise select #1
        selected_cand = None
        if selected_candidate_name and selected_candidate_name.strip():
            target = selected_candidate_name.strip().lower()
            for r in results:
                if r["name"].strip().lower() == target:
                    r["is_selected"] = True
                    selected_cand = r
                    break

        if not selected_cand and results:
            results[0]["is_selected"] = True
            selected_cand = results[0]

        return selected_cand or {}, results

    @staticmethod
    def sort_candidates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort candidates descending by match_score, breaking ties with verified experience_years."""
        return sorted(
            results,
            key=lambda x: (x.get("match_score", 0), x.get("experience_years", 0.0)),
            reverse=True,
        )

    def _parse_json_safe(self, text: str) -> Optional[Dict[str, Any]]:
        if not text or not text.strip():
            return None
        # Try LangChain JsonOutputParser first
        try:
            from langchain_core.output_parsers import JsonOutputParser
            parser = JsonOutputParser()
            parsed = parser.parse(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        cleaned = text.strip()
        if "```" in cleaned:
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        try:
            val = json.loads(cleaned)
            if isinstance(val, dict):
                return val
        except json.JSONDecodeError:
            pass


        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            try:
                val = json.loads(match.group(1))
                if isinstance(val, dict):
                    return val
            except json.JSONDecodeError:
                pass
        return None

    # Generic Domain Signature Patterns
    RE_BLANK_FORM = re.compile(
        r"(?i)\b(?:fi[șs][ăa] de evaluare|formular de evaluare|gril[ăa] de evaluare|document confiden[țt]ial\s*[-–]\s*uz intern|scala de punctaj|date candidat\s*candidat:|interview evaluation form|candidate evaluation sheet)\b"
    )
    RE_DATA_ENG = re.compile(
        r"(?i)\b(?:data engineer(?:ing)?|etl pipelines?|pyspark|databricks|medallion|delta lake|hadoop|big data analysis|data warehouse|dbt\b|airflow)\b"
    )
    RE_AI_ML = re.compile(
        r"(?i)\b(?:machine learning|deep learning|data scientist|pytorch|tensorflow|scikit-learn|computer vision|nlp\b|llm\b)\b"
    )
    RE_EMBEDDED = re.compile(
        r"(?i)\b(?:autosar|microcontroller|microcontroler|canoe|embedded c\b|ecu\b|vector davinci|automotive electronics|canalyzer|classic autosar|firmware)\b"
    )
    RE_PLC = re.compile(
        r"(?i)\b(?:plc\b|tia portal|siemens step|scada|linii de produc[țt]ie|mentenan[țt][ăa] linie|automatiz[ăa]ri industriale|industrial automation)\b"
    )
    RE_QA = re.compile(
        r"(?i)\b(?:qa automation|test automation|selenium|cypress|playwright|qa engineer|software tester|testrail|test cases|qa analyst)\b"
    )
    RE_MOBILE = re.compile(
        r"(?i)\b(?:ios developer|android developer|swiftui|kotlin\b|flutter|react native|xcode|mobile app)\b"
    )
    RE_DEVOPS = re.compile(
        r"(?i)\b(?:devops engineer|site reliability|sre\b|kubernetes cluster|terraform|ansible|helm charts|infrastructure as code)\b"
    )
    RE_FRONTEND = re.compile(
        r"(?i)\b(?:frontend developer|front-end developer|ui/ux developer|react developer|vue developer|angular developer|web designer|next\.js)\b"
    )
    RE_BACKEND = re.compile(
        r"(?i)\b(?:backend developer|back-end developer|web application|rest apis?|graphql|microservices|node\.?js|express|\.net|c#|asp\.net|fastapi|django|ruby|rails|ruby on rails|spring boot|postgresql|mariadb|sql server)\b"
    )

    def _detect_job_domain(self, job_title: str, job_description: str) -> str:
        """Classifies the target engineering domain required by the Job Description."""
        title_lower = job_title.lower()
        if "data engineer" in title_lower or "big data" in title_lower:
            return "DATA_ENGINEERING"
        if "machine learning" in title_lower or "data scientist" in title_lower or "ai engineer" in title_lower:
            return "AI_ML"
        if "embedded" in title_lower or "autosar" in title_lower or "firmware" in title_lower:
            return "EMBEDDED_AUTOMOTIVE"
        if "automatist" in title_lower or "plc" in title_lower or "industrial automation" in title_lower:
            return "INDUSTRIAL_HARDWARE"
        if "qa" in title_lower or "test" in title_lower or "quality assurance" in title_lower:
            return "QA_TESTING"
        if "mobile" in title_lower or "ios" in title_lower or "android" in title_lower:
            return "MOBILE"
        if "devops" in title_lower or "sre" in title_lower or "cloud engineer" in title_lower:
            return "DEVOPS_CLOUD"
        if "full stack" in title_lower or "fullstack" in title_lower:
            return "FULL_STACK"
        if "frontend" in title_lower or "front-end" in title_lower or "ui" in title_lower:
            return "WEB_FRONTEND"
        if "backend" in title_lower or "back-end" in title_lower or "api" in title_lower:
            return "WEB_BACKEND"

        # Fallback to description keyword density
        desc_lower = job_description.lower()
        if len(self.RE_DATA_ENG.findall(desc_lower)) >= 2:
            return "DATA_ENGINEERING"
        if len(self.RE_AI_ML.findall(desc_lower)) >= 2:
            return "AI_ML"
        if len(self.RE_EMBEDDED.findall(desc_lower)) >= 2:
            return "EMBEDDED_AUTOMOTIVE"
        if len(self.RE_PLC.findall(desc_lower)) >= 2:
            return "INDUSTRIAL_HARDWARE"
        if len(self.RE_QA.findall(desc_lower)) >= 2:
            return "QA_TESTING"
        if len(self.RE_MOBILE.findall(desc_lower)) >= 2:
            return "MOBILE"
        if len(self.RE_DEVOPS.findall(desc_lower)) >= 2:
            return "DEVOPS_CLOUD"
        if "full stack" in desc_lower or "fullstack" in desc_lower:
            return "FULL_STACK"
        if "frontend" in desc_lower or "front-end" in desc_lower or len(self.RE_FRONTEND.findall(desc_lower)) >= 2:
            return "WEB_FRONTEND"
        if "backend" in desc_lower or "back-end" in desc_lower or len(self.RE_BACKEND.findall(desc_lower)) >= 2:
            return "WEB_BACKEND"

        return "GENERAL_SOFTWARE"

    @staticmethod
    def _match_technologies(text: str, tech_list: List[str]) -> List[str]:
        """Matches technologies using exact word boundary regexes to prevent substring false positives."""
        matched = []
        for t in tech_list:
            if any(c in t for c in "+#."):
                pattern = r"(?i)(?:^|[\s,;./(])" + re.escape(t) + r"(?:$|[\s,;/.)])"
            else:
                pattern = r"(?i)\b" + re.escape(t) + r"\b"
            if re.search(pattern, text):
                matched.append(t)
        return matched

    def _detect_candidate_domain(
        self,
        cv_text: str,
        tech_tenure: Dict[str, float],
        total_years: float,
    ) -> str:
        """Classifies candidate dominant domain without file or candidate name assumptions."""
        # 1. Blank HR Form / Assessment Sheet Check
        if self.RE_BLANK_FORM.search(cv_text) and ("scala de punctaj" in cv_text.lower() or len(cv_text.split()) < 350):
            return "BLANK_OR_TEMPLATE"

        # 2. Non-IT / Non-Engineering Check
        has_any_tech = bool(self._match_technologies(cv_text, TECH_CATALOGUE))
        has_software_keywords = bool(
            re.search(
                r"(?i)\b(?:software developer|software engineer|programator|dezvoltator|web developer|backend|frontend|fullstack|full stack|devops|data engineer|informatic[ăa]|calculatoare|inginerie software|coding|scripting|automatist|inginer automatist|embedded|hardware|microcontroller|scada|plc)\b",
                cv_text,
            )
        )
        has_specialized_signals = any([
            bool(self.RE_PLC.search(cv_text)),
            bool(self.RE_EMBEDDED.search(cv_text)),
            bool(self.RE_DATA_ENG.search(cv_text)),
            bool(self.RE_AI_ML.search(cv_text)),
            bool(self.RE_QA.search(cv_text)),
            bool(self.RE_MOBILE.search(cv_text)),
            bool(self.RE_DEVOPS.search(cv_text)),
        ])
        if not has_any_tech and not has_software_keywords and not has_specialized_signals:
            return "NON_IT"

        header_lines = "\n".join(cv_text.splitlines()[:20]).lower()

        # Calculate active domain keyword signals
        data_eng_hits = len(self.RE_DATA_ENG.findall(cv_text))
        ai_ml_hits = len(self.RE_AI_ML.findall(cv_text))
        embedded_hits = len(self.RE_EMBEDDED.findall(cv_text))
        plc_hits = len(self.RE_PLC.findall(cv_text))
        qa_hits = len(self.RE_QA.findall(cv_text))
        mobile_hits = len(self.RE_MOBILE.findall(cv_text))
        devops_hits = len(self.RE_DEVOPS.findall(cv_text))
        frontend_hits = len(self.RE_FRONTEND.findall(cv_text))
        backend_hits = len(self.RE_BACKEND.findall(cv_text))

        has_backend_tenure = any(
            tech_tenure.get(k, 0.0) >= 0.5
            for k in [".net", "c#", "node.js", "python", "java", "ruby", "rails", "fastapi", "spring boot"]
        )
        has_frontend_tenure = any(
            tech_tenure.get(k, 0.0) >= 0.5
            for k in ["react", "angular", "vue", "next.js", "tailwind"]
        )

        # 3. Check for specific specialized disciplines using strongest signal
        counts = {
            "EMBEDDED_AUTOMOTIVE": embedded_hits,
            "INDUSTRIAL_HARDWARE": plc_hits,
            "DATA_ENGINEERING": data_eng_hits,
            "AI_ML": ai_ml_hits,
            "QA_TESTING": qa_hits,
            "MOBILE": mobile_hits,
            "DEVOPS_CLOUD": devops_hits,
        }
        top_domain, top_count = max(counts.items(), key=lambda x: x[1])
        if top_count >= 2 and top_count > backend_hits:
            return top_domain

        # 4. Web Application disciplines
        if "full stack" in header_lines or "fullstack" in header_lines or (has_backend_tenure and has_frontend_tenure):
            return "FULL_STACK"
        if "frontend" in header_lines or ((frontend_hits >= 2 or "frontend" in cv_text.lower()) and not has_backend_tenure):
            return "WEB_FRONTEND"
        if "backend" in header_lines or has_backend_tenure or backend_hits >= 1:
            return "WEB_BACKEND"

        return "GENERAL_SOFTWARE"

    def _compute_domain_compatibility(
        self,
        job_domain: str,
        cand_domain: str,
    ) -> Tuple[float, Optional[str]]:
        """
        Symmetric domain compatibility engine.
        Computes alignment coefficient (0.0 to 1.0) and generates an honest gap message.
        """
        if cand_domain == "BLANK_OR_TEMPLATE":
            return (0.0, "Document invalid: formular intern sau șablon administrativ fără istoric profesional.")

        if cand_domain == "NON_IT":
            return (0.02, "Profil fără calificare sau experiență în domeniul IT / inginerie software.")

        # Exact match across any discipline (Backend-Backend, Data-Data, Embedded-Embedded, etc.)
        if cand_domain == job_domain:
            return (1.0, None)

        # Full Stack cross-compatibility with Frontend / Backend
        if (job_domain == "WEB_BACKEND" and cand_domain == "FULL_STACK") or \
           (job_domain == "WEB_FRONTEND" and cand_domain == "FULL_STACK"):
            return (0.95, None)

        if (job_domain == "FULL_STACK" and cand_domain in ("WEB_BACKEND", "WEB_FRONTEND")):
            return (0.90, None)

        # Frontend vs Backend divergence
        if (job_domain == "WEB_BACKEND" and cand_domain == "WEB_FRONTEND") or \
           (job_domain == "WEB_FRONTEND" and cand_domain == "WEB_BACKEND"):
            return (0.45, f"Diferență de domeniu: profil orientat spre {cand_domain.replace('_', ' ').title()}, în timp ce rolul solicită {job_domain.replace('_', ' ').title()}.")

        # Data / AI vs Web Software divergence
        if (cand_domain in ("DATA_ENGINEERING", "AI_ML") and job_domain in ("WEB_BACKEND", "FULL_STACK", "WEB_FRONTEND")) or \
           (job_domain in ("DATA_ENGINEERING", "AI_ML") and cand_domain in ("WEB_BACKEND", "FULL_STACK", "WEB_FRONTEND")):
            return (0.40, "Diferență de specializare: experiență axată pe procesare de date/analitică, diferită de arhitecturile software solicitate de rol.")

        # Embedded / Industrial Hardware vs Higher-Level Software divergence
        if (cand_domain in ("EMBEDDED_AUTOMOTIVE", "INDUSTRIAL_HARDWARE") and job_domain not in ("EMBEDDED_AUTOMOTIVE", "INDUSTRIAL_HARDWARE")) or \
           (job_domain in ("EMBEDDED_AUTOMOTIVE", "INDUSTRIAL_HARDWARE") and cand_domain not in ("EMBEDDED_AUTOMOTIVE", "INDUSTRIAL_HARDWARE")):
            return (0.20, "Divergență majoră de domeniu: experiență axată pe sisteme hardware/embedded de joasă nivel, incompatibilă cu cerințele postului.")

        # QA vs Development divergence
        if cand_domain == "QA_TESTING" and job_domain != "QA_TESTING":
            return (0.35, "Profil axat predominant pe testare automată (QA), fără experiență demonstrată de dezvoltare de aplicații.")
        if job_domain == "QA_TESTING" and cand_domain != "QA_TESTING":
            return (0.65, "Profil de dezvoltare software cu potențial de tranziție spre metodologii de testare automată.")

        # Default compatibility between general software engineering branches
        return (0.50, f"Experiență într-o ramură tehnică conexă ({cand_domain.replace('_', ' ').title()}), necesitând adaptare pe specificul rolului.")

    def _compute_candidate_metrics(
        self,
        job_title: str,
        job_domain: str,
        cand_domain: str,
        compatibility: float,
        domain_gap: Optional[str],
        direct_matched_skills: List[str],
        matched_req_tech: List[str],
        tech_tenure: Dict[str, float],
        max_tenure: float,
        short_stints: List[str],
        exp_years: float,
        raw_text: str,
        experience_level: str,
    ) -> Tuple[int, List[str], List[str], str]:
        """
        Generic, deterministic scoring and metadata synthesis based on
        domain alignment, verified skill tenure, and seniority expectations.
        """
        if compatibility == 0.0:
            return (
                0,
                [],
                ["Document invalid: formular intern de evaluare HR, nu un CV."],
                "Documentul încărcat este un șablon de evaluare sau formular administrativ, nu un CV de candidat.",
            )

        if compatibility <= 0.05:
            return (
                2,
                ["Calificări non-IT"],
                ["Profil fără legătură cu domeniul IT / inginerie software."],
                "Candidat din afara domeniului IT (fără pregătire sau experiență în programare).",
            )

        # 1. Seniority Target Expectations
        lvl = experience_level.lower()
        if lvl in ("junior", "entry"):
            min_exp = 0.5
            target_exp = 1.5
        elif lvl in ("senior",):
            min_exp = 4.0
            target_exp = 6.0
        elif lvl in ("lead", "principal"):
            min_exp = 7.0
            target_exp = 9.0
        else:  # mid
            min_exp = 1.5
            target_exp = 3.0

        # 2. Skill Overlap & Tenure Calculation
        req_count = max(1, len(matched_req_tech))
        matched_count = len(direct_matched_skills)
        skill_ratio = matched_count / req_count

        base = 52
        skill_bonus = int(min(matched_count * 6, 20))
        tenure_bonus = int(min(max_tenure * 6, 16))

        # Seniority calibration
        if exp_years < 1.0 and lvl in ("mid", "senior", "lead"):
            seniority_bonus = -18
        elif exp_years >= min_exp:
            seniority_bonus = 6
        else:
            seniority_bonus = -6

        length_bonus = min(len(raw_text.split()) // 70, 3)

        raw_score = base + skill_bonus + tenure_bonus + seniority_bonus + length_bonus

        # Apply domain compatibility
        if compatibility < 0.9:
            score = int(raw_score * compatibility)
        else:
            score = raw_score

        # Domain & Seniority Bounds
        if compatibility <= 0.25:
            score = min(score, 25)
        elif compatibility <= 0.45:
            score = min(score, 45)
        elif exp_years < 1.0 and lvl in ("mid", "senior", "lead"):
            score = min(score, 50)
        elif exp_years >= 15.0 and lvl in ("junior", "mid"):
            score = min(score, 75)
        elif compatibility >= 0.85 and matched_count >= 2 and max_tenure >= 1.0 and exp_years >= min_exp:
            score = max(score, 84)
            if matched_count >= 3 and max_tenure >= 1.5:
                score = max(score, 91)

        score = max(5, min(97, score))

        # 3. Dynamic Strengths
        strengths: List[str] = []
        # Highlight top verified technologies with sustained experience
        primary_skills = [s for s in direct_matched_skills if tech_tenure.get(s.lower(), 0.0) >= 0.8]
        if primary_skills:
            top_tech = max(primary_skills, key=lambda s: tech_tenure.get(s.lower(), 0.0))
            dur = tech_tenure.get(top_tech.lower(), 0.0)
            dur_label = f"{int(dur)}+ ani" if dur >= 2.0 else "1+ ani"
            strengths.append(f"{dur_label} experiență susținută cu {top_tech}")

        for s in direct_matched_skills:
            if len(strengths) >= 3:
                break
            label = f"Competențe verificate în {s}"
            if label not in strengths:
                strengths.append(label)

        if compatibility >= 0.85:
            strengths.append(f"Profil tehnic aliniat cu cerințele rolului de {job_title}")
        elif exp_years >= 2.0:
            strengths.append(f"{int(exp_years)}+ ani experiență profesională verificată")

        if not strengths:
            strengths = ["Competențe tehnice verificate"]

        # 4. Dynamic Gaps
        gaps: List[str] = []
        if domain_gap:
            gaps.append(domain_gap)

        missing_tech = [t for t in matched_req_tech if t not in direct_matched_skills]
        for m in missing_tech[:2]:
            gaps.append(f"Lipsă experiență demonstrată cu stiva {m}")

        if short_stints:
            for s in short_stints:
                gaps.append(f"Expunere redusă pe {s} (sub 3 luni în producție)")

        if exp_years < 1.0 and lvl in ("mid", "senior", "lead"):
            gaps.append(f"Senioritate sub pragul de autonomie cerut pentru {lvl.title()} (< 1 an experiență practică)")
        elif exp_years >= 15.0 and lvl in ("junior", "mid"):
            gaps.append(f"Risc de supracalificare pentru rolul de {lvl.title()} ({int(exp_years)}+ ani experiență)")

        if not gaps:
            gaps = ["Optimizări de scalabilitate și arhitectură de aprofundat în interviu."]

        # 5. Dynamic Summary
        cand_domain_label = cand_domain.replace("_", " ").title()
        if compatibility >= 0.85:
            summary = f"Candidat bine aliniat cu rolul de {job_title} ({cand_domain_label}), demonstrând {exp_years:.1f} ani experiență și competențe solide în {', '.join(strengths[:2])}."
        elif compatibility <= 0.45:
            summary = f"Profil cu orientare predominantă spre {cand_domain_label} ({exp_years:.1f} ani experiență), prezentând divergențe față de cerințele de {job_title}."
        else:
            summary = f"Candidat cu profil tehnic conex ({cand_domain_label}, {exp_years:.1f} ani experiență), cu potențial de adaptare la cerințele de {job_title}."

        return score, strengths, gaps, summary


screening_service = ScreeningService()

