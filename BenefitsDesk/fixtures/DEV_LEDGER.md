# Development credit ledger (Benefits Desk)

Live calls made while building, on the owner's personal key (owner approved all usage). Totals copied from
the SQLite ledger output at each step; the per-call rows for these discovery calls were lost when the dev
state file was reset at 16:35, so this table is the record for them. Later runs keep their rows in `state/desk.sqlite`.

| Time (IST) | Calls | Credits | What |
|---|---|---|---|
| 16:14 | job search group_by industries (count-only), person enrich x2 | 2.00 | industry value; two consenting personas |
| 16:16 | 11 job-search count queries (free), 1 row query (2 rows) | 0.06 | phrase counts; one 429 after retries, marked failed |
| 16:23 | web search | 1.00 | IRDAI insurer figures: news results only |
| 16:25 | web search (IRDAI site) | 1.00 | found a redirect link to an IRDAI PDF |
| 16:26 | web fetch | 1.00 | returned a Google redirect page, not the PDF: no figures |
| | **Total** | **5.06 (≈ Rs 134)** | |
