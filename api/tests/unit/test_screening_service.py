import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from services.screening_service import ScreeningService, screening_service
from llm.chunking import SemanticTextSplitter
from models.cv_chunk import CVChunk
from schemas.interview import CandidateItem

class TestScreeningServiceUnit:
    def test_semantic_text_splitter(self):
        splitter = SemanticTextSplitter(chunk_size=100, chunk_overlap=20)
        sample_text = (
            "FastAPI is a modern web framework for building APIs with Python.\n\n"
            "PostgreSQL with pgvector provides native vector similarity search.\n\n"
            "Docker and Kubernetes orchestrate production microservices."
        )
        chunks = splitter.split_text(sample_text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 120  # bounded near chunk_size

    @pytest.mark.asyncio
    async def test_screen_candidates_rag_multi_candidate(self, db_session: AsyncSession):
        candidates = [
            CandidateItem(
                name="Alice Wonder",
                cv_filename="alice_resume.pdf",
                cv_raw_text="5 years experience in Python, FastAPI, Docker, and PostgreSQL databases. Built REST APIs.",
            ),
            CandidateItem(
                name="Bob Builder",
                cv_filename="bob_resume.docx",
                cv_raw_text="1 year junior developer working with HTML, CSS, and basic JavaScript. Learning Python.",
            ),
        ]

        top_cand, results = await screening_service.screen_candidates_rag(
            db=db_session,
            job_title="Senior Python Engineer",
            job_description="Looking for an expert in Python, FastAPI, and PostgreSQL with Docker experience.",
            experience_level="senior",
            candidates=candidates,
        )

        assert top_cand is not None
        assert len(results) == 2

        # Verify results structure
        for res in results:
            assert "name" in res
            assert "match_score" in res
            assert "strengths" in res
            assert "gaps" in res
            assert "matched_chunks" in res
            assert "summary" in res

        # Candidate with higher skill alignment should be ranked top
        assert results[0]["name"] == "Alice Wonder"
        assert results[0]["match_score"] >= results[1]["match_score"]
        assert results[0]["is_selected"] is True

        # Verify chunks persisted in PostgreSQL cv_chunks table
        stmt = select(CVChunk).where(CVChunk.candidate_name == "Alice Wonder")
        res_db = await db_session.execute(stmt)
        chunks_stored = res_db.scalars().all()
        assert len(chunks_stored) > 0
        assert chunks_stored[0].candidate_id is not None
        assert chunks_stored[0].candidate_id == results[0]["id"]

    @pytest.mark.asyncio
    async def test_screen_candidates_with_null_bytes_and_many_candidates(self, db_session: AsyncSession):
        # Test 10 candidates, including corrupted ligatures/null bytes (\x00)
        candidates = [
            CandidateItem(
                name=f"Candidate {i}",
                cv_filename=f"cv_{i}.pdf",
                cv_raw_text=f"Experience with .NET and pharmacy \x00eet management. Python {i} skills. Bug fixes \x00 in WASM.",
            )
            for i in range(10)
        ]

        top_cand, results = await screening_service.screen_candidates_rag(
            db=db_session,
            job_title="Full Stack Engineer",
            job_description="C# or Python engineer with .NET or FastAPI experience.",
            experience_level="mid",
            candidates=candidates,
        )

        assert top_cand is not None
        assert len(results) == 10

    def test_timeline_extractor_and_duration_calculation(self):
        from llm.chunking import TimelineExtractor, SemanticTextSplitter

        # Test calculation and formatting across various date formats
        assert TimelineExtractor.calculate_months("Oct 2025 – Present") >= 1
        assert TimelineExtractor.calculate_months("Jan 2022 – Dec 2024") == 36
        assert TimelineExtractor.calculate_months("Jun 2025 – Jul 2025") == 2
        assert TimelineExtractor.calculate_months("2021 – 2024") >= 36
        assert TimelineExtractor.calculate_months("Octombrie 2025 – Prezent") >= 1

        # Test block parsing on realistic CV snippet
        cv_snippet = (
            "IT Perspectives — Software Developer                 Oct 2025 – Present\n"
            ".NET  React.js  Python  Docker  MariaDB  Azure DevOps\n"
            "• Developed and maintained enterprise web application using .NET for backend.\n\n"
            "Tech Intern — Junior Dev                             Jun 2025 – Jul 2025\n"
            "React\n"
            "• Fixed minor UI bugs.\n"
        )
        blocks = TimelineExtractor.parse_cv_blocks(cv_snippet)
        assert len(blocks) == 2
        assert "Software Developer" in blocks[0]["role"]
        assert ".NET" in blocks[0]["technologies"]
        assert blocks[0]["duration_months"] >= 1

        # Test split_cv_with_timeline generates header-preserved chunks
        splitter = SemanticTextSplitter(chunk_size=400, chunk_overlap=30)
        chunks, timeline_summary, tenure, work_history, exp_years = splitter.split_cv_with_timeline(cv_snippet)
        assert len(chunks) >= 2
        assert any("[IT Perspectives" in c for c in chunks)
        assert "Oct 2025 – Present" in timeline_summary
        assert ".net" in tenure
        assert exp_years >= 1.0
        assert len(work_history) >= 1

    @pytest.mark.asyncio
    async def test_tenure_weighting_candidate_comparison(self, db_session: AsyncSession):
        # Candidate 1 has 3 years of sustained .NET and React experience
        # Candidate 2 has only 1 month of internship exposure to .NET and React
        candidates = [
            CandidateItem(
                name="Experienced Dev",
                cv_filename="exp_dev.pdf",
                cv_raw_text=(
                    "Senior Software Engineer | Enterprise Corp       Jan 2022 – Dec 2024\n"
                    ".NET  React  SQL Server  Docker\n"
                    "Architected scalable backend microservices using .NET and React dashboards.\n"
                ),
            ),
            CandidateItem(
                name="One Month Intern",
                cv_filename="intern_dev.pdf",
                cv_raw_text=(
                    "Junior Intern | Summer Labs                     Jun 2024 – Jun 2024\n"
                    ".NET  React\n"
                    "Completed a 3-week introductory training module on .NET and React.\n"
                ),
            ),
        ]

        top_cand, results = await screening_service.screen_candidates_rag(
            db=db_session,
            job_title="Senior .NET Full Stack Engineer",
            job_description="Seeking strong experience in .NET and React with Docker.",
            experience_level="senior",
            candidates=candidates,
        )

        assert top_cand is not None
        assert len(results) == 2

        exp_result = next(r for r in results if r["name"] == "Experienced Dev")
        intern_result = next(r for r in results if r["name"] == "One Month Intern")

        # Candidate with sustained tenure must outrank candidate with only 1 month
        assert exp_result["match_score"] > intern_result["match_score"]
        assert exp_result["is_selected"] is True
        assert exp_result["experience_years"] is not None
        assert exp_result["experience_years"] >= 2.5
        assert intern_result["experience_years"] is not None
        assert intern_result["experience_years"] <= 0.2

        # Intern must have a tenure/duration gap identified
        assert any(
            "expunere redusă" in g.lower()
            or "sub 3 luni" in g.lower()
            or "senioritate sub pragul" in g.lower()
            or "limited tenure" in g.lower()
            for g in intern_result["gaps"]
        )

        # Experienced dev must have sustained experience recognized in strengths
        assert any(
            "susținută" in s.lower() or "sustained" in s.lower() or "ani" in s.lower() or ".net" in s.lower()
            for s in exp_result["strengths"]
        )

    def test_education_and_projects_not_counted_as_work_experience(self):
        from llm.chunking import TimelineExtractor
        cv_text = (
            "Ander Razvan\n"
            "Software Developer\n\n"
            "EXPERIENCE\n"
            "IT Perspectives - Software Developer                 Oct 2025 - Present\n"
            ".NET  React.js  Python  Docker\n"
            "Developed enterprise web application with .NET and React.\n\n"
            "Sobis Solutions SRL - Software Developer             May 2024 - Oct 2025\n"
            "Node.js  Angular  Git\n"
            "Developed full-stack web application using Node.js.\n\n"
            "EDUCATION\n"
            "University of Sibiu\n"
            "M.Sc. in Cybersecurity                               2025 - Present\n"
            "Informatics (B.Sc.)                                  2022 - 2025\n"
            "High School College\n"
            "Electronics & Automation                             2018 - 2022\n\n"
            "PROJECTS\n"
            "ChatFlow - Personal Project                          Jan 2023 - Dec 2024\n"
            "React Native Node.js Docker\n\n"
            "SKILLS & TOOLS\n"
            "Git, Docker, C#, Python, React\n"
        )
        blocks = TimelineExtractor.parse_cv_blocks(cv_text)
        assert len(blocks) >= 5

        # Check education blocks are classified as not work
        edu_blocks = [b for b in blocks if b.get("is_education")]
        assert len(edu_blocks) >= 2
        for eb in edu_blocks:
            assert eb.get("is_work") is False

        # Check project blocks with date intervals are classified as not work
        proj_blocks = [b for b in blocks if b.get("is_project")]
        assert len(proj_blocks) >= 1
        for pb in proj_blocks:
            assert pb.get("is_work") is False

        # Calculate work experience: total work years should be ~2-2.5 years, NOT 6+ years (school & projects excluded)!
        tot_years, tot_months = TimelineExtractor.calculate_total_work_experience(blocks)
        assert 1.5 <= tot_years <= 3.0

        # Tech tenure should not credit Git or Docker with personal project or high school
        tech_tenure = TimelineExtractor.calculate_tech_tenure(blocks)
        git_tenure = tech_tenure.get("git", 0.0)
        assert git_tenure <= 2.0  # Around 1.5 years from Sobis Solutions SRL, NOT 4+ years
        assert tech_tenure.get(".net", 0.0) <= 2.0

    def test_word_boundary_tech_matching(self):
        # Prevent false positives like 'rest' in 'Somarest' or 'go' in Romanian words
        matched_false = screening_service._match_technologies("Somarest confecții textile", ["REST"])
        assert "REST" not in matched_false

        matched_true = screening_service._match_technologies("Architected REST APIs with microservices", ["REST"])
        assert "REST" in matched_true

        # Symbols like C# and .NET
        matched_dotnet = screening_service._match_technologies("Working with .NET 8 and C# backend", [".NET", "C#", "C++"])
        assert ".NET" in matched_dotnet
        assert "C#" in matched_dotnet
        assert "C++" not in matched_dotnet

    def test_job_and_candidate_domain_detection(self):
        # 1. Job Domain Detection
        assert screening_service._detect_job_domain("Backend Developer", "Building APIs with Ruby on Rails and Redis") == "WEB_BACKEND"
        assert screening_service._detect_job_domain("Data Engineer", "PySpark and Databricks ETL pipelines") == "DATA_ENGINEERING"
        assert screening_service._detect_job_domain("Embedded Software Engineer", "AUTOSAR ECU microcontroller C++") == "EMBEDDED_AUTOMOTIVE"
        assert screening_service._detect_job_domain("QA Automation Engineer", "Cypress Selenium Playwright test suites") == "QA_TESTING"
        assert screening_service._detect_job_domain("Frontend Engineer", "React TypeScript Next.js Tailwind") == "WEB_FRONTEND"
        assert screening_service._detect_job_domain("DevOps Specialist", "Kubernetes Terraform Docker AWS CI/CD") == "DEVOPS_CLOUD"
        assert screening_service._detect_job_domain("Mobile Developer", "React Native iOS Android Swift") == "MOBILE"

        # 2. Candidate Domain Detection
        blank_text = "FIȘĂ DE EVALUARE CANDIDAT Scala de punctaj: 1 - 5 Document confidențial - uz intern"
        assert screening_service._detect_candidate_domain(blank_text, {}, 0.0) == "BLANK_OR_TEMPLATE"

        non_it_text = "Inginer Textil Gemini CAD Tipare textile confecții croitorie 10 ani experiență"
        assert screening_service._detect_candidate_domain(non_it_text, {}, 10.0) == "NON_IT"

        auto_text = "Embedded Software Engineer Classic AUTOSAR CANoe DaVinci Microcontroller ECU Automotive C C++"
        assert screening_service._detect_candidate_domain(auto_text, {}, 4.0) == "EMBEDDED_AUTOMOTIVE"

        plc_text = "Inginer Automatist TIA Portal Siemens STEP 7 SCADA Linii de productie mentenanta senzori"
        assert screening_service._detect_candidate_domain(plc_text, {}, 3.0) == "INDUSTRIAL_HARDWARE"

        data_text = "Senior Data Engineer PySpark Databricks Medallion Architecture Delta Lake Big Data Analysis ETL"
        assert screening_service._detect_candidate_domain(data_text, {}, 4.0) == "DATA_ENGINEERING"

        qa_text = "QA Automation Engineer Cypress Selenium Playwright TestRail E2E automated test suites"
        assert screening_service._detect_candidate_domain(qa_text, {}, 3.0) == "QA_TESTING"

        fe_text = "Senior Frontend Developer React TypeScript Next.js Tailwind CSS HTML5 Figma UI components"
        assert screening_service._detect_candidate_domain(fe_text, {}, 4.0) == "WEB_FRONTEND"

        backend_text = "Software Developer .NET C# Node.js Docker PostgreSQL REST APIs"
        assert screening_service._detect_candidate_domain(backend_text, {".net": 2.0, "node.js": 1.5}, 3.5) == "WEB_BACKEND"

    def test_bidirectional_domain_compatibility(self):
        # Symmetrical compatibility: matching domain is 1.0
        assert screening_service._compute_domain_compatibility("WEB_BACKEND", "WEB_BACKEND")[0] == 1.0
        assert screening_service._compute_domain_compatibility("DATA_ENGINEERING", "DATA_ENGINEERING")[0] == 1.0
        assert screening_service._compute_domain_compatibility("EMBEDDED_AUTOMOTIVE", "EMBEDDED_AUTOMOTIVE")[0] == 1.0

        # Cross-domain penalties are fair and symmetric
        assert screening_service._compute_domain_compatibility("WEB_BACKEND", "DATA_ENGINEERING")[0] == 0.40
        assert screening_service._compute_domain_compatibility("DATA_ENGINEERING", "WEB_BACKEND")[0] == 0.40
        assert screening_service._compute_domain_compatibility("WEB_BACKEND", "EMBEDDED_AUTOMOTIVE")[0] == 0.20
        assert screening_service._compute_domain_compatibility("EMBEDDED_AUTOMOTIVE", "WEB_BACKEND")[0] == 0.20

        # Non-IT and blank templates get near-zero or zero
        assert screening_service._compute_domain_compatibility("WEB_BACKEND", "NON_IT")[0] == 0.02
        assert screening_service._compute_domain_compatibility("WEB_BACKEND", "BLANK_OR_TEMPLATE")[0] == 0.0

    @pytest.mark.asyncio
    async def test_fifteen_candidates_end_to_end_screening(self, db_session: AsyncSession):
        job_title = "Backend Developer"
        job_description = (
            "About the role: As a backend developer, you will contribute to designing, implementing and operating "
            "a system that supports the product requested features. We work with: Ruby on Rails, Dry-Rb, Sidekiq, "
            "Shoryuken, RSpec/minitest, AWS (S3/SQS/RDS/EKS), Redis, Datadog. Experience with Ruby on Rails or another "
            "backend language and willingness to learn Rails. Locations: Sibiu (Fully Remote)."
        )

        candidates = [
            CandidateItem(name="Adrian Vlădescu", cv_filename="Adrian_Vladescu_Rails_Dev.pdf", cv_raw_text="Ruby on Rails Developer. ApexCloud Labs Jan 2021 – Present. Ruby on Rails Rails Sidekiq Redis PostgreSQL AWS RSpec Docker Git."),
            CandidateItem(name="Victor Moldovan", cv_filename="Victor_Moldovan_Backend_Dev.pdf", cv_raw_text="Software Developer Sibiu Romania. NexusCore Technologies Oct 2022 – Present .NET C# Docker PostgreSQL GraphQL Redis Git. Vortex Digital Systems May 2021 – Oct 2022 Node.js TypeScript REST PostgreSQL."),
            CandidateItem(name="Simona Iacob", cv_filename="Simona_Iacob_Python_Dev.pdf", cv_raw_text="Backend Software Engineer Aether Dynamics Mar 2021 – Present Python FastAPI PostgreSQL Docker Redis AWS Git REST Event Sourcing."),
            CandidateItem(name="Radu Călinescu", cv_filename="Radu_Calinescu_DotNet_Dev.pdf", cv_raw_text="Backend Software Developer OmniSoft Enterprise Jun 2021 – Present .NET C# SQL Server REST Git Docker SOLID Clean Architecture."),
            CandidateItem(name="Dan Dumitru", cv_filename="Dan_Dumitru_Java_Backend.pdf", cv_raw_text="Java Backend Engineer Horizon FinTech Global Feb 2020 – Dec 2023 Java Spring Boot PostgreSQL Docker Microservices REST Git."),
            CandidateItem(name="Alina Petrescu", cv_filename="Alina_Petrescu_Node_Dev.pdf", cv_raw_text="Node.js Backend Developer PulseGrid Solutions Sep 2022 – Present Node.js TypeScript Express PostgreSQL GraphQL Docker Git."),
            CandidateItem(name="Cornel Diaconu", cv_filename="Cornel_Diaconu_Senior_Architect.pdf", cv_raw_text="Senior Software Architect Monolith Systems International Jan 2005 – Present Java C++ Oracle SQL Linux SOAP 19+ years experience. Education 2000 – 2005."),
            CandidateItem(name="Matei Sandu", cv_filename="Matei_Sandu_Junior_Intern.pdf", cv_raw_text="Junior Developer Intern AppLaunch Studio Mar 2025 – Aug 2025 JavaScript React HTML CSS Git student 3rd year."),
            CandidateItem(name="Roxana Enache", cv_filename="Roxana_Enache_Frontend_Dev.pdf", cv_raw_text="Senior Frontend Developer Prism UI Studios Jan 2020 – Present React TypeScript Next.js Tailwind HTML5 CSS3 Figma."),
            CandidateItem(name="Tiberiu Oprea", cv_filename="Tiberiu_Oprea_Data_Engineer.pdf", cv_raw_text="Senior Data Engineer DataSphere Analytics Jan 2021 – Present Python PySpark Databricks Delta Lake SQL ETL pipelines Hadoop."),
            CandidateItem(name="Laura Vasiliu", cv_filename="Laura_Vasiliu_QA_Automation.pdf", cv_raw_text="QA Automation Engineer VerifyQuality Labs Jan 2022 – Present Python Cypress Selenium Playwright Git CI/CD QA testing."),
            CandidateItem(name="Bogdan Cazacu", cv_filename="Bogdan_Cazacu_Embedded_Auto.pdf", cv_raw_text="Embedded Software Engineer AutoDrive Electronics Jan 2021 – Present Classic AUTOSAR Microcontroller CANoe Vector DaVinci ECU Embedded C C++."),
            CandidateItem(name="Marian Neagu", cv_filename="Marian_Neagu_Industrial_PLC.pdf", cv_raw_text="Inginer Automatist Mechatron Industrial Systems Feb 2021 – Present TIA Portal Siemens STEP 7 SCADA PLC linii de productie senzori."),
            CandidateItem(name="Costel Gheorghe", cv_filename="Costel_Gheorghe_Inginer_Textil.pdf", cv_raw_text="Inginer Textil Textile Craft Solutions 2018 – Present Gemini CAD Tipare textile confecții croitorie agroturism non-IT."),
            CandidateItem(name="Formular Standard HR", cv_filename="Formular_Evaluare_Standard.pdf", cv_raw_text="FIȘĂ DE EVALUARE CANDIDAT Scala de punctaj: 1 - 5 Document confidențial - uz intern Grilă de evaluare tehnică HR Date candidat Candidat:"),
        ]

        top_cand, results = await screening_service.screen_candidates_rag(
            db=db_session,
            job_title=job_title,
            job_description=job_description,
            experience_level="mid",
            candidates=candidates,
        )

        assert top_cand is not None
        assert len(results) == 15
        assert results[0]["is_selected"] is True

        # Verify top candidates are authentic backend developers matching the role
        top_names = [r["name"] for r in results[:3]]
        assert "Adrian Vlădescu" in top_names or "Simona Iacob" in top_names
        assert results[0]["match_score"] >= 80

        # Verify lowest ranks are non-IT and blank form
        lowest_names = [r["name"].lower() for r in results[-3:]]
        assert any("formular" in name or "costel" in name or "neagu" in name for name in lowest_names)
        assert results[-1]["match_score"] <= 5

    def test_tie_breaker_by_experience_years_sorting(self):
        """When match_score is identical, candidate with higher verified experience_years must rank higher."""
        items = [
            {"name": "Candidate A (4.7y)", "match_score": 97, "experience_years": 4.7},
            {"name": "Candidate B (7.3y)", "match_score": 97, "experience_years": 7.3},
            {"name": "Candidate C (5.3y)", "match_score": 97, "experience_years": 5.3},
            {"name": "Candidate D (Lower)", "match_score": 92, "experience_years": 8.0},
        ]
        sorted_items = ScreeningService.sort_candidates(items)
        assert sorted_items[0]["name"] == "Candidate B (7.3y)"
        assert sorted_items[1]["name"] == "Candidate C (5.3y)"
        assert sorted_items[2]["name"] == "Candidate A (4.7y)"
        assert sorted_items[3]["name"] == "Candidate D (Lower)"

