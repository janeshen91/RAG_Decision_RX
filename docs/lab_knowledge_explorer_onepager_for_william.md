# Lab Knowledge Explorer - MVP Summary (for sign-off)

**Prepared for:** William (co-founder) - approval to proceed
**Engagement:** Magi <-> Qcellect

---

## What it is
An internal AI search-and-summary tool over ETC's antibody-development documents -- meeting minutes, lab notebooks, method reports, and presentation slides. A researcher asks a question (or searches a keyword) and gets a **source-grounded answer**: when the documents record an actual decision, the tool lays out what was decided, why, and the supporting evidence with citations; when they don't, it cleanly summarizes what the documents *do* say instead of inventing a decision. Everything is delivered inside a wiki with a summary card for each document and keyword search.

## How it works
Word, PDF, and PowerPoint files are securely stored on AWS and processed with advanced document parsing. When a user asks the wiki's assistant a question, it quickly finds the most relevant passages and an AI composes a clear answer that **cites the quoted passages from the source documents** -- using only what the documents actually say.

## Timeline
**12 weeks, one engineer**, with part-time biologist and bioinformatician review:
- **Weeks 1-3:** Document ingestion + wiki (summary cards, keyword search)
- **Weeks 4-6:** Question answering with cited answers
- **Weeks 7-9:** Quality and accuracy evaluation
- **Weeks 10-12:** Interface polish, user testing with researchers, handover

(Reviewer involvement from Qcellect's biologist/bioinformatician is required at set points -- corpus hand-off, accuracy annotation, and user testing -- and is a scheduling dependency.)

## Cost
**~$5,000 / month, all-in** -- includes development, AWS hosting, and AI usage for the engagement. AI usage is covered up to a normal-usage allowance; sustained volume well above baseline (e.g. very high query loads or unusually large document dumps) would be reviewed and billed at direct pass-through cost. After the 12-week build, ongoing run-and-support cost is expected to be lower -- mainly AWS hosting + AI usage + light maintenance. *(Exact allowance and recurring figure to be confirmed in the engagement terms.)*

## Data & legal
Operates on the ETC Antibody Development document set. **Qcellect, as the data owner, authorizes the processing and holds the legal responsibility** for uploading and using those documents. On the technical side, external AI providers are used **only after their zero-retention / no-training terms are verified** -- a confirmed gate before any real documents are processed.

## In scope (this MVP)
Text documents (Word / PDF / PowerPoint); combined keyword + meaning-based search; cited answers (including decision records where decisions exist); wiki interface; an accuracy evaluation.

*Scope note:* the MVP is built and validated on a **pilot subset first**; broader ETC coverage follows once accuracy gates pass, with full-folder indexing possibly deferred to post-MVP if those gates slip.

## Out of scope (planned for later)
- Reading data out of images (gels, plots, micrographs).
- Per-user permission controls. The MVP runs behind a single **shared access boundary** (shared login / VPN / app-level auth) -- it is **not public** -- and assumes all authenticated pilot users may see all documents.
- Live document-edit syncing -- the MVP runs on a **fixed document snapshot** that is re-indexed manually when the corpus is updated.

These are deliberately deferred to keep the first version deliverable in 12 weeks, and are documented as the post-MVP roadmap.

## What sign-off enables
The start of the 12-week build on the ETC corpus, under the terms above.
