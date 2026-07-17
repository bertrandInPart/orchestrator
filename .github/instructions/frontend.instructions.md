---
applyTo: "client/**"
---

# Frontend conventions (Angular)

These apply to `frontend-builder` (implementation) and inform `architect` (design).

## Structure

- Feature modules under `client/src/app/features/<feature-slug>/`, each with its own components,
  services, and routing module. Shared/reusable UI lives under `client/src/app/shared/`.
- Components stay presentational where possible; data-fetching and state live in Angular services
  (or a state-management layer, if one gets introduced — that's an architecture decision, not a
  frontend-builder one; flag it if you think one is needed).

## Non-happy-path states are not optional

Every screen a feature touches must implement, at minimum, the **empty**, **loading**, **error**,
and **success** states carried over from `spec.md`'s UX Walkthrough into `architecture.md`.
Shipping only the happy path is an incomplete implementation of the spec, not a minor omission —
treat a missing error or empty state the same as a missing acceptance criterion.

## API contract

- Treat the request/response shapes in `architecture.md` as frozen. If what you need doesn't
  actually match what's there, don't silently work around it client-side (e.g. by post-processing
  a mismatched response shape) — flag the mismatch in your completion comment. That's a signal the
  Architect stage needs a second look.

## Accessibility & responsiveness

- Keyboard reachability and sensible focus handling after an action completes are required, not
  aspirational, for any new interactive element.
- If the app is responsive, check narrow viewports for any new screen — note in
  `frontend-notes.md` if a modal-vs-full-screen decision was made and why.

## What you must not do

- Touch anything under `server/**` or any schema/migration file.
- Skip a non-happy-path state because it's "less code than the happy path."
