# #18 — Benefits Desk

Back to the [leaderboard](../README.md). Follows [RULES.md](RULES.md).

- **Owner:** Atishay6571
- **Created:** 2026-11-22 15:35
- **Status:** Proposed
- **Parents (if a merge):** none
- **Round 1 score:** not scored yet (RULES §5.1 review pending)
- **Round 2:** not played

## 1. One-line pitch
An insurance desk for the client's workforce: employer side designs the cover; employee side tells each person what they have, what's missing, what to do.

## 2. The problem and the paid job
- **Client:** the logistics company in the problem statement, as the employer of its staff, drivers and delivery partners. **Track:** Open.
- **Who is paid for this job today:** employee-benefits brokers and insurance advisers, on commission.
- **Today's price:** UNKNOWN. No commission rate card, broker disclosure or regulation has been sourced yet; a sourced commission figure is needed before any rupee comparison.

## 3. Why it's unique
- **Which track examples it is not:**
  - not the Handbook's insurance example, 4.1 The Underwriting Desk, which insures a *business* from its application; this desk advises the client's *employees* and designs the client's own group cover;
  - not a hiring screener: job posts are read only for the benefits employers promise, never to judge a candidate.
- **Why other teams won't build it:** UNKNOWN. The owner has not stated this yet.
- **Nearest existing idea:** [#14 Notice-Period Alert](14-notice-period-alert.md) also watches named people's job changes, and was dropped as surveillance with a weak purpose. Benefits Desk differs in that only people who opt in are watched, and the purpose (their own cover ending) is stated to them. It is not a duplicate of any idea on the leaderboard.

## 4. The service: request types
| Request | Input | Output | Irreversible? |
|---|---|---|---|
| Employer: benefits benchmark | role group (drivers, warehouse staff, office staff) | count of recent job posts from similar employers that mention each benefit, with the filter and as-of date, and the note that job posts understate what employers offer | No |
| Employer: cover package proposal | the benchmark, plus the client's staff groups | a proposed cover package for drivers, warehouse staff and office staff | No |
| Employer / employee: insurer shortlist | the cover type | insurers shortlisted on regulator figures (claims settled, complaints), each with source and date; ranked without regard to commission, and the commission shown | No |
| Employee: opt-in and fact file | the person's profile link, plus five answers: age band, dependants, city, cover already held, monthly budget | a fact file in which every belief is labelled **Told**, **Checked** or **Guessed**; the person can see and correct every belief | No |
| Employee: people-like-you comparison | the fact file | the person's situation compared with employers like theirs, from job posts | No |
| Employee: cover gap | the fact file | the gap between cover held and cover needed, from a fixed rules table | No |
| Employee: application | the chosen insurer and cover | a filled-in application; **buying waits for the person's approval** | **Yes** (buying) |
| Cover-gap alarm (trigger) | a job change for an opted-in person | the date the old group health cover ends, and a prepared request to convert it to a personal policy before the window closes | **Yes**, if the request is sent; it is only prepared, and waits for the person |

**Variants (kept inside this idea, not separate entries):**
- **Driver scheme matcher:** match drivers to government cover they qualify for.
- **Claims helper:** check a rejected claim against the policy wording, and draft the complaint for the person to file.
- **Shipment cover at booking:** per-parcel cover offered to the client's customers.

## 5. Crustdata calls per request
| Request | Endpoint and fields | Credits | Verified? (fixture link or UNVERIFIED) |
|---|---|---|---|
| Benefits benchmark; people-like-you comparison | job search: logistics posts in India since 1 Sep 2026, filtered for benefits mentioned (e.g. "health insurance") | UNKNOWN: job search is not in the RULES §2 price table | UNVERIFIED. The owner reports a live check on 22 Nov 2026 (3,362 posts, 113 mentioning "health insurance"), but no recorded response is committed under `fixtures/`. Our own 14:00 call to `job/search` returned HTTP 400 because of a wrong request body ([data check](_council/round2-brief-and-data-check.md)). |
| Fact file (Checked beliefs) | person enrich: employer, role, city, job changes | 1 per person | UNVERIFIED (no recorded person-enrich response) |
| Similar employers | company search, company enrich: staff history (headcount series) | 0.03 per search result; 2 per enriched company | Enrich: headcount series recorded in the 14:00 check ([data check](_council/round2-brief-and-data-check.md)); search for "similar employers" UNVERIFIED |
| Cover-gap alarm | watcher on job changes for opted-in people; create, `/test` and run reads free, each alert 5 | 5 per alert | UNVERIFIED: the person-watch path has not been checked (the same gap noted on [#14](14-notice-period-alert.md)) |
| Insurer shortlist | not Crustdata: regulator reports and insurers' public filings, reached through web search and web fetch | web search 1; web fetch price not measured | UNVERIFIED |

- **Data sources outside Crustdata:** regulator reports and insurers' public filings for insurer figures; the person, for age band, family and existing cover.
- **Live API calls and credits (RULES §3):** this document made no live calls. Credits spent by this entry: 0. The owner's 22 Nov live check (above) was not recorded through the project client, so its credits are UNKNOWN and it is not a source until its response is committed.
- **Cost per job, from the RULES §2 table:** one employee fact file is at least 1 credit (≈ ₹26) for person enrich, plus 5 credits (≈ ₹130) for each job-change alert. Job-search and web-fetch costs are not in the table, so the full cost per job is UNKNOWN.

## 6. Decision rules
- **Belief labels:** every belief in the fact file is **Told** (the person said it), **Checked** (a record states it) or **Guessed** (worked out).
  - Guessed beliefs only choose which question to ask; they never decide an output.
  - Age, health and family are never guessed.
  - The person can see and correct every belief.
- **Cover gap:** a fixed rules table maps cover held against cover needed. The table itself is UNKNOWN: its rows have not been written yet.
- **Job change:** a new employer on the person's record counts as a job change. A promotion inside the same company does not.
- **Insurer ranking:** regulator figures only (claims settled, complaints), each with source and date; commission plays no part in the order and is shown beside each insurer.
- **Benefits counts:** always shown with the count, the filter and the as-of date, and the note that job posts understate what employers offer.
- **Cannot verify:** a person with no public record gets "cannot verify" for every employer fact, and the service asks the person instead of guessing.
- **Not claimed, because it cannot be sourced:** which policies similar people bought, and which insurers are "popular".

## 7. Hidden-test cases (at least 4, including duplicate, lookalike and cannot verify)
Draft cases: facts, not advice.

| Request | Correct answer | Based on (fixture or assumption) |
|---|---|---|
| An opted-in person whose record shows a new employer starting after 1 Sep 2026 | The job-change date, with its source, and the old cover flagged as ending | assumption; no fixture yet |
| Hard case: the same person promoted inside the same company | Not a job change; no alarm | assumption |
| Share of rival logistics job posts since 1 Sep 2026 that mention health insurance | 113 of 3,362 (≈ 3.4%), with the filter and the as-of date (22 Nov 2026), and the note that job posts understate what employers offer | owner's live check, 22 Nov 2026; UNVERIFIED until the response is committed |
| A person with no public record | "Cannot verify" for employer facts; the person is asked instead | assumption |
| Duplicate record | UNKNOWN: no duplicate case supplied yet | — |
| Lookalike name | UNKNOWN: no lookalike case supplied yet | — |

## 8. Approvals and kill-restart
- **Irreversible actions:** buying a policy waits for the person's approval; the cover-conversion request is prepared, not sent, until the person acts.
- **Idempotency keys:** UNKNOWN; not designed yet.
- **Kill mid-step:** UNKNOWN; not designed yet. The existing Crustdata client's cache, ledger and resume (see [AsOf](01-asof.md) §6) would be the starting point.

## 9. Ethics
- **Personal data used, and why:**
  - from the person, after opt-in: profile link, age band, dependants, city, cover already held, monthly budget;
  - from Crustdata person records: employer, role, city, job changes;
  - the job is personal cover advice, so this data is needed; age, health and family come only from the person, never from a guess.
- **Consent:** only people who opt in; the purpose is stated; the data is deleted afterwards.
- **Who could be harmed by a wrong answer:** UNKNOWN; not assessed yet beyond the risks below.
- **Right of reply:** the person sees every belief, with its Told / Checked / Guessed label, and can correct it.
- **How each decision is explained:** each belief carries its label, each insurer figure its source and date, each benefits count its filter and as-of date.
- **Licence:** comparing insurance for the public is regulated in India. The service is a tool used by a licensed broker or agent.
- **Commission bias:** rank without regard to commission, and show the commission.

## 10. Finance
- **Buyer:** UNKNOWN. The service is used by a licensed broker or agent; whether the broker, the employer or the employee pays has not been decided.
- **Price in ₹:** UNKNOWN; not set.
- **Cost per job:** at least 1 credit (≈ ₹26) per fact file, plus 5 credits (≈ ₹130) per job-change alert; job-search and web-fetch costs UNKNOWN (§5).
- **Margin:** UNKNOWN, since neither price nor full cost is known.
- **Sources needed:** a sourced broker commission figure for today's price; the job-search and web-fetch credit costs.

## 11. Design questions
- **Likely 5-minute live fix:** UNKNOWN; not stated yet.
- **100x volume:** UNKNOWN; not stated yet.
- **A second client:** UNKNOWN; not stated yet.

## 12. 3-minute demo script
UNKNOWN: no demo script written yet.

## 13. Build plan and cut-lines
UNKNOWN: no build plan written yet.

## 14. Open risks and unknowns
- **Consent:** handled by opt-in, a stated purpose and deletion afterwards (§9).
- **Licence:** comparing insurance for the public is regulated in India; the service is a tool for a licensed broker or agent.
- **Commission bias:** ranked without regard to commission, which is shown.
- **Job posts understate what employers offer:** said beside every count.
- **Data unverified:** the job-search count, person enrich and the person-watch path all lack a recorded response (§5).
- **Overlap with a dropped idea:** #14 was dropped for watching named people's job changes; the council may read the cover-gap alarm the same way despite the opt-in.

## Discussion
<!-- Others append below: "- <name>, <date>: <proposal>". The owner merges. -->
