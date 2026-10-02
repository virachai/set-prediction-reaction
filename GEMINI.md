# GEMINI.md — set-prediction-reaction

Instructional context and engineering guidance for working with the **set-prediction-reaction** repository.

---

## 1. Project Overview & Core Thesis

`set-prediction-reaction` is a lean **evidence machine** designed to record timestamped market and news events alongside subsequent market observations as immutable historical evidence.

### Core Invariants & Philosophy
- **Prediction accuracy is an interpretation, not the foundation:** Focus strictly on durable, auditable evidence capture.
- **Git is the audit trail:** Every piece of evidence is tracked directly in source control or artifact storage.
- **Evidence is append-only:** Historical observations must never be overwritten, modified, or silently replaced.
- **Storage is filesystem JSON:** No databases, dashboards, ML models, APIs, or messaging integrations in this phase.
- **Evidence flow:**
  $$\text{source event} \longrightarrow \text{immutable event commit} \longrightarrow \text{wait / window} \longrightarrow \text{market observation} \longrightarrow \text{reaction commit}$$

---

## 2. Directory Structure

```text
set-prediction-reaction/
├── events/                 # Immutable source event records: events/YYYY-MM-DD/<event_id>.json
├── reactions/              # Immutable market reaction records: reactions/YYYY-MM-DD/<reaction_id>.json
├── scripts/                # Deterministic pipeline runners and core logic (e.g., pipeline.py)
├── tests/                  # Unit and integration tests (pytest)
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions CI workflow (offline test & pipeline verification)
├── README.md               # User-facing project documentation
├── SPECS.md                # Normative project specifications & definition of done
├── .gitignore              # Ignored local files, cache, and virtual environments
├── pyproject.toml          # Python project configuration and test dependencies
└── GEMINI.md               # Agent guidelines and project instructions (this file)
```

> **Note:**
> - Do not create mutable aggregates like `latest.json`, `current.json`, or `data.json`.
> - `validations/` is reserved for future derived measurements; do not generate validations during the initial phase.

---

## 3. Evidence Data Models

### 3.1 Event Record (`events/YYYY-MM-DD/<event_id>.json`)
Represents an event observed from a source (currently synthetic sample source).

```json
{
  "event_id": "evt_<16_hex_chars>",
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
```

- **Timestamp Rule:** `published_at` (source publication time) and `captured_at` (observation time) must both be ISO-8601 strings with an explicit timezone offset (e.g. `+07:00` or `Z`). Never use naive datetimes.
- **Identity Hash:** `event_id = "evt_" + sha256(canonical_string)[:16]`
  - Stable fields: `source`, `published_at`, `ticker`, `title`, `content_hash`.

### 3.2 Reaction Record (`reactions/YYYY-MM-DD/<reaction_id>.json`)
Represents observed market state after a specified time window following the event.

```json
{
  "event_id": "evt_<16_hex_chars>",
  "reaction_id": "rxn_<16_hex_chars>",
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
```

- **Data Status:** Distinguish between `"synthetic"` and `"observed"`. For offline prototypes, market values must be marked `"synthetic"` or `null`—never present synthetic values as real data.
- **Linkage:** `event_id` must match an existing event record.
- **Identity Hash:** `reaction_id = "rxn_" + sha256(canonical_string)[:16]`
  - Stable fields: `event_id`, `window`, `observed_at`, `ticker`.

---

## 4. Append-Only Storage Contract

Every write operation must conform to the following invariants:

1. **Deterministic Path:** Compute destination paths based on date partition:
   - `events/{YYYY-MM-DD}/{event_id}.json`
   - `reactions/{YYYY-MM-DD}/{reaction_id}.json`
2. **New Record:** If the file does not exist, write it atomically (e.g. write to a temp file and rename).
3. **Idempotent Replay:** If the file exists and contains identical canonical content, perform a no-op without re-writing or updating file modification metadata.
4. **Conflict Guard:** If the file exists but canonical content differs, **raise a fatal error / fail loudly**. Never overwrite or silently patch evidence.

---

## 5. Building, Running, and Testing

The project uses Python (standard library preferred; `pytest` for testing).

### Local Environment Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pytest
```

### Running the Offline Pipeline
```powershell
# Run the synthetic deterministic pipeline
python -m scripts.pipeline --sample
```

### Running Tests
```powershell
# Execute the full pytest suite
pytest -v

# Run with coverage (if pytest-cov installed)
pytest --cov=scripts -v
```

### Idempotency Verification Pattern
A key requirement is proving zero file modifications on replay:
```powershell
python -m scripts.pipeline --sample
git status --porcelain  # Should show modified/untracked files on first run
python -m scripts.pipeline --sample
git status --porcelain  # Must show no additional diffs or re-written files
```

---

## 6. Scope Boundaries & Non-Goals

### In Scope (Current Phase)
- Standard library Python architecture with deterministic hashing and atomic JSON writers.
- Synthetic offline `sample` generator without network dependencies.
- Strict schema validation, timezone enforcement, and linkage verification.
- Pytest suite covering identity determinism, replay idempotency, conflict failure, and timestamps.
- GitHub Actions CI workflow running the tests and an isolated offline pipeline run.

### Explicitly Out of Scope (Do NOT Build)
- Real broker / live news ingestion.
- Databases (SQL, NoSQL, SQLite) or cache servers.
- REST / GraphQL APIs, web servers, or UIs / dashboards.
- Machine learning models, trading recommendations, or prediction scoring.
- Scheduled / cron worker deployments in CI.
- Scraping external sites or bypassing access controls.

---

## 7. Development & Contribution Conventions

- **Code Style:** Pure Python 3.10+ with clear type annotations (`typing`), docstrings, and standard library modules (`hashlib`, `json`, `datetime`, `pathlib`).
- **Purity:** Keep collectors, normalizers, hashers, and storage writers cleanly separated into modular functions or classes.
- **Testing Standard:** Every feature or bug fix must include automated pytest tests. Critical test cases include:
  1. Deterministic event ID generation.
  2. Input divergence producing different IDs.
  3. First-time evidence persistence.
  4. Exact replay idempotency (no file touched).
  5. Content divergence for identical ID failing loudly.
  6. Reaction linkage to valid `event_id`.
  7. Rejection of timezone-naive timestamps.
  8. End-to-end sample execution.
- **Git Hygiene:**
  - Never stage or commit changes unless explicitly instructed by the user.
  - Do not push to remote repositories unless requested.
  - Never commit API tokens, credentials, or private configuration.
