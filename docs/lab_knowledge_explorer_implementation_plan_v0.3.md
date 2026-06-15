# Lab Knowledge Explorer - Implementation Plan

Draft v0.3 | Baseline schedule: 12 weeks with 2 engineer-equivalents. Working draft - companion to lab_knowledge_explorer_spec_v0.3.md.

NOTE: Staffing is the hard dependency. This 12-week plan REQUIRES two engineer-equivalents: Eng-P (Python/ML) and Eng-I (Ruby/Decko/AWS). The stated 1-engineer team does NOT fit 12 weeks - see the 16-week single-engineer schedule in Section 6. The single-engineer 12-week path is not offered as realistic.

## Roles
- Eng-P -- Python/ML: pipeline, retrieval, synthesis, eval (Tracks A, C).
- Eng-I -- Ruby/Decko/AWS: fork, Cardtypes, MCP/REST, auth, webhooks, infra (Tracks B, C). OWNERSHIP TO BE NAMED (see Section 6 open dependency).
- Bio -- biologist (part-time, ~25%); BioInf -- bioinformatician (part-time, ~15%). Time budgets in Section 5.

---

## Week 0 -- Preflight gates (blocking, before any real-corpus work)
Eng-I (+ Eng-P):
- Provider governance: verify zero-retention / no-training settings and contractual terms for LlamaParse + Anthropic/OpenAI. SIGNOFF OWNER: project owner (Jane) or named engineering lead; EVIDENCE ARTIFACT: a "Provider Data-Handling Verification" section in the deploy runbook (date, owner, links). No confidential document is sent to any external API until this is signed off (mock/synthetic data only until then).
- Cloud security: AWS IAM least-privilege; S3 versioning + private bucket-of-record; secrets manager.
- Backups: configure automated RDS + S3 backups BEFORE any real-corpus upload (restore drill is later, Week 11).
- STAFFING DECISION GATE: if a named Eng-I is not assigned by end of Week 0, the active plan automatically becomes the 16-week single-engineer schedule (Section 6).

## Phase 1 -- Foundations (Weeks 1-4): Tracks A + B in parallel
| Wk | Track A (Eng-P) | Track B (Eng-I) |
|---|---|---|
| 1 | LibreOffice headless converter (.doc/.ppt); LlamaParse spike on pilot (mock/synthetic until Week 0 gate clears) | Fork Decko deck; stand up EC2/RDS/S3 from Magi-AGI pattern; enable automated backups |
| 2 | Parent-child chunker + semantic fallback; Streamlit chunk-review UI; deck parsing rules (slide text, speaker notes, bullet hierarchy, unanalyzed-visual flags) | Decko REST endpoint for file bytes + metadata + version/hash; ConstructRecord + entity/person Cardtypes; cloud security audit -> runbook |
| 3 | Ingestion worker consumes files VIA the Decko REST API (mocked locally) - not a folder scanner; file/version IDs (content hash) wired from the start; entity extraction via a temporary YAML/JSON dictionary seed (+ regex + NER) | JWT/role auth on MCP/REST; File upload -> S3 + async webhook; permissions batch-check endpoint (>=2 roles, mock data) |
| 4 | Index pilot corpus; smoke eval set (10-15 queries incl. negatives); embedding benchmark on smoke set -> PROVISIONAL model lock (decision rule below) | +parsed card write-back (Decko-owned); status states; manual ConstructRecord card renders in wiki |

Bio: provide pilot corpus (Wk1, ~2 d); chunk-boundary review incl. a deck subset (Wk2-4, ~5 d); annotate smoke eval (Wk4, ~2 d). BioInf: nomenclature/entity validation + embedding-benchmark support (Wk3-4, ~4 d).

### Embedding decision rule (Week 4 provisional lock)
- Sample coverage: the smoke set must span >=10 distinct constructs across all pilot doc types (ELISA notebooks, GLDC notebooks, method reports, minutes).
- Rule: pick the candidate with the best smoke recall@5 by a margin > 3 points AND acceptable latency/cost; if candidates are within 3 points, keep BGE-large (default - cheaper, no extra infra).
- This is a PROVISIONAL lock with a controlled reset path: if Phase 2/3 acceptance fails and failure analysis attributes it to embeddings, a controlled full re-index + re-validation is a scheduled contingency (cost: ~re-embed corpus + re-run Phase 2 gates).

### Deck validation (specific)
Subset: 5 converted decks from ABD presentations spanning both .ppt and .pptx and >=2 years. Must pass: slide text extracted; speaker notes captured where present; bullet hierarchy preserved; image/figure blocks flagged "unanalyzed." Bio reviews the subset in Wk4.

### Baseline vs acceptance targets (distinct)
Phase 1 MEASURES baselines (precision@5 and recall@5 on the smoke set). ACCEPTANCE TARGETS are set deliberately from stakeholder/domain expectation -- starting point precision@5 >= 0.7, recall@5 >= 0.6 (from the source critique/spec), to be confirmed with the project owner -- NOT defined as whatever the early prototype achieves.

Phase 1 exit criteria (demonstrable, with thresholds):
- Pilot converted+parsed+chunked+indexed; biologist reviews >=20 documents / >=150 chunks; >=80% of boundaries rated scientifically coherent.
- Both precision@5 and recall@5 baselines measured on the 10-15 smoke queries; acceptance targets agreed (not auto-set from prototype).
- Embedding model provisionally locked per the decision rule above.
- Ingestion reads via the Decko REST interface with version IDs (so Phase 2 is a routing/JWT switch, not a rewrite).
- Decko live on AWS with JWT/role auth; webhook fires on upload; batch-check correct for 2 roles on mock data; automated backups confirmed running.

## Phase 2 -- Integration & retrieval quality (Weeks 5-8): Track C
| Wk | Work | Who |
|---|---|---|
| 5 | Switch ingestion from mocked REST -> live Decko service-role (routing/JWT only); write Draft ConstructRecords; version pinning already in place | Eng-P + Eng-I |
| 6 | Dynamic permission gate (over-retrieve -> coarse pre-filter -> Decko batch authz -> backfill) with timeout budget + degraded response; fuzzy quote validation (earlier); secure logging/redaction + restricted prompt capture (earlier, before leak tests) | Eng-P + Eng-I |
| 7 | Lifecycle webhooks: idempotent CRUD + tombstoning; rename = delete-and-rebuild fallback (defer parent-rename cascade to post-MVP); basic permission-gate tests (earlier); promote YAML/JSON dictionaries -> Decko dictionary cards (alias change triggers reindex) | Eng-I + Eng-P |
| 8 | Acceptance eval set; full permission-leak tests (incl. adversarial relevance); citation-drift test; hardening -- not first implementation | Eng-P, Bio (~3 d annotate), BioInf (~2 d failure analysis) |

### Authz latency target -- load shape
p95 < 300 ms measured for a single batch authz check of up to 50 unique source_doc_card_ids (the dedup'd parent set from candidate_N <= 100), at pilot concurrency (<= 5 concurrent users, ~1-2 QPS). On slow: wait up to the budget then exclude. On unavailable/error: exclude those sources, return an auditable degraded-result flag. Unauthorized chunks never enter prompts, citations, logs, or traces.

Phase 2 exit criteria (HARD GATES -- GO/NO-GO for Phase 3):
- Permission-leak tests pass: 0 unauthorized content in results, prompts, logs, or citations, incl. the adversarial case; fail-closed verified (Decko down -> no leakage + degraded flag within latency budget).
- Quote grounding: 0 fabricated quotes on the acceptance set (fuzzy/offset validated).
- Source-version citation stability: citations survive a document-replacement test.
- Pilot retrieval quality meets the acceptance targets agreed in Phase 1.

CONTINGENCY: if any hard gate fails, Phase 3 does NOT start. The schedule slips to fix the failing gate; Phase 3 work (benchmark confirm, scale, deploy) cannot proceed on an ungated pipeline. Account for a 1-2 week buffer if gates slip.

## Phase 3 -- Refinement & deploy (Weeks 9-12): Track D
| Wk | Work | Who |
|---|---|---|
| 9 | Confirm embedding choice on the broader acceptance set (model locked Wk4 - this validates; controlled reset only if gates attributed failure to embeddings) | Eng-P + BioInf (~1 d) |
| 10 | Legacy-conversion scale test beyond pilot; performance/latency tuning (observability already in place from Wk6) | Eng-P + Eng-I |
| 11 | Restore DRILL + operational runbooks (automated backups already configured Wk0); assistant-chat frontend polish | Eng-I |
| 12 | User testing with 2 researchers; known-issues + post-MVP backlog | Eng-P + Bio (~2 d); Eng-I on standby for fixes |

Phase 3 exit criteria: two researchers independently answer construct questions without engineer support; embedding choice confirmed; deploy reproducible from runbook; restore drill passed; known-issues documented.

## Section 5 -- Reviewer (Bio/BioInf) time budget
- Bio ~ 15-18 days / 12 wks (~25%): corpus (Wk1, 2 d); boundary review incl. decks (Wk2-4, 5 d); synthesis-prompt review (Wk6, 2 d); eval annotation (Wk4 2 d + Wk8 3 d); user testing (Wk12, 2 d).
- BioInf ~ 9 days (~15%): nomenclature/entity validation (Wk3-4, 3 d); embedding-benchmark support (Wk3-4 + Wk9, 4 d); retrieval failure analysis (Wk8, 2 d).
- Neither reviewer role is the bottleneck; the engineers are (Section 6).

## Section 6 -- Staffing branch (explicit) + open dependency
- Primary: 12 weeks, 2 engineer-equivalents. Eng-I is a REQUIRED prerequisite, heavily loaded Wk0-8, ~50% Wk9-12.
- Single-engineer alternative: 16 weeks (sequential). Wk1-8: Decko/AWS foundations and the Python pipeline built sequentially (not parallel); Wk9-12: integration (Track C); Wk13-16: benchmarking, scale, refinement, deploy.
- Decision gate (Week 0): if no named Eng-I by end of Week 0, the 16-week schedule becomes active automatically.
- OPEN DEPENDENCY (for the project owner): name Eng-I source -- internal hire, contractor, or a borrowed Magi-AGI maintainer (the Decko/MCP stack overlap makes a maintainer the lowest-ramp option). The 12-week plan rests on this resource being owned.

## Section 7 -- Explicitly NOT in the MVP (no buried work)
- Local-only inference fallback -- architecture seam + governance requirement only; full build is a post-MVP backlog item with its own estimate.
- Parent-rename cascade propagation in Qdrant -- MVP uses delete-and-rebuild; active propagation deferred.
- Vision/OCR track; decks beyond the pilot validation subset; biomedical fine-tuning; user correction/learning loop; cross-department RBAC beyond Decko's native roles.

## Section 8 -- Top risks for reviewers to pressure-test
1. Eng-I dependency / ownership -- the 12-week commitment collapses to 16 weeks without a named second engineer.
2. Phase-2 hard gates all landing in Weeks 6-8 (gate + quote-grounding + version-stability + retrieval quality); 1-2 week buffer if they slip.
3. Decko fork/adapt effort -- new Cardtypes + batch-check endpoint + CRUD webhooks + versioning + early REST interface + dictionary-card migration; is "fork-and-adapt" really lighter than greenfield at this surface area?
4. Week-0 governance gate delaying real-corpus work if provider verification stalls.
