# AsOf web UI

A React + TypeScript (strict) + Tailwind app over the AsOf HTTP API (`backend/http_api.py`). Every screen
reads the real backend. There is no fixture mode.

## Run it (two terminals)

```bash
# 1. the API, from the repo root (replay mode, 0 credits; binds 127.0.0.1:8787)
uv run python -m backend.http_api
#    it prints "Approval token for this session: ..." which you paste when you approve

# 2. the UI
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

The app calls relative `/api/...`. Vite proxies `/api` to `http://127.0.0.1:8787`, so no CORS setup or env var
is needed. Set `VITE_API_URL` only to call a different API origin directly. If `/api/health` fails, every page
shows "Backend not running" with the start command.

`npm run build` type-checks (`tsc`) and builds to `dist/`. `npm run preview` serves the build with the same proxy.

## Routes

The URL holds the state, so every page can be shared and Back works.

| Route | Shows |
|---|---|
| `/` | One-line description, a search box (domain or company name) and "Try" chips. A domain opens `/clear/:domain`; a name opens `/resolve?q=`. |
| `/resolve?q=` | "Cannot resolve: N companies match", with each candidate's name, domains and confidence and a button to clear each domain. It never picks one for you. |
| `/clear/:domain` | The clearance file as of today (see "Case file" below). |
| `/dispute/:domain?as_of=YYYY-MM-DD` | The dispute file as of D, with a date input and "move the date" presets (TCI: 2020-01-01, 2026-09-01, 2026-10-15). Each move pushes a URL and refetches. |
| `/files` | Stored case files (from `/api/cost`) with status (Draft, Approved, Issued, Stale) and cost. |
| `/files/:id` | One stored artifact: a case file, an audit report or an evidence request, with its approval record (by, at) and STALE marks. |
| `/audit` | A structured claims form (field, value, as of, claim text; add and remove rows). It returns a verdict list (agrees, contradicts, cannot verify) with each line's statement and evidence ids, and the report can be issued through approval. |
| `/watch` | Request a watcher for a domain, approve it with the token, issue it, then fire the free test alert. Shows the stale line ids with links to the affected case files. A real alert costs 5 credits. |
| `/ledger` | Credits and ₹ spent this run against the measured cost of each stored file. |

## Case file screen

- **Header:** company, domain, kind, as-of date D, the file id with a copy button, and the cost line in the
  backend's `cost_note` wording.
- **Date gutter:** each line has a fixed left column with its point date (tabular mono) and a thin status rule.
  The statement sits on the right, verbatim. D is a marker at the top of the gutter. Subsequent events sit under
  "Dated after D — reported, never attested".
- **Status** is always text plus color: Attested, Cannot attest, Subsequent event, Stale. Label badges
  ("profile-derived count", "estimate", "true at retrieval only", "as recorded") are always shown.
- **Refusals** give the refusal code in plain words, plus "What would settle it" (the `missing` text).
- **Evidence chips** (E1, E2, …) open a right-side drawer with the endpoint, field path, verbatim excerpt, point
  date, retrieved at and cache key. Esc closes it, focus is trapped while it is open, and focus returns afterwards.
- **Evidence request** card, labelled "Not a negative finding", with its own Issue flow.
- **Approval stepper:** Draft → Held for approval → Approved (by, time) → Issued (sandbox). Issue calls
  `/api/issue`. If the item is held, a modal asks for the token from the API server's terminal, then runs approve
  and issue. Buttons are disabled while a request is pending, so a double click does nothing extra.

## Layout of the code

- `src/lib/api.ts`: the one fetch helper (typed responses; the server's `{error}` message on 4xx).
- `src/lib/useAsync.ts`: loading, error and retry for each page. `src/lib/useIssueFlow.ts`: the shared approval
  flow. `src/lib/format.ts`: en-IN dates and ₹.
- `src/types.ts`: mirrors `backend/models.py` and the HTTP envelopes.
- `src/pages/*`: one lazily loaded page per route. `src/components/*`: small, focused components.

## Design

The look is an "evidentiary registry": a light, cool theme. The colors are CSS variables in `src/index.css`,
mapped into `tailwind.config.js`. The fonts are self-hosted with @fontsource: Source Serif 4 for headings, IBM
Plex Sans for body text and IBM Plex Mono for values, dates and ids. Every text and tint pair passes WCAG AA.

## Live mode
Start the API with `uv run python -m backend.http_api --live --cap 10`. The header badge then reads
"live · confirm before spend · N credits left". A request that is not in the stored copies shows a
"Live lookup needed" panel with the credit and ₹ estimate; only its button spends.
