# Orchestrator Workflow Dashboard

A small local web dashboard that visualizes where every feature currently sits in the
agentic feature chain (spec-writer → architect → backend-builder / frontend-builder →
test-engineer → reviewer → release-engineer):

- **Board view** — features grouped by `Stage`, mirroring the GitHub Projects v2 board (or
  Jira, whichever `.orchestrator/config.yml` selects), showing Feature Slug, Current Agent,
  and Feature Branch per card.
- **Feature detail view** — drill into a single feature's lifecycle history (every DoR/DoD
  check, callback, retry, escalation, parsed from its lifecycle file) plus a secondary
  timeline of ticket activity (parsed from the `<!-- meta: ... -->` comment convention in
  `.orchestrator/skills/ticket-comments.skill.md`).

This is tooling for the orchestrator itself — a separate stack (Node/Express + React/Vite)
from the product code in `server/`/`client/`, run locally, refreshed manually. It does not
poll, use webhooks, or deploy anywhere.

## Requirements

- Node.js 18+
- `.orchestrator/config.yml` must exist in the repo root (run
  `.orchestrator/scripts/init-wizard.py` once if it doesn't) with a `ticket_system.provider`
  of `github` or `jira`.
- Credentials as environment variables (never committed):
  - GitHub: `GITHUB_TOKEN` — a personal access token (or `gh auth token` output) with `repo`
    and `read:project` scope.
  - Jira: `JIRA_EMAIL` and `JIRA_API_TOKEN` for the account tied to `jira.base_url`.

## Running it

```powershell
cd .orchestrator\dashboard
npm install
$env:GITHUB_TOKEN = "<token>"   # or JIRA_EMAIL / JIRA_API_TOKEN
npm run dev
```

This starts the Express API (`http://localhost:4000` by default, override with
`DASHBOARD_PORT`) and the Vite dev server (`http://localhost:5173`) together. Open
`http://localhost:5173` in a browser. The client proxies `/api/*` requests to the backend.

For a production-style single-process run (backend serves the built frontend):

```powershell
npm start
```

This builds the client and serves it, plus the API, from `http://localhost:4000`
(or `$env:DASHBOARD_PORT`).

## API

- `GET /api/board` — normalized list of features across every stage:
  `{ slug, title, stage, currentAgent, branch, ticketUrl, ticketId }[]`
- `GET /api/features/:slug` — lifecycle history entries + ticket comment activity for one
  feature.

Both routes read the ticket provider chosen in `.orchestrator/config.yml` and are backed by
one of `server/adapters/github.js` or `server/adapters/jira.js` — the routes and frontend
never branch on provider themselves.

## Notes

- Nothing here is polled or pushed automatically — click **Refresh** in the UI to re-fetch.
- Lifecycle files are read directly off disk (`.orchestrator/docs/features/<slug>/*_lifecycle.md`)
  relative to the repo checkout the dashboard is run from; it does not support aggregating
  multiple repos/orchestrator instances.
