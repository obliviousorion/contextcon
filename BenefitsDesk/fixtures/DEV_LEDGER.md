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
| 16:37 | T2/T3/L1 live: 3 calls (2 sample rows), T3 unmatched person enrich (free) | 0.06 | Open-track cases recorded |
| 16:45 | E1 first run: 22 calls (role counts free, person-search counts) | 1.04 | leavers filter rejected (HTTP 400, free) |
| 16:47 | probe: past.end_date filter (400, free), 1 row with job history | 0.23 | found that past.end_date is not filterable |
| 16:49 | E1 rerun: person-search counts + 2 x 10 leaver rows with job history | 5.64 | leavers confirmed row by row |
| 16:44 | live smoke test (2 count-only queries, cache bypassed) | 0.00 | 3,434 / 114 reproduced |
| 16:46 | web fetch IRDAI document page + 2 PDF links | 3.00 | page fetched; PDFs not readable by web fetch |
| 18:05 | person enrich with education x2 (consenting personas) | 2.00 | guided v2 intake (after code freeze) |
| 18:07 | company search x2 (two 400s free, 15 then 13 results) | 3.24 | insurers from data |
| 18:08 | company enrich x3 insurers | 6.00 | headcount history, offices (check total 9.24 <= 10) |
| 18:10 | company enrich x2 employers | 4.00 | employer staff counts for the diary |
| | **Total** | **≈ 30.27 (≈ Rs 799)** | per-call rows for everything after 16:35 are in `state/desk.sqlite` (`bd ledger`) |
