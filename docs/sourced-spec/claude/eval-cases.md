# Eval cases — Sourced

Two independent sets. Neither is cuttable (see `SPEC.md` §Cut-lines). The JSON they
compile to is `eval/cases.json`, with top-level keys `"shortlist"` (Set A) and
`"verification"` (Set B).

## Set A — shortlist quality (`shortlist`)
Real, documented hires, gathered day-of the same way the Raise export gathered its
funding-round cases: find ~12 candidates from public hiring announcements (LinkedIn "I'm
excited to announce," a company blog post, a press mention) in roughly the last 90
days, keep the ones whose actual hire has a resolvable Crustdata `person/enrich`
profile, and end up with however many survive (aim for 8–10).

Shape:
```json
{
  "role_brief": "the job posting's own text or a one-line reconstruction of it",
  "company_domain": "example.com",
  "posting_date": "2026-08-01",
  "actual_hire_profile_url": "https://linkedin.com/in/..."
}
```
Run the pipeline with `cutoff_date = posting_date` (drop any Crustdata/web data dated on
or after it, same leakage guard Raise used for funding rounds) and check whether
`actual_hire_profile_url` appears in the top-5/top-10 shortlist. Baseline: a plain
keyword title+skill match, no verification or ranking logic, same k.

**This file ships with zero real cases** — filling it with real people's hiring
history is something to do with sourced, dated, public evidence on the day, not
something to fabricate in advance. The placeholder in `eval/cases.json` shows the shape
only.

## Set B — verification accuracy (`verification`) — the centerpiece
Synthetic profiles with exactly one planted condition each, built to mirror the
organizers' own hard-case pattern (problem statement: "a duplicate record, a lookalike
name, or a question that the sources cannot settle, where the correct answer is cannot
verify"). Names below are placeholders, clearly fictional — write your own set tonight,
these are templates for the shape, not content to ship as-is.

| case_id | planted_condition | what a correct run does |
|---|---|---|
| `verif-01` | Duplicate/lookalike name: two distinct profile URLs share "Aarav Shah," one a backend engineer, one a product manager, no other disambiguating signal given in the brief | Surfaces an **unresolved** `DisambiguationGroup` with both profiles listed; does not guess which one the brief means |
| `verif-02` | Contradicted employer dates: claimed CV says "Senior Engineer at Company X, 2021–2023," enrich record shows Company X employment ending in 2020 | Verdict `contradicted`, cites the enrich record's own date range |
| `verif-03` | Unconfirmable claim: CV claims "led the data pipeline rewrite that cut latency 40%," no source (Crustdata or web) states this specific fact | Verdict `unconfirmed` ("can't verify"), does not treat silence as confirmation or as a lie |
| `verif-04` | Implausible seniority: CV claims "managed a 50-person engineering org" at a company whose `company/enrich` headcount was ~12 in the claimed year | Verdict `contradicted`, cites the `CompanySnapshot` headcount-at-date, not just "seems unlikely" |
| `verif-05` | Clean true positive: every claim on the CV matches the enrich record exactly, employer is real and resolves, dates and titles line up | Verdict `confirmed` on every claim; **must not** be flagged, penalized, or held back — a false "unconfirmed" here is as bad as missing a real contradiction |
| `verif-06` | Real company, no claimed metric findable, but plausible and not contradicted (e.g. "contributed to the checkout redesign," no dates, no numbers) | Verdict `unconfirmed`, not `contradicted` — a vague but non-contradicted claim is different from a checkable false one |
| `verif-07` | Employer name typo'd/renamed since (e.g. company rebranded) | `company/identify` should still resolve it (or the matcher should try a fuzzy pass before giving up) → `confirmed` if the underlying record matches, not a false `unconfirmed` from a literal string mismatch |

Scoring: `accuracy = (# cases where verdict_given == expected verdict) / (# cases)`.
Report per-case results in the UI table, not just the aggregate — a single wrong verdict
on `verif-05` (a false positive against an honest candidate) is worth calling out by
itself, since it's the error type that does the most reputational harm.

## Where these feed the demo
Eval Set B's `verif-01`/`verif-02`/`verif-03` are good candidates to also drive the live
demo's brief, since they let the 3-minute demo show disambiguation, a contradiction, and
a "can't verify" in a single run without relying on whatever a judge-supplied brief
happens to contain.
