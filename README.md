# set-prediction-reaction

Lean evidence experiment.

## Thesis

Collect timestamped market/news events and later market observations as immutable evidence. Prediction accuracy is a later interpretation, not the foundation.

## Rules

- Git is the audit trail.
- GitHub Actions is the worker.
- Evidence is append-only; never overwrite historical observations.
- Preserve source, published_at, captured_at, and event identity.
- Derived validation must reference the underlying event/reaction evidence.
- No database, dashboard, ML, API, or LINE in the first experiment.

## Minimal flow

source event -> immutable event commit -> wait -> market observation -> reaction commit -> optional validation.

## Proposed layout

- `events/` — source events
- `reactions/` — observed market state/reaction
- `validations/` — derived measurements
- `.github/workflows/` — workers
- `scripts/` — small deterministic collectors/processors

This repository is an experiment workspace only; `.tmp` is intentionally used for scratch/repo prototyping.
