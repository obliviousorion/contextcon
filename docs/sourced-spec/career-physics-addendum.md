# Career physics: addendum to Sourced

Extends the claim-checking part of Sourced (`SPEC.md` steps 7 and 8) and the "Career Check only" fallback.
It does not touch sourcing, ranking, outreach or booking.

Data facts below were checked against live Crustdata responses on 22 Nov 2026.

## 1. What this adds

- Checks that need no data (dates that break logic).
- A founding-year check.
- A split between "an independent record says so" and "only the candidate's own profile says so".
- A split between "cannot be true" and "unlikely, ask a person".
- Guard rules for five data traps we saw in real records.

## 2. Verdicts

Sourced has three output values. Keep them, so the output format does not change, and add two detail fields.

| Detail verdict (`verdict_detail`) | Meaning | Output value | `evidence_grade` |
|---|---|---|---|
| verified | An independent record states it (company page, filing, press) | `confirmed` | `independent` |
| consistent | Only the candidate's own profile states it | `confirmed` | `self_reported` |
| contradicted | A record says otherwise | `contradicted` | as found |
| impossible | Breaks logic or time | `contradicted` | `logic` |
| implausible | Unlikely; a person should look | `unconfirmed` + `refer: true` | as found |
| cannot_verify | Nothing settles it | `unconfirmed` | none |

**Open decision for the team:** `implausible` maps to `unconfirmed`, not `contradicted`. Reason: the rules say a wrong answer costs more than "cannot verify". If the builder handbook's Career Check example expects `contradicted` for a team-size mismatch, change this one row.

## 3. Checks, in order

Stop at the first check that gives `impossible` or `contradicted`.

| # | Check | Needs | If it fails |
|---|---|---|---|
| L1 | Job ends before it starts | CV only | impossible |
| L2 | Start or end date is in the future | CV only | impossible |
| L3 | Two full-time jobs overlap by more than 3 months | CV only | implausible (remote work and side roles exist) |
| C1 | Job starts 2 or more years before the employer's `basic_info.year_founded` | company record | impossible |
| C1b | Job starts 1 year before the founding year | company record | implausible (renames and re-registrations happen) |
| P1 | Employer and dates match the person record, within 3 months | person record | pass: consistent; fail: contradicted |
| P2 | Title on the CV differs in level from the person record | person record | contradicted |
| W1 | An independent page states the same fact | web search and fetch | pass upgrades consistent to verified |
| S1 | Claimed team is larger than the department on that date | `headcount.timeseries`, `headcount.by_role_absolute` | implausible, never contradicted |
| S2 | Claimed money figure exceeds the whole company's revenue | company `revenue` | implausible |

## 4. Change requested to SPEC steps 7 and 8

- **Step 8:** "led 50 people at a company with 10 employees" is currently `contradicted`. Change to `implausible`. Staff counts look profile-based (inferred from the department breakdown), so they miss drivers and warehouse staff and act as a lower bound.
- **Step 7:** a match against the candidate's own profile stays `confirmed`, but must carry `evidence_grade: self_reported`.

## 5. Data facts (checked live)

**Person record, each job entry:** `title`, `start_date`, `end_date`, `crustdata_company_id`, `is_default`, `employment_type`, `seniority_level`, `location.raw`, `company_headcount_latest`.

**Company record:** `basic_info.year_founded`, `basic_info.all_domains`, `headcount.timeseries` (dated points; the sample company had 204, starting 28 Nov 2022), `headcount.by_role_absolute`, `locations.all_office_addresses`.

**Limits on our plan:** records are a stored copy, not live (live refresh is not on the plan). First and last name fields come back empty.

**Cost in credits:** person record 1; company record 2; people search 0.03 per result plus 0.1 for job history; watch alert 5; creating a watch and reading its runs are free.

**Cost per CV:** about 1 for the person plus 2 per employer. Four employers is about 9 credits.

## 6. Trap rules

| Trap seen in real data | Rule |
|---|---|
| "Recently changed jobs" flag was a promotion inside one company | Compare `crustdata_company_id`, not the flag |
| Move between two firms of one group | Different company ID but shared name: treat as two employers, never merge |
| Several current jobs (board seats, advisory) | Use the entry with `is_default: true` as the main job |
| Dates stored as the first of the month | Allow 1 month either side before calling a mismatch |
| No staff counts before late Nov 2022 | Team-size claims before that date: cannot_verify |
| Record last refreshed before the date in question | cannot_verify, and name the refresh date |
| Person asked for their data to be removed (`match_status: redacted`) | Do not process and do not contact |

## 7. Add-ons, in build order

Each one is optional and independent.

1. **"What would make this true" note.** For each failed line, state the nearest value that would pass, to tell a typo from a lie.
2. **Right of reply.** An `implausible` or `contradicted` line never triggers a rejection draft by itself. It triggers a "please clarify" draft, held for approval.
3. **Bias guard.** Verdicts never read name, gender, age or college. A career gap is reported with no verdict.
4. **Witness count.** Count other people recorded at that employer in those years. Zero is a flag. Count only; contact nobody.
5. **Title translator.** Convert titles to a level adjusted for company size on that date.
6. **Fast lane.** A CV with every line verified or consistent is marked for a quicker first call.

## 8. Cases to add to eval Set B

One planted problem each.

1. Job ends before it starts: impossible.
2. Job starts 3 years before the employer was founded: impossible.
3. CV title "Head of", record says "Manager": contradicted.
4. Start date off by 2 months: consistent, with a note.
5. "Led 200" at a firm showing 40 staff in 2024: implausible, refer.
6. "Led 200" in 2020: cannot_verify (no staff counts that early).
7. Two company records share the employer's name and nothing breaks the tie: cannot_verify.
8. Person record marked removed: not processed.
