# Guided flow v2: UI <-> API contract

Session: an HttpOnly cookie `bd_session` set by `/api/login`. All `/api/*` calls below send it automatically (same origin).
Errors: `{error: string}` with a 4xx status. Show `error` as plain text.

## Screens and calls, in order
1. **Login** (first screen). Fields: LinkedIn link; secondary link "Use another profile or just my name and company" reveals Name + Company inputs; a 4-digit PIN; a tick box "This is my own profile and I agree to it being looked up."
   `POST /api/login {link?: string, name?: string, company?: string, pin: "1234", consent: boolean}`
   - 200 `{user_id, returning: boolean, stage: "confirm" | "questions" | "dashboard" | "refused"}`
   - 401 `{error: "Link or PIN not recognised."}` (also for a wrong PIN; reveals nothing)
   - 403 `{error: "This demo only works for people who have agreed to be looked up. Nothing was looked up."}`
   - 400 `{error}` for a bad PIN format or a missing consent tick on first visit.
   `GET /api/me` -> `{logged_in: boolean, user_id?, stage?, mode?: "live"|"replay"}` (call on load; if logged in, go to the stage).
   `POST /api/logout` -> `{ok: true}`. `POST /api/forget` -> `{deleted: {<table>: <rows>}, note}` (show the counts, then return to Login).
2. **Confirm card** (stage `confirm`). `GET /api/intake` -> `{items: IntakeItem[]}`. One card listing every item; each row: plain label, value, a small tag (Checked / Our guess / Not found), "Source" opens the pointer, and tap actions: **Correct** (confirm) or **Change** (shows `choices` as taps, or a text box if no choices). Items with kind `missing` show their `question` with `choices`.
   `POST /api/intake {items: {[key]: {action: "confirm"} | {action: "edit", value: any}}}` -> `{stage: "questions" | "refused", message?}`. Every item must be answered before the button enables.
3. **Two questions**, one at a time, tap choices (frontend only, plain words, no insurance jargon):
   - `dependants`: "Who depends on you?" multi-select: `just_me` "Just me", `partner` "Partner", `children` "Children", `parents` "Parents", `not_sure` "Not sure".
   - `insurance_now`: "Do you have any insurance now?" multi-select: `from_work` "Yes, from work", `bought_myself` "Yes, I bought it myself", `none` "No", `not_sure` "Not sure".
   `POST /api/answers {dependants: string[], insurance_now: string[]}` -> `{run_id}`. Then show the dashboard in its loading state.
4. **Dashboard** (stage `dashboard`). `GET /api/dashboard?as_of=YYYY-MM-DD` (omit as_of for now). Poll every 1.5 s while `run.status === "running"`.
   Buttons: **Check for changes** `POST /api/check` -> `{run_id}`; **Live / Replay** switch `POST /api/mode {mode}` -> `{mode}` (label: "Next run uses live Crustdata calls" / "Next run replays recorded responses"); **Log out**; **Forget me** (confirm dialog first); link "Console" -> `/console`.
   Next step: `POST /api/choose {company_id}` -> `{action}`; then **Approve** `POST /api/approve {key, approver: "person"}` and `POST /api/act {run_id: action.run_id}`; poll `GET /api/sandbox` for the receipt count of `action.key` (1 = exactly once).

## Types
```ts
type Source = { record: string; record_id?: string; field_path?: string; passage?: string; url?: string;
                record_date?: string | null; retrieved_at?: string };
type IntakeItem = { key: "employer" | "role" | "start_date" | "city" | "age_band"; label: string; value: any;
  kind: "checked" | "guessed" | "missing"; source?: Source | null; basis?: string; question?: string; choices?: string[] };
type Fact = { fact_id: string; statement: string; value: any; label: "told" | "checked" | "guessed";
  source: Source | null; cannot_verify?: boolean; missing?: string; last_checked?: string };
type TrailStep = { key: "you" | "employer" | "people" | "insurers" | "gaps"; title: string; searched: string; source: string;
  records: number | null; credits: number; status: "found" | "searched, cannot verify" | "skipped" | "computed" | "running";
  mode: "live" | "replay" | "no call"; recorded_at?: string | null; reused?: boolean; note?: string; pointers: Source[] };
type InsurerFact = { label: string; value: any; source: Source };
type Insurer = { company_id: number; name: string; facts: InsurerFact[];
  claims: { cannot_verify: true; missing: string } | { value: string; source: Source }[] };
type DiaryEntry = { date: string; subject: string; subject_kind: "you" | "group"; new: string; previous: string | null;
  trigger: string; source: Source | null; label: "told" | "checked" | "guessed"; gap_changed: boolean; next_step_changed: boolean };
type Dashboard = {
  user: { user_id: string; mode: "live" | "replay"; stage: string; last_checked: string | null };
  as_of: string;                  // the date the view is "as believed on"
  dates: string[];                // slider stops (ascending, ISO dates)
  run: { run_id: string | null; status: "running" | "finished" | "held" | "stopped" | "none" };
  profile: Fact[];                // as believed on as_of
  graph_case: { facts: Fact[]; peer_benchmark: any | null };   // same shape the existing graph's buildGraph() takes
  insurers: { note: string; selection: any; items: Insurer[]; status: string; missing?: string };
  gaps: { rule_id: string; cover: string; called_for: string; severity: string; explanation: string; facts_used: string[] }[];
  questions: { question: string; why: string }[];
  cannot_verify: { statement: string; missing: string }[];
  trail: TrailStep[];
  next_step: { choices: { company_id: number; name: string }[]; action: any | null; conversion: any | null };
  diary: DiaryEntry[];
  cost: { credits: number; inr: number };
};
```
