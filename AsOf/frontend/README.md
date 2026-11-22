# AsOf Web UI

A high-fidelity single-page web application for **AsOf**, built with **Vite**, **React**, **TypeScript**, and **Tailwind CSS**.

AsOf takes counterparty requests in plain terms and returns finished, provable case files. It decides what raw data records can swear to, and as of when, enforcing strict non-extrapolation, staleness bounds, and evidence lineage.

---

## Features

1. **Request Bar**:
   - Supports 4 tool types: `clear` (clearance file), `dispute` (dispute file), `attest` (single field attestation), and `resolve` (entity resolution).
   - Domain and As-Of date (`D`) selectors with live interactive query support.

2. **Case File & Attestation Findings**:
   - Status chips: `attested` (emerald), `cannot_attest` (rose), `subsequent_event` (purple).
   - Value formatting, point date, retrieved-at timestamp, and templated statements.
   - Refusal reasons with `refusal_code` (e.g. `NOT_YET_RECORDED`, `STALE_DATA`, `CANNOT_RESOLVE`) and exact `missing` explanations.
   - Interactive evidence chips (`[E1]`, `[E2]`, etc.) opening modal views with endpoint, field path, and verbatim excerpts.

3. **Cost & Ledger Panel**:
   - Crustdata credits consumed.
   - INR total fee clearly labelled with `(estimate)`.
   - API calls count and cache hits count.

4. **Approval & Outbox Transition**:
   - One-click "Approve & issue" button.
   - Idempotently transitions from `draft` → `held for approval` → `issued (sandbox)` and disables further clicks.

5. **"Move the date" Slider**:
   - Interactive slider switching between real fixture outcomes:
     - `2022-06-01`: Delhivery dispute (C02: `NOT_YET_RECORDED` - series starts 2022-11-28).
     - `2026-10-15`: TCI Express dispute (C07: `STALE_DATA` - 38-day staleness gap > 14 days).
     - `2026-11-22`: Delhivery clearance (All 5 fields attested: existence, listing, headcount, revenue_band, domains).
     - `Resolve Refusal`: Shree Balaji Logistics (C08: 25 candidates, `CANNOT_RESOLVE` without domain).

6. **Backend / API Switch**:
   - Uses local JSON fixtures (`fixtures/demo_casefile.json`, `fixtures/demo_refusals.json`) by default.
   - Supports live backend connection via `VITE_API_URL` environment variable.

---

## Getting Started

### Prerequisites
- Node.js (v18+)
- npm

### Installation
```bash
cd frontend
npm install
```

### Production Build
To check TypeScript types and build the optimized distribution:
```bash
npm run build
```

The output will be placed in `frontend/dist/`.

### Previewing the Build
```bash
npm run preview
```

### Connecting to a Live Backend
Set the `VITE_API_URL` variable in `.env.local` or when running Vite:
```bash
VITE_API_URL=http://localhost:8000 npm run dev
```
