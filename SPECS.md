# SPECS — set-prediction-reaction

## Mission

Build the smallest working **evidence machine** for timestamped market/news events.

The goal is **not** to prove prediction accuracy.

The goal is durable, auditable data:

> source event → immutable evidence → later market observation → immutable reaction evidence

**Git is the audit trail. GitHub Actions is CI/worker infrastructure, but no scheduled worker is required in this phase.**

---

## Definition of Done

The agent is finished only when ALL are true:

1. \x60.tmp/set-prediction-reaction/\x60 is its own Git repository.
2. The implementation is a minimal, runnable Python pipeline.
3. The pipeline creates a deterministic synthetic sample event without network access.
4. The pipeline writes an immutable event record.
5. The pipeline writes a later reaction record linked by \x60event_id\x60.
6. Re-running with the same input does not rewrite existing evidence.
7. A conflicting write for an existing identity fails loudly.
8. Tests cover identity, append-only behavior, linkage, timestamps, and end-to-end execution.
9. GitHub Actions runs the tests and the offline sample pipeline in CI.
10. README documents the exact local commands.
11. The agent runs tests and the sample pipeline successfully.
12. A second pipeline run produces no evidence changes.
13. The agent commits the completed implementation in the nested repository.
14. The parent \x60/workspace\x60 repository is not modified or committed by this task.
15. **Do not push to GitHub** unless explicitly instructed.

---

## Scope

### Build now

- Python implementation; standard library preferred.
- Synthetic \x60sample\x60 source only.
- Normalized event model.
- Immutable JSON evidence.
- Deterministic IDs.
- Append-only/idempotent writer.
- Reaction records linked to events.
- Basic schema/time validation.
- Pytest tests.
- One GitHub Actions CI workflow.
- Local Git history.

### Do NOT build now

- Real broker/news ingestion.
- Database.
- API/web server.
- Dashboard/UI.
- ML/model training.
- Prediction scoring or trading recommendations.
- Broker ranking.
- LINE integration.
- Authentication.
- Docker/cloud infrastructure.
- Scheduled production worker.
- High-frequency tick storage.
- Scraping that bypasses access controls.
- Commercial redistribution of third-party data.

If a real external source is unavailable, finish the offline synthetic pipeline. Do not add credentials or external dependencies just to make the prototype run.

---

## Repository Isolation

This is a **nested repository** inside \x60.tmp\x60.

The agent MUST:

\x60\x60\x60bash
cd .tmp/set-prediction-reaction
git init
git rev-parse --show-toplevel
\x60\x60\x60

The repository root returned by \x60git rev-parse --show-toplevel\x60 MUST be:

\x60\x60\x60text
.../.tmp/set-prediction-reaction
\x60\x60\x60

Do not modify, stage, commit, reset, or rewrite history in the parent \x60/workspace\x60 repository.

Do not force-push or rewrite Git history.

---

## Repository Contract

Expected structure:

\x60\x60\x60
set-prediction-reaction/
├── events/
├── reactions/
├── scripts/
├── tests/
├── .github/
│   └── workflows/
│       └── ci.yml
├── README.md
├── SPECS.md
├── .gitignore
└── pyproject.toml
\x60\x60\x60

Evidence directories may use \x60.gitkeep\x60 if empty.

Do not create \x60validations/\x60 in this phase.

---

## Evidence Model

### Event

An event is information observed from a source.

Minimum fields:

\x60\x60\x60json
{
  "event_id": "evt_<deterministic-id>",
  "source": "sample",
  "source_type": "news",
  "ticker": "PTT",
  "title": "Sample event",
  "url": null,
  "published_at": "2026-10-02T09:00:00+07:00",
  "captured_at": "2026-10-02T09:00:05+07:00",
  "content_hash": "<sha256>",
  "schema_version": 1,
  "data_status": "synthetic"
}
\x60\x60\x60

Rules:

- \x60published_at\x60 = source publication time.
- \x60captured_at\x60 = when the system observed the event.
- Never substitute one for the other.
- Timestamps must be ISO-8601 with an explicit timezone offset.
- \x60event_id\x60 is deterministic.
- \x60content_hash\x60 may be used by the synthetic implementation, but real-source correction/version semantics are **out of scope** for this phase.
- The same synthetic input must produce the same \x60event_id\x60.
- Historical evidence must never be silently replaced.

### Reaction

A reaction records market state observed after the event.

Minimum:

\x60\x60\x60json
{
  "event_id": "evt_<deterministic-id>",
  "reaction_id": "rxn_<deterministic-id>",
  "ticker": "PTT",
  "observed_at": "2026-10-02T09:15:00+07:00",
  "price": 25.10,
  "volume": null,
  "benchmark": {
    "symbol": "SET",
    "value": null
  },
  "window": "15m",
  "schema_version": 1,
  "data_status": "synthetic"
}
\x60\x60\x60

For this offline experiment, market values are synthetic or null. **Never present synthetic values as real market observations.**

\x60data_status\x60 MUST distinguish at least:

- \x60synthetic\x60
- \x60observed\x60

Real market data is future work.

---

## Storage Convention

\x60\x60\x60
events/YYYY-MM-DD/<event_id>.json
reactions/YYYY-MM-DD/<reaction_id>.json
\x60\x60\x60

Evidence is historical.

Never use mutable aggregate files such as:

- \x60latest.json\x60
- \x60current.json\x60
- \x60data.json\x60

---

## Append-Only Contract

The evidence writer MUST:

1. Calculate the deterministic target path.
2. If the exact evidence file does not exist, create it.
3. If it exists with identical canonical content, treat the operation as idempotent and do not rewrite it.
4. If it exists but content differs, fail loudly.
5. Never silently repair, replace, or mutate historical evidence.
6. Prefer atomic creation so concurrent/repeated execution cannot partially write evidence.

The important invariant is:

> **same input + second run = no historical evidence changes**

---

## Identity

### Event identity

Use a deterministic SHA-256 hash over canonical stable fields.

For this MVP, use:

\x60\x60\x60
source
published_at
ticker
title
content_hash
\x60\x60\x60

Suggested format:

\x60\x60\x60
event_id = "evt_" + first 16 hex characters of SHA-256
\x60\x60\x60

Canonicalization and hashing MUST be deterministic and tested.

### Reaction identity

Use:

\x60\x60\x60
event_id
window
observed_at
ticker
\x60\x60\x60

Suggested format:

\x60\x60\x60
reaction_id = "rxn_" + first 16 hex characters of SHA-256
\x60\x60\x60

Different observations MUST NOT collapse into one identity.

Do not implement statistical reaction scoring in this phase.

---

## Pipeline

Provide one minimal command demonstrating the complete offline flow:

\x60\x60\x60
sample source
    ↓
normalize event
    ↓
calculate event_id
    ↓
append event evidence
    ↓
create synthetic reaction
    ↓
append reaction evidence
\x60\x60\x60

Example:

\x60\x60\x60bash
python -m scripts.pipeline --sample
\x60\x60\x60

The command must be safe to run repeatedly.

The implementation must clearly identify sample data as synthetic.

---

## Tests

Minimum test coverage:

1. Deterministic event identity.
2. Different inputs produce different identities.
3. First evidence write.
4. Identical replay is idempotent and does not rewrite the file.
5. Conflicting content for an existing identity fails.
6. Reaction references an existing \x60event_id\x60.
7. Invalid/naive timestamps are rejected.
8. End-to-end sample pipeline works.
9. A second end-to-end run produces no evidence diff.

Do not add tests for features that are explicitly out of scope.

---

## GitHub Actions

Create \x60.github/workflows/ci.yml\x60.

It MUST:

1. Run on \x60push\x60.
2. Run on \x60pull_request\x60.
3. Use a supported Python version.
4. Install the minimal test dependency.
5. Run the test suite.
6. Run the offline sample pipeline in a temporary/isolated location so CI does not depend on committed historical evidence.

**Do not add a cron/scheduled production worker yet.**

CI proves reproducibility; production ingestion is a later phase.

---

## README

README must explain:

- purpose of the experiment
- evidence model
- repository isolation
- local setup
- how to run tests
- how to run the sample pipeline
- how append-only/idempotent behavior works
- that sample data is synthetic
- what is explicitly not implemented yet

Do not claim prediction accuracy, real market coverage, or real broker/news ingestion.

---

## Security / Data Handling

- Never commit API keys, cookies, session tokens, or credentials.
- Future credentials must come from environment/secrets.
- Treat external URLs/content as untrusted input.
- Never execute source content.
- Do not add third-party credentials to complete this offline prototype.
- Synthetic data must be clearly marked.
- Do not claim synthetic market observations are real.

---

## Agent Operating Rules

Work autonomously from this specification.

Do not ask for confirmation for choices already constrained here.

If something is unspecified, choose the smallest conventional implementation and document it.

Do not expand scope.

At the end, the agent MUST:

1. Run tests.
2. Run the sample pipeline.
3. Run the sample pipeline a second time.
4. Verify no historical evidence was rewritten.
5. Inspect generated evidence.
6. Run \x60git status\x60 and \x60git diff\x60.
7. Commit the completed implementation in the nested repository.
8. Report:
   - files changed
   - test result
   - sample evidence created
   - second-run/idempotency result
   - commit hash
   - remaining limitations

The final report MUST distinguish implemented evidence infrastructure from future real-data integration.

---

## Success Criterion

A fresh agent can read this file and independently produce:

\x60\x60\x60
synthetic event
    ↓
deterministic identity
    ↓
write once
    ↓
later synthetic observation
    ↓
reaction references event
    ↓
second run changes nothing
    ↓
tests pass
    ↓
Git commit preserves the evidence trail
\x60\x60\x60

That is the complete product of this phase.

**Nothing more is required.**
