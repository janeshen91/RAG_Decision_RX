# Lab Knowledge Explorer - Implementation Plan (MVP)

**Version 0.4 (Draft, rev. 2 - reviewer fixes applied)** - Single engineer (Lake), ~12 weeks, lean MVP scope (companion to `lab_knowledge_explorer_spec_v0.4_mvp.md`).

> Supersedes the 2-engineer framing of plan v0.3 (now the post-MVP north-star reference). 12 weeks solo is feasible **because** the heavy items -- role permissions, lifecycle webhooks, secure permission-aware logging -- are deferred (spec v0.4 Section 3), AND because Phase 1 is **local-first** (cloud cutover deferred to Week 4). Maps to Jane's 4 x 3-week structure.

## Team
- **Engineer: Lake** (sole builder).
- **Bio** + **BioInf** (Jane's team) -- part-time reviewers at defined points only. Budgets at the end.

## Week 0 - Preflight
- **Provider governance (launch gate):** verify zero-retention / no-training terms for LlamaParse + Anthropic/OpenAI before any real-corpus processing. Qcellect authorizes processing and carries legal risk, but provider terms are still a hard gate -- this does not make governance optional.
- **Access-scope confirmation:** confirm the MVP runs on **one shared access scope** (all pilot users may see all indexed docs). If not, a minimal access boundary is added before launch (spec Section 2). The app is **not public** -- it sits behind a shared access boundary (shared Decko login / VPN / app-level auth); deferring per-user permissions is not the same as no auth.
- **AWS prep (background):** accounts, IAM least-privilege, private S3 + automated backups, secrets manager -- developed in parallel, not on the critical path until Week 4.
- Until governance clears, work on mock/synthetic data only.

## Phase 1 (Weeks 1-3) - Ingestion + wiki, LOCAL-FIRST
**Local-first, cloud-second rule:** run the forked Decko + Postgres + Python RAG service **locally** (Docker Compose) for Weeks 1-3; validate ingestion/retrieval/keyword-search locally; AWS is built in parallel as a background task; the cloud push + S3 cutover happens in **Week 4** once local code is frozen.

**Deliverables:** local Decko fork + Postgres + RAG skeleton; converter (`.doc/.ppt`) incl. deck rule (text/notes/bullets + unanalyzed-figure flags); LlamaParse; parent-child chunker + **Streamlit chunk-review UI**; embed -> Qdrant + BM25; **ingestion trigger** (manual CLI sync script, or simple synchronous on-save webhook POSTing card ID); **snapshot manifest** (file_path, source_hash, parsed_text_hash, ingested_at); **per-document summary cards (citation-backed) + keyword search via the assistant-chat/BM25 path** (not Decko global search); ingest the **pilot subset** (P7/P9/Method Reports/minutes).
**Bio:** boundary review in the chunk-review UI; provide/confirm pilot corpus.
**Cut line:** if local Decko/converter slips, keep the pipeline + chunk-review UI running on plain local files first and defer wiki/assistant polish; do not let infra block pipeline validation.
**Exit criteria:** pilot ingested + indexed locally; **biologist confirms >=80% chunk boundaries coherent (>=20 docs reviewed)**; keyword search + citation-backed summary cards usable; chunk-review operational; snapshot manifest produced.
**Fallback exit (if the cut line is invoked):** the pipeline + chunk-review + a **CLI keyword search** meet the Phase-1 bar, and the **in-wiki summary-cards + keyword search slip to Week 4** (cloud cutover). If neither the wiki nor a CLI search is ready, Phase 1 slips rather than being declared done.

## Phase 2 (Weeks 4-6) - Cloud cutover + query + synthesis
**Week 4:** cloud cutover (deploy local-frozen stack to AWS EC2/RDS/S3).
**Deliverables:** hybrid retrieval (BM25 atomic-entity + BGE dense + RRF) + parent expansion; **decision-record synthesis** with `decision_status` (explicit_decision_found | no_explicit_decision_found), fuzzy quote-grounding, citations (by source_hash), confidence; query interface (wiki assistant-chat + CLI).
**Exit criteria:** end-to-end query returns a **quote-grounded decision record** in ~10s that **cites all supporting retrieved evidence (>=2 sources when available/expected)**; **0 fabricated quotes** on a 10-query manual check (biologist-verified); `no_explicit_decision_found` returned cleanly (with evidence summary) when no decision is stated.

## Phase 3 (Weeks 7-9) - Quality + evaluation
**Deliverables:** acceptance eval; prompt iteration; **biomedical-embedding benchmark as forward-looking analysis** (the MVP stays on BGE-large; a domain model that materially wins informs a **post-MVP** reindex, not a mid-MVP swap); full-folder expansion (gated, see below).
**Evaluation spec:**
- **Acceptance set: 30-50 queries**, owned by **Bio (ground-truth annotator)**, spanning categories: construct/assay lookups, "what was decided" (explicit), **ghost-decision negatives (>=3: a decision discussed or deferred but NOT made -> must return `no_explicit_decision_found`)**, and no-answer/out-of-corpus cases.
- **Metrics + pass/fail:** precision@5 >= 0.7 and recall@5 >= 0.6 (provisional, owner-confirmed); **0 fabricated quotes**; **ghost-decision cases all pass**; decision/no-decision labels correct on >=90% of decision-bearing queries.
**BioInf:** nomenclature/entity validation; retrieval failure analysis.
**Full-folder expansion (gated):** runs **only after pilot acceptance passes** (Phase 3 gates met), so it never competes with evaluation -- realistically late Phase 3 into Phase 4, and only if the **Phase 2 manual-query gate** (end of Week 6) already passed. If acceptance slips, full-folder indexing becomes a post-MVP item and the MVP ships validated on the pilot (plus any already-indexed sampled subset).
**Exit criteria:** acceptance gates met on the pilot; embedding choice confirmed; expansion scope decided per the gate.

## Phase 4 (Weeks 10-12) - Wrap-up
**Deliverables:** wiki + assistant-chat polish; **user testing with 2 researchers**; deploy runbook + **backup/restore drill**; known-issues + **post-MVP backlog** (deferred permissions/versioning/governance rigor from v0.3).
**Exit criteria:** two researchers answer real questions **unaided**; deploy reproducible from the runbook; restore drill passes; backlog documented.

## Reviewer time budget
- **Bio ~12-15 days:** pilot corpus (Wk1); boundary review (Wk1-3); synthesis-prompt + manual-query verification (Wk4-6); **acceptance ground-truth annotation (Wk7-8)**; user testing (Wk12).
- **BioInf ~7-9 days:** nomenclature/entity validation + embedding-benchmark support (Wk7-9); failure analysis (Wk8).
- These are **hard dependencies on Jane's team availability** at those weeks; slippage in reviewer availability slips the corresponding exit gate.

## Explicitly NOT in these 12 weeks (post-MVP)
Role permissions / dynamic authz gate / leak tests; lifecycle webhooks, tombstoning; permission-aware secure logging; local-only inference fallback; ConstructRecord richness (timelines/contributors/graph). Full treatment lives in spec + plan **v0.3**. (Lightweight citation snapshots ARE in the MVP -- spec Section 5.)

## Honest risks
1. **Solo across Decko fork + AWS + pipeline + wiki in 12 weeks is tight.** Local-first staging (Phase 1) removes AWS from the Week 1-2 critical path; the eval/polish weeks (7-12) are the buffer.
2. **Decko is fork-and-adapt of the existing Magi-AGI stack** -- the 12-week math depends on that reuse holding (not a greenfield Rails build).
3. **Full-folder expansion** runs late Phase 3 / Phase 4 (after acceptance) and is gated so it never competes with the eval gates.

## Relationship to v0.3
This is the MVP build order. The deferred items above are the bridge back toward the v0.3 north-star (construct-centric, permissioned, versioned, governed).
