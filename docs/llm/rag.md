# RAG & Vector Retrieval (`llm/rag.md`)

## 1. Overview
Multi-candidate RAG screening pipeline integrating semantic chunking, section-aware timeline/tenure extraction, vector embeddings, and PostgreSQL pgvector cosine similarity search.

## 2. Chunking & Timeline/Tenure Extraction (`llm/chunking.py`)
- **LangChain `RecursiveCharacterTextSplitter` Integration**:
  - `SemanticTextSplitter` leverages LangChain's `RecursiveCharacterTextSplitter` from `langchain-text-splitters` for bounded, overlapping chunking while respecting semantic separators (`\n\n`, `\n`, sentence endings).
- **`TimelineExtractor`**:
  - **Section Demarcation**: Detects sections (`EXPERIENCE`, `EDUCATION`, `PROJECTS`, `SKILLS`) and academic degree keywords (`B.Sc.`, `M.Sc.`, `Bachelor`, `Master`, `High School`, `Cybersecurity`, etc.).
  - **Education & Projects Isolation**: High school, university degrees (`B.Sc.`, `M.Sc.`, `Licență`, `Master`), volunteering, courses, and personal/academic projects (detected via section headers and `PROJECT_KEYWORDS_REGEX` matching personal, side, pet, hobby, diploma, or student projects) are classified with `is_work=False` and strictly excluded from professional career duration and tech tenure calculations.
  - **Date Interval Parsing**: Detects date intervals in English & Romanian formats (`Oct 2025 – Present`, `May 2024 - Oct 2025`, `Jan 2022 – Dec 2024`, `06/2024 – 07/2024`, `2018 – 2022`).
  - **Overlapping Interval Deduplication (`calculate_total_work_experience`)**: Uses set union of active employment months to prevent double-counting concurrent roles, returning non-inflated total career experience.
  - **Technology Tenure Weights (`calculate_tech_tenure`)**: Computes exact cumulative employment duration per technology (e.g. 1.0 year for .NET, 1.5 years for Git) exclusively across verified employment roles (`is_work=True`), ignoring personal projects or academic degrees.
  - **Structured Work History**: Generates verified employment blocks and detailed timeline summaries.
- **`SemanticTextSplitter`**:
  - `split_cv_with_timeline`: Preserves role and duration context by prefixing chunks with `[Role (Interval, Duration)]: `.
  - Returns `(chunks, timeline_summary, tech_tenure, work_history, experience_years)`.
  - Standard recursive splitting on semantic boundaries via LangChain.

## 3. LangChain Embeddings & pgvector Retrieval
- **LangChain `OllamaEmbeddings`**:
  - JD queries and CV chunks use LangChain's `OllamaEmbeddings` (`langchain-ollama`) or native async REST configured with `nomic-embed-text` (768 dimensions). Strictly fails fast with explicit error if model is missing or offline.
- **LangChain `JsonOutputParser`**:
  - Candidate evaluation JSON payloads parsed reliably using `JsonOutputParser` from `langchain-core`.
- **Vector Search & Relational Isolation (`cv_chunks`)**:
  - PostgreSQL `cv_chunks` table includes `candidate_id` (indexed UUID) linking directly to `candidates.id`.
  - Chunks and vector similarity searches are strictly isolated per candidate (`WHERE CVChunk.candidate_id == c_id`), completely preventing chunk pollution or overwrites between candidates with identical names.
  - Search order: `order_by(CVChunk.embedding.cosine_distance(jd_embedding))`.
- **Tenure Weighting**:
  - LLM instructions explicitly evaluate experience duration (rewarding sustained experience in required technologies, penalizing and flagging short exposure <= 3 months as gaps).
  - Domain compatibility and tenure analysis dynamically weight candidate alignment based on verified employment duration.
  - Primary skill badges dynamically select core frameworks/languages with their own exact verified tenure.
- **Observability & Logging**:
  - Full structured logs (`logger.info`) for each parsed block (section, `is_work`, `is_education`, role, dates, duration, detected stack).
  - Clean tech tenure breakdown and final scoring summaries printed on every candidate screening pass.

## 4. Generic & Symmetric Domain Alignment Engine (`ScreeningService`)
- **Zero-Hardcoding Principle**:
  - The screening engine is 100% role-agnostic, generic, and bidirectional, complying strictly with Section 7 of `AGENTS.md`. No hardcoded candidate names, cities, test ladders, or target stack biases.
- **Dynamic Domain Detection (`_detect_job_domain` & `_detect_candidate_domain`)**:
  - Automatically identifies domain categories from the Job Description and CV texts independently:
    - `DATA_ENGINEERING`, `AI_ML`, `EMBEDDED_AUTOMOTIVE`, `INDUSTRIAL_HARDWARE`, `QA_TESTING`, `MOBILE`, `DEVOPS_CLOUD`, `FULL_STACK`, `WEB_FRONTEND`, `WEB_BACKEND`, `GENERAL_SOFTWARE`, `NON_IT`, and `BLANK_OR_TEMPLATE`.
  - Signal density and dominant keyword counts (e.g. comparing non-web domain keywords vs. backend hits, parsing primary job headers) prevent keyword traps (such as Python in ETL pipelines vs. web APIs, or C++ in automotive ECUs vs. application development).
- **Exact Word Boundary & Punctuation Guard Matching (`_match_technologies`)**:
  - Strict regex word boundary guards (`\b` and symbols like `.NET`, `C#`, `C++`) prevent catastrophic false positives (e.g., matching "REST" in "Somarest" textile factories or "Go" in Romanian words like "psihopedagogică").
- **Symmetric Domain Compatibility Matrix (`_compute_domain_compatibility`)**:
  - Evaluates domain alignment symmetrically:
    - Matching domains: 1.0 coefficient.
    - Full-stack / adjacent web disciplines: 0.85 - 0.95.
    - Software cross-disciplines (e.g. Data vs. Web): 0.40.
    - Hardware/Embedded vs. Web: 0.20.
    - Non-IT profiles: 0.02 max.
    - Blank HR sheets or template forms: 0.00.
  - Bidirectionally verified: Evaluated for a Data Engineer JD, a Data Engineer ranks #1; evaluated for an Embedded JD, an Embedded Engineer ranks #1; evaluated for a Web Backend JD, a Backend Developer ranks #1.
- **Tenure-Weighted Candidate Calibration (`_compute_candidate_metrics`)**:
  - Factors in verified tenure on required skills (rewarding >= 3 years sustained experience, flagging exposure <= 3 months as gaps).
  - Evaluates seniority fit against target level (e.g. flagging 20+ years as overqualified for mid-level roles, or < 1 year as junior/intern).
  - Dynamically synthesizes Romanian summary, strengths, and actionable gaps without any predetermined text or artificial heuristics.
- **Same-Domain Alternative Stack Recognition**:
  - Backend developers with alternative stacks (.NET, Java, Python, Node, Go) applying for Ruby on Rails (or vice-versa) are recognized for transferable foundations (APIs, SQL, ORMs, design patterns, microservices), calibrating their scores between 45-70% cleanly above unrelated disciplines (Data/ML at 20-30%) and incompatible hardware domains (Embedded/PLC at 10-20%).

