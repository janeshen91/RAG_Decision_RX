# Lab Knowledge Explorer - Engineering Specification (MVP)

**Version 0.4 (Draft, rev. 2 - reviewer fixes applied)** - Lean MVP scope. Single-engineer build. Cited **decision-record** output over the ETC corpus via a Decko wiki.

> This v0.4 reconciles the rigorous v0.3 spec (now the **north-star / post-MVP reference**, `lab_knowledge_explorer_spec_v0.3.md`) with Jane's "For William" 12-week single-engineer direction. It keeps the rigor worth keeping (quote-grounding, evaluation discipline, citation-stable snapshots, light governance) and **defers the heavy items** (role permissions, lifecycle webhooks) to post-MVP -- subject to the access prerequisite in Section 2.

## 1. Product goal
Over unstructured ETC antibody-development documents (meeting minutes, lab notebooks, method reports, presentation decks), answer natural-language and keyword queries and return a source-grounded **decision record**. Retrieval is entity/construct-aware even though the output is a decision record (robust entity retrieval feeding decision-record synthesis). Surfaced through a Decko wiki with per-document summary cards and keyword search.

## 2. Scope (MVP) and the access prerequisite
**MVP access prerequisite (required for the permission deferral to be safe):** the MVP assumes **one shared access scope** -- every pilot user is authorized to see every indexed document. Deferring the permission gate (Section 3) is valid ONLY under this assumption. If any pilot document must be hidden from any pilot user, a minimal access boundary must be added before launch (do not launch on a mixed-access corpus without it).

**Not public:** even under one shared scope, the wiki/RAG app sits behind a single shared access boundary (shared Decko login / VPN / Cloudflare or app-level auth). "Per-user permissions deferred" means uniform access for **authenticated** pilot users -- not unauthenticated or open access.

**In scope:**
- Forked Decko wiki with **per-document summary cards + keyword search** + assistant chat.
- Ingestion: legacy `.doc`/`.ppt` conversion (LibreOffice) -> LlamaParse -> doc-type-aware parent-child chunking. **Deck rule:** extract slide text + speaker notes + bullet hierarchy; flag figures/images as *unanalyzed* (surfaced, not silently dropped).
- Hybrid retrieval: **BM25 (atomic-entity tokenizer) + BGE-large dense + RRF** + parent expansion; entity/keyword metadata.
- Synthesis: **decision record** with **fuzzy/normalized quote-grounding (0 fabricated quotes)**, citations, and confidence.
- **Citation-stable snapshot manifest** (Section 5) -- not deferred.
- Chunk-review UI (Streamlit); evaluation (smoke + acceptance). (Embedding model is **fixed on BGE-large** for the MVP; a biomedical benchmark is Phase-3 forward-looking analysis for post-MVP -- see Section 7.)
- **Light governance:** verify external-provider zero-retention / no-training terms before real-corpus processing (a launch gate; see Section 8).

**Summary cards must be governed by the same grounding rules:** each per-document summary card is either citation-backed (links to source passages) or clearly labelled AI-generated with source links. Summary cards are not an ungrounded hallucination surface.

## 3. Deferred to post-MVP (= v0.3 rigor)
Deferred deliberately (single shared-access pilot per Section 2; one engineer / 12 weeks):
- Role-based **permissions / dynamic Decko authz gate / leak tests / coarse pre-filter** (valid only under the Section 2 access prerequisite).
- **Lifecycle webhooks** (create/update/delete/rename/perm-change), tombstoning, permission-aware secure logging.
- **Local-only inference fallback.**
- **ConstructRecord richness** (timelines, contributors, entity cross-linking / knowledge graph) -- the v0.3 north-star output.

(Note: lightweight source-version/citation snapshots are NOT deferred -- see Section 5.)

## 4. Output - decision record
`{ decision_status, decision, stated_rationale[], evidence_summary, evidence[{quote, source_file, section, source_hash, parsed_text_hash}], sources[], confidence }`
- **`decision_status`** is `explicit_decision_found | no_explicit_decision_found`. Decisions are surfaced **only when explicitly stated** in the evidence (no inferred decisions). When `no_explicit_decision_found`, **`decision` is `null`** and **`evidence_summary`** captures what the documents do say -- the record never fabricates a decision to fill the field.
- Every `quote` is validated against retrieved text (fuzzy/normalized) before return; **0 fabricated quotes**.
- Each **`stated_rationale[]`** item is **quote-backed** (ties to an `evidence` entry) or explicitly labelled as a summary of evidence -- never an inferred "why".
- `confidence` reflects directness of evidence and corroboration.

## 5. Architecture (lean)
**Ingestion (offline):** convert (`.doc->.docx`, `.ppt->.pptx`) -> LlamaParse -> parent-child chunking (parent ~800-1200 tok; child ~256, ~10% overlap; regex boundaries + semantic fallback) -> embed children (BGE-large) to Qdrant + build BM25 over the same children. Source docs stored as Decko `File` cards (S3); per-document summary cards generated (citation-backed per Section 2).

**Ingestion trigger (MVP-simple):** a **manually-run CLI sync script**, OR a single **synchronous `on-save` Decko webhook** that POSTs the uploaded card ID to the Python RAG service. This uni-directional trigger replaces the deferred multi-event lifecycle machinery.

**Citation-stable snapshot manifest (required):** ingestion records, per document, `{ file_path, source_hash, parsed_text_hash, ingested_at }`. Evidence citations reference **`source_hash` and `parsed_text_hash`** so quote grounding stays stable even across a manual reindex or a parser change (replaces full source-version pinning for the MVP).

**Keyword search (scope-correct):** document **keyword/full-text search is powered by the RAG service's BM25 index**, exposed through the wiki's **assistant-chat panel via the MCP service** -- NOT by modifying Decko's core/global search. Decko's native global search stays limited to card titles and metadata. (Child chunks remain Qdrant/BM25-only, never Decko cards, so Decko's CQL cannot and should not be the full-text engine.)

**Query (online):** query (+ optional expansion / entity extraction) -> BM25 + dense -> RRF (k=60) -> parent dedupe + expansion -> decision-record synthesis (Claude/GPT-4o, configurable) -> quote validation -> render in the wiki.

**No permission gate in the MVP** (per Section 2 access prerequisite); see Section 3.

## 6. Corpus
Target: the whole **ETC Antibody Development** folder. ~400-450 text-ingestible `.doc/.docx/.pdf` documents (this count **excludes** the ~213 presentation decks, which are ingested separately for slide text/notes/bullets per the deck rule, with figures flagged unanalyzed). Images, Sanger traces, spreadsheets, and instrument data are deferred. **Pragmatic order:** Phase 1 ingests the clean **pilot subset** (P7 Wnt-3A ELISA, P9 GLDC, Method Reports, ABD meeting minutes) to validate conversion/chunking/retrieval; full-folder expansion is a Phase-3 step **gated on pilot acceptance** (see plan).

## 7. Evaluation & acceptance
- **Smoke set (Phase 1):** 10-15 pilot queries incl. negative/no-answer cases.
- **Acceptance set (Phase 3):** sized and categorized in the plan; explicit ground-truth + owner.
- **Metrics:** precision@5 / recall@5; fuzzy quote-grounding rate (0 fabricated); **decision/no-decision correctness** (ghost-decision negatives); confidence calibration.
- **Acceptance targets (provisional, owner to confirm):** precision@5 >= 0.7, recall@5 >= 0.6.
- **Embedding model:** the MVP is **fixed on BGE-large** (`bge-large-en-v1.5`). A biomedical/scientific-embedding benchmark runs in **Phase 3 as forward-looking analysis** (does a domain model materially beat BGE?) to inform a **post-MVP** reindex decision -- the MVP does not swap models mid-build.

## 8. Cost, commercial context & governance
~**$5,000/month all-in** (development + AWS hosting + AI usage) under the Magi-Qcellect engagement; AI token usage is included up to a normal-usage allowance, with sustained well-above-baseline volume reviewed/billed at pass-through cost (exact allowance is a commercial term to confirm). **Qcellect (the data owner) authorizes processing of the ETC corpus and carries the legal risk for it** -- but this does **not** relax technical confidentiality: external providers are used **only after their zero-retention / no-training terms are verified**, which is a **launch gate**.

## 9. Stack
LlamaParse + LibreOffice (convert); custom Python pipeline; Qdrant; rank_bm25; BAAI/bge-large-en-v1.5; Claude / GPT-4o synthesis (env-configurable); forked Decko (Rails/Postgres/S3) + MCP; Streamlit chunk-review; AWS (EC2/RDS/S3); Python 3.11+.

## 10. Risks & mitigations
| Risk | Mitigation |
|---|---|
| Decision-record output reintroduces decision-extraction risk | `decision_status` + explicit-only rule + ghost-decision eval negatives + quote-grounding |
| Mixed-access corpus assumed homogeneous | Section 2 access prerequisite as an explicit launch gate |
| Citations drift on a frozen corpus | Snapshot manifest (source_hash) referenced by evidence |
| Keyword-search scope creep into Decko core | BM25 via assistant-chat/MCP; Decko global search = titles/metadata only |
| Legacy `.doc`/`.ppt` conversion failures | Conversion stage + per-file fallback + status log |
| Embeddings miss antibody nomenclature | BM25-primary + entity exact-match; biomedical benchmark in Phase 3 (informs post-MVP swap, not mid-MVP) |
| Visual (deck) evidence implied but unread | Deck rule: extract text/notes/bullets, mark figures unanalyzed |
| Single engineer / 12 weeks slips | Local-first staging; deferrals (Section 3); pilot-first; eval/polish weeks as buffer |

## 11. Relationship to v0.3
`lab_knowledge_explorer_spec_v0.3.md` remains the **north-star / post-MVP** specification (construct-centric ConstructRecord, full permission/versioning/governance rigor). This v0.4 is the **build order** for the single-engineer 12-week MVP; the deferred items in Section 3 are the planned bridge back toward v0.3.
