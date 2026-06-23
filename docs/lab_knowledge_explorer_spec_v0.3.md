# Lab Knowledge Explorer - Engineering Specification

**Version 0.3 (Draft)** - Construct-centric knowledge retrieval over the ETC antibody-development corpus, built on Decko + AWS.

> Status: working draft under multi-reviewer iteration (Claude drafts; Codex + Gemini review). This document is the canonical baseline for the implementation plan. Repo placement is provisional (see Section 16).

---

## 1. Product goal
A retrieval system over unstructured lab documents (meeting minutes, lab notebooks, method reports, presentation decks). Given a construct, vector, assay, experiment ID, researcher, or natural-language query, it retrieves and organizes all related evidence into a source-grounded **ConstructRecord**: what it is, where it was discussed, which experiments involved it, results/concerns, **who worked on it**, and how it evolved over time. Explicit decisions are surfaced **only when stated verbatim** -- never inferred. The system is surfaced through a Decko wiki frontend.

## 2. Framing assumptions
- **A1.** Construct-centric knowledge retrieval; decisions optional and quote-backed only.
- **A2.** Formats in-scope **with conversion**: `.doc/.docx/.ppt/.pptx/.pdf`. Deferred: standalone images, Sanger traces, spreadsheets, instrument data.
- **A3.** Stack = LlamaParse + custom Python pipeline + Qdrant; LlamaIndex is an optional helper, not a hard dependency.
- **A4.** Built on **Decko** (forked deck + MCP server) on **AWS (EC2/RDS/S3)**, mirroring the Magi-AGI deployment pattern.
- **A5. Pilot corpus (exact):** `P7 Wnt-3A ELISA` (~17 `.docx` + 12 `.doc`), `P9 GLDC` (~14 `.doc`), `Method Reports` (7 `.doc`), `ABD meeting minutes` (48 `.doc`). Conversion burden: ~70 `.doc` -> `.docx`; `.docx` subset zero-conversion. No decks in the pilot (deck handling validated separately).

## 3. Goals & non-goals
**In scope:** ingestion with legacy conversion; document-type-aware parent-child chunking; entity extraction (constructs/vectors/assays/experiment IDs/projects/**people**) with synonyms; Qdrant (dense) + BM25 (sparse) hybrid + RRF; LLM synthesis -> ConstructRecord with fuzzy quote grounding; **Decko wiki frontend + assistant chat**; **role-based access control (Decko authz, dynamically enforced at retrieval)**; **AWS deployment substrate**; chunk-boundary QA tooling.

**Out of scope (named gaps):** image/figure understanding (gels, FACS, micrographs -> vision track); sequence/instrument/spreadsheet data; **user answer-correction/learning loop** (distinct from chunk-boundary QA, which *is* in scope and only feeds boundary-rule tuning); fine-tuned/biomedical-trained embeddings (benchmarked, not trained); real-time sync. The **local-only inference path** (Section 13) is a required architecture capability but is **not MVP-complete**.

## 4. Corpus reality (drives hard requirements)
~2,000+ files; only **~400-450 text-ingestible** (`.doc/.docx/.pdf`); the majority by count is out-of-scope binary.

| Format | Handling |
|---|---|
| `.docx` | Direct LlamaParse |
| `.doc` (legacy, majority of text) | **Convert -> .docx**, then parse |
| `.pdf` | Direct; detect scanned -> defer |
| `.ppt/.pptx` (~213 decks) | **In-scope deck rule:** extract slide text + speaker notes + bullet hierarchy; `.ppt -> .pptx`; flag adjacent images/figures as *unanalyzed* (surfaced, not dropped) |
| images / `.ab1` / `.xls` / `.pzf` / instrument | **Deferred** (vision/data tracks post-MVP) |

Strong structure to exploit: named entities throughout; folder + filename encode `project / experiment / date`; provenance (doc numbers, dated filenames, attendees) supports citations and timelines. Filter `.DS_Store`/`Thumbs.db`/`.psd`/`.meg`; dedupe `.doc`/`.docx` pairs.

## 5. Architecture - three layers + canonical ownership
**Canonical owners (no dual source of truth):**
- **Decko owns:** source files (S3-backed `File` cards), the persisted `+parsed` Markdown card per source doc, permissions, entity cards, and **approved** ConstructRecords.
- **RAG service owns:** derived indexes (Qdrant), the BM25 index, parent/child chunk offsets, and ephemeral parse artifacts.

**Layer 1 - Decko wiki** (Rails, RDS Postgres, S3): source docs as `File` cards (each with one cached `+parsed` Markdown sub-card); `ConstructRecord` Cardtype with typed `+field` children; construct/project/assay/**person** entity cards cross-linked via the reference graph; permissions as cards; Draft/Published approval workflow; frontend = wiki UI + assistant chat (the `magi-assistant-wiki` SSE+MCP template).

**Layer 2 - RAG service** (Python, isolated container, new repo `magi-rag-service`): async ingestion worker -> convert -> LlamaParse -> parent-child chunk -> entity extract -> embed -> Qdrant + BM25. Query path per Section 7. Reads/writes cards via the Decko MCP/REST API (JWT/role auth) -- "just another MCP client."

**Layer 3 - AWS:** EC2 (Decko/Thin/Nginx, RAG service, Qdrant), RDS Postgres (Decko), S3 (docs/attachments), Cloudflare front.

## 6. Ingestion orchestration & index lifecycle
**Async worker (parse billed once/file):** on `File` card create, Rails fires an async webhook -> worker reads the bytes **via a Decko service-role API path or a Decko-provided S3 object key + version** (never an independent S3 layout) -> LibreOffice headless convert (isolated container) -> LlamaParse -> writes the cached **`+parsed` Markdown card** (Decko-owned) -> chunk/index run from the cached card. Per-file status states surfaced on the card: `uploaded -> converted -> parsed -> partial -> failed -> deferred`.

**Versioning:** every chunk and Evidence record is pinned to an exact source revision (`source_doc_version` / `content_hash`). Vectors tie to a specific file revision.

**Lifecycle webhooks (mirror exact wiki state):** Decko emits **create / update / delete / rename / permission-change** events on all indexed card types. The RAG service exposes endpoints that:
- **Invalidate/tombstone** all chunks matching a `source_doc_card_id` on delete/replace.
- **Idempotently reindex** with idempotency keys; reindex jobs are **versioned** and **reject stale completion** if a newer file/permission version exists (ordering/race-safe).
- Re-sync **coarse permission tags** (Section 7) on permission-change.

## 7. Retrieval & the permission gate (security-critical)
Pipeline:
1. Query -> optional expansion + entity extraction.
2. **Entity exact-match pre-filter** (Qdrant metadata keyword filter on extracted constructs/aliases) + **coarse role pre-filter** (broad optimization; see below).
3. **Over-retrieve** `candidate_N` (configurable, default ~100, max cap configurable) via **BM25** (atomic-entity tokenizer -- primary for exact construct/plasmid codes) **+ dense** (`BAAI/bge-large-en-v1.5`, 1024-d, cosine, normalized), paginating both -> **RRF** (k configurable, default 60) -> parent dedupe.
4. **Dynamic Decko batch authorization -- the only correctness gate.** Pass the caller's Decko JWT/role; batch-check candidate **`source_doc_card_id` and `parsed_card_id`** (the `+parsed` card inherits exactly the source `File` card's read permission) against Decko's read rules. **Fail closed:** on Decko API timeout/error, those sources are excluded and the response carries an auditable **degraded-result** flag.
5. **Backfill** across the paginated candidate pool until `authorized_top_k` (configurable, default ~10) authorized parents are found or the candidate cap is reached; **log pool exhaustion**.
6. Bounded parent expansion via stored **offsets into the pinned `+parsed` Markdown revision** (not the original binary `File` bytes), fetched by content hash.
7. Synthesis -> fuzzy/normalized quote validation with offsets.

**Coarse role pre-filter (Section 7.2):** a broad recall optimization -- sync coarse group/role tags to Qdrant so the candidate pool is populated with potentially-accessible chunks, avoiding post-filter recall collapse. It is **never sufficient or authoritative**; it has periodic consistency checks vs Decko, supports **fallback widening**, and candidate generation must be able to proceed **without** it in degraded/debug mode (dynamic Decko authz still gates).

**Invariant:** unauthorized chunks never appear in prompts, citations, user-visible traces, or normal application logs.

## 8. Data model
- **ConstructRecord**: `entity, summary, timeline[], evidence[], related_entities[], contributors[], source_documents[], explicit_decisions[], confidence` + provenance/lifecycle: `generated_at, generated_by_model, pipeline_version, source_chunk_ids[], approval_status, approved_by, approved_at`.
- **Evidence**: `quote, source_doc_id, source_doc_version|content_hash, parent_id, child_id, quote_start/end (normalized locator into +parsed revision), section, slide_or_page, doc_type`.
- **TimelineEvent**: `date, description, evidence_ids[]` (must cite Evidence, not just a filename).
- **explicit_decisions[]**: quote-backed objects `{decision_text, actor?, date?, evidence_id}`; `null` for missing fields; **no inferred summaries**.
- **contributors[]**: people/researchers extracted from authorship/attendees, linked to entity cards.
- **Chunk metadata**: `node_id, parent_id, source_doc_card_id, parsed_card_id, source_doc_version, filename, doc_type, project, experiment_id, date, contributors[], construct_names[], section_index, child_index, coarse_roles[]`.

## 9. Synthesis & grounding
Prompt instructs *organize evidence*, not summarize; cite every excerpt; separate evidence from inference; populate `explicit_decisions` only when stated; never fabricate. **Quote validation is normalized/fuzzy with offsets** (exact substring fails on OCR/parser normalization, hyphenation, whitespace, tables).

**Confidence is two-axis** -- *directness of evidence* x *cross-source corroboration* -- so a single authoritative method report can be **high**, not auto-medium. Rendered as `high | medium | low` with both axes recorded.

## 10. Component specs (deltas from prose above)
| Component | Key points |
|---|---|
| Converter | LibreOffice headless; scanned-PDF detection; retry/fallback; status states |
| Parser | LlamaParse; tables preserved atomic; speaker-notes/bullet extraction for decks |
| Chunker | Parent-child; per-doc-type regex boundaries + semantic fallback; chunk-review-tunable |
| Entity extractor | **Hybrid**: filename/folder regex + **domain dictionary/aliases (Decko cards, biologist-editable)** + LLM/NER + **synonym normalization** (first-class); includes **people/contributors**; alias changes trigger reindex |
| Indexer | Qdrant (`bge-large-en-v1.5`, normalized cosine) + BM25 (atomic-entity tokenizer) |
| Retriever | Section 7 pipeline; configurable `candidate_N`/`authorized_top_k`/cap |
| Synthesizer | configurable Claude / GPT-4o (Section 13 governance); fuzzy quote validation; enriched schema |
| Chunk-review UI | **Streamlit** (Track A); archived after boundary freeze |
| Decko bridge | MCP/REST client (JWT/role): write Draft ConstructRecords + `+parsed` cards; batch permission checks; lifecycle webhooks |

## 11. Evaluation & acceptance
- **Smoke set (Phase 1, Week 4):** 10-15 pilot queries incl. **negative/no-answer** cases.
- **Acceptance set (Phase 2):** broader; by doc type; construct/assay/timeline/contributor coverage; explicit ground-truth definition (what counts as a correct ConstructRecord / relevant doc).
- **Metrics:** precision@5 / recall@5; **fuzzy quote-grounding rate (0 fabricated)**; entity-extraction accuracy; timeline correctness; confidence calibration.
- **Acceptance targets (provisional, pending project-owner confirmation):** precision@5 >= 0.7, recall@5 >= 0.6. Targets are set deliberately (from stakeholder/domain expectation), **not** derived from the prototype's own output; Phase 1 measures baselines, targets are confirmed before Phase 2 gating.
- **Permission-leak tests:** >=2 roles with overlapping/restricted access, **including cases where unauthorized docs are more semantically relevant than authorized ones** (the recall-collapse adversarial case); prove restricted content is absent from results, prompts, logs, and citations.
- **Citation-drift tests:** after source document update/replacement (offsets must remain valid or re-resolve).
- **Embedding benchmark (Phase 1, Weeks 3-4):** BGE-large vs **biomedical/scientific embedding candidates** (e.g. PubMedBERT, SPECTER2, others) on the smoke set, producing a **provisional model lock** before Phase 2 (see the plan's decision rule).

## 12. Observability
Per-query logs by default capture **prompt metadata/hash + retrieved chunk IDs + RRF ranks + latency + conversion/parse failures + caller role**. **Full-prompt capture is disabled unless in restricted debug mode.** Logs have redaction/restricted access, a retention policy, and no cross-role visibility -- logging must not become a permission bypass.

## 13. Data governance (external-service handling)
The corpus is **confidential biotech IP** (no PHI expected, but treat as sensitive). LlamaParse and the synthesis LLM (Claude/GPT-4o) send document content to external services.
- **Approved providers only**, configured for **zero data retention + no training on inputs**.
- **Acceptance criterion (gating):** the deployment **must not process confidential documents through any external API until the account/org data-handling settings and contracts are verified** for that provider -- verification is a deployment checklist item, not an assumption.
- Secrets via a secrets manager (never in cards/repo).
- **Local-only fallback path** (local parser + self-hosted embeddings + local LLM) is a **required architecture capability** for the most sensitive material, configurable per-corpus -- but **not MVP-complete** (budgeted as a post-pilot item; see plan).

## 14. Infrastructure & operating cost
MVP scale (100-1,000 docs, 10-20 researchers, 100-500 queries/day):
| Option | Monthly |
|---|---|
| A - single VM + API LLM | $130-580 |
| **B - local embeddings + cloud LLM (recommended)** | $180-820 |
| C - fully self-hosted GPU | $350-1,100 |
Budget **~$500/month**, expected under for the first months. Drivers: EC2/RDS/S3 (~$100-250), LlamaParse ($20-100), LLM inference ($50-500). Department rollout (50-100 users) -> $1-3k/mo, mostly LLM query volume. Infra cost is negligible vs the cost of validating retrieval quality and adoption.

## 15. Risks & mitigations
| Risk | Mitigation |
|---|---|
| Legacy conversion fails on a subset | Conversion stage + per-file fallback + status log; digital-native first |
| Chunk boundaries split scientific context | Chunk-review UI week 1; semantic fallback; biologist gate |
| Embeddings miss antibody nomenclature | BM25-primary + entity exact-match filter; biomedical benchmark Phase 1 |
| Visual evidence excluded -> incomplete answers | Named gap; deck visual-placeholder flags; vision track post-MVP |
| Permission leak via stale vectors | Dynamic Decko authz (authoritative, fail-closed); coarse tags non-authoritative + consistency-checked |
| Stale index on rename/delete/permission change | Lifecycle webhooks; versioned idempotent reindex; tombstoning |
| Decko API failure on the gate | Fail closed + degraded-result flag |
| Dual-write inconsistency | Single bucket-of-record; canonical ownership (Section 5) |
| Approval-workflow bottleneck | Draft-by-default; human approval async; generated never overwrites approved |
| Local-fallback scope creep | Capability-but-not-MVP-complete; explicitly budgeted |
| 12-week scope slip | Parallel tracks (Section 16); pilot corpus first; Streamlit not custom UI |

## 16. Implementation shape & repository boundary
**Parallel tracks (detailed week-by-week in the implementation plan):**
- **Track A - Python pipeline/algorithmic:** ingestion via a mocked Decko REST interface (not a folder scanner -- so Phase 2 is a routing switch, not a rewrite), chunker, entity extractor, Qdrant/BM25 retrieval + synthesis, Streamlit chunk-review, eval datasets.
- **Track B - Decko/AWS/infra:** AWS standup, forked Decko + Cardtypes, MCP/REST API incl. **permissions batch-check endpoint**, JWT auth, lifecycle webhooks, file versioning, backup/restore, runbooks -- on mock RAG responses.
- **Track C - integration & validation:** wire RAG into the Decko frontend; verify security gates; run adversarial role-based eval; transition the pilot corpus.
- **Track D - refinement & deployment:** embedding-benchmark confirmation (model locked in Phase 1), legacy-conversion scale testing, runbooks, deployment.

**Repository boundary:** the Python RAG pipeline lives in a new dedicated repo **`magi-rag-service`** (decoupled microservice) alongside the Decko fork. The spec + implementation plan stay in the current repo's `docs/` until `magi-rag-service` is provisioned, then migrate. The implementation plan must explicitly identify the eventual `magi-rag-service` boundary and not treat Decko/AWS as a thin wrapper.

## 17. Deliberate deviations & deferred items
- **Decision typing:** the earlier critique proposed `DecisionType {explicit, implied, uncertain, no_decision_found}`. We **intentionally surface explicit decisions only** (quote-backed, no inference) -- the construct-centric pivot deprioritizes decision reconstruction. *Implied/uncertain* decisions are deliberately **not** produced.
- **MiniCOIL / learned sparse:** noted in source material as a possible BM25 successor; kept as a **post-MVP** retrieval option, not in the MVP (BM25 first for interpretability/cost).
- **Vision/OCR track** (figure/gel/FACS understanding), **sequence/instrument data**, **fine-tuned embeddings**, **user correction/learning loop**, **local-only inference completeness** -- all deferred, named here so they read as choices.

## 18. Open questions
1. Decks: the MVP validates slide-text/notes/bullet extraction on a 5-deck subset. Should ingestion expand to the full ~213-deck corpus within the MVP, or stay limited to the validation subset until the vision/OCR track?
2. Backfill/over-retrieval defaults (`candidate_N`, `authorized_top_k`, cap) -- tune against the recall-collapse eval before locking?
3. Embedding model: ship BGE-large and benchmark biomedical in Phase 1 (current plan) -- sufficient, or benchmark before any indexing?
4. Local-only fallback: how hard a requirement for the pilot vs a documented post-pilot capability?
