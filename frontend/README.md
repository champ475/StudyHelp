# StudyHelp frontend

React + TypeScript (Vite). Structured step-input widgets (tap-to-select, no typing — ARCHITECTURE.md D13) plus a streaming chat UI consuming the backend's SSE pipeline (`POST /sessions/{id}/steps`).

**Dev mode only.** Session creation is a local identity picker, not a real account/consent flow (ARCHITECTURE.md D18) — never point this at real students.

## Run locally

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api/* to the backend on :8000
```

Requires the backend running (`docker compose up` from the repo root — Postgres + Redis + API, migrated and seeded) for anything beyond the identity picker to work; the dev server itself starts independently.

## Scripts

- `npm run dev` — Vite dev server
- `npm run build` — typecheck (`tsc --noEmit`) then production build
- `npm run lint` — ESLint
- `npm run test` — Vitest (component tests, no backend required — network calls are mocked)
