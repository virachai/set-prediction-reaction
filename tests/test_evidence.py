"""
Comprehensive test suite for set-prediction-reaction evidence pipeline,
identity determination, append-only invariants, and idempotency.
"""

import json
from pathlib import Path
import pytest

from scripts.evidence import (
    validate_iso8601_tz,
    compute_event_id,
    compute_reaction_id,
    compute_validation_id,
    append_evidence,
    create_sample_event,
    create_sample_reaction,
    create_sample_validation,
)
from scripts.pipeline import run_pipeline


def test_timestamp_validation():
    # Valid ISO-8601 with tz offset
    dt = validate_iso8601_tz("2026-10-02T09:00:00+07:00")
    assert dt.year == 2026

    dt_z = validate_iso8601_tz("2026-10-02T02:00:00Z")
    assert dt_z.year == 2026

    # Naive timestamp should raise ValueError
    with pytest.raises(ValueError, match="timezone-naive"):
        validate_iso8601_tz("2026-10-02T09:00:00")

    # Invalid string should raise ValueError
    with pytest.raises(ValueError, match="Invalid ISO-8601"):
        validate_iso8601_tz("not-a-timestamp")


def test_deterministic_event_identity():
    event1 = {
        "source": "sample",
        "published_at": "2026-10-02T09:00:00+07:00",
        "ticker": "PTT",
        "title": "Test Title",
        "content_hash": "abc123hash",
    }
    event2 = {
        "source": "sample",
        "published_at": "2026-10-02T09:00:00+07:00",
        "ticker": "PTT",
        "title": "Test Title",
        "content_hash": "abc123hash",
    }
    
    id1 = compute_event_id(event1)
    id2 = compute_event_id(event2)
    
    assert id1 == id2
    assert id1.startswith("evt_")
    assert len(id1) == 20  # "evt_" (4 chars) + 16 hex chars

    # Different input produces different identity
    event_diff = {**event1, "title": "Different Title"}
    id_diff = compute_event_id(event_diff)
    assert id_diff != id1


def test_deterministic_reaction_identity():
    rxn1 = {
        "event_id": "evt_1234567890abcdef",
        "window": "15m",
        "observed_at": "2026-10-02T09:15:00+07:00",
        "ticker": "PTT",
    }
    rxn2 = {
        "event_id": "evt_1234567890abcdef",
        "window": "15m",
        "observed_at": "2026-10-02T09:15:00+07:00",
        "ticker": "PTT",
    }
    
    id1 = compute_reaction_id(rxn1)
    id2 = compute_reaction_id(rxn2)
    
    assert id1 == id2
    assert id1.startswith("rxn_")
    assert len(id1) == 20

    rxn_diff = {**rxn1, "window": "1h"}
    assert compute_reaction_id(rxn_diff) != id1


def test_deterministic_validation_identity():
    val1 = {
        "event_id": "evt_1234567890abcdef",
        "reaction_id": "rxn_abcdef1234567890",
        "window": "15m",
        "validation_type": "reaction_metrics",
    }
    val2 = {
        "event_id": "evt_1234567890abcdef",
        "reaction_id": "rxn_abcdef1234567890",
        "window": "15m",
        "validation_type": "reaction_metrics",
    }
    id1 = compute_validation_id(val1)
    id2 = compute_validation_id(val2)
    assert id1 == id2
    assert id1.startswith("val_")
    assert len(id1) == 20

    val_diff = {**val1, "window": "1h"}
    assert compute_validation_id(val_diff) != id1


def test_append_evidence_first_write_and_idempotency(tmp_path):
    event = create_sample_event()
    
    # First write
    path1 = append_evidence(event, "events", base_dir=tmp_path)
    assert path1.exists()
    
    mtime1 = path1.stat().st_mtime
    
    # Second write (identical replay) should be idempotent
    path2 = append_evidence(event, "events", base_dir=tmp_path)
    assert path2 == path1
    mtime2 = path1.stat().st_mtime
    
    # File should not have been rewritten (mtime unchanged)
    assert mtime1 == mtime2


def test_append_evidence_conflict_fails(tmp_path):
    event = create_sample_event()
    append_evidence(event, "events", base_dir=tmp_path)
    
    # Conflicting event with same event_id but different title
    conflicting_event = dict(event)
    conflicting_event["title"] = "Tampered Title"
    
    with pytest.raises(FileExistsError, match="Conflict: Evidence file"):
        append_evidence(conflicting_event, "events", base_dir=tmp_path)


def test_reaction_requires_event_linkage(tmp_path):
    rxn = {
        "reaction_id": "rxn_test1234567890ab",
        "ticker": "PTT",
        "observed_at": "2026-10-02T09:15:00+07:00",
        "window": "15m",
        # missing event_id
    }
    with pytest.raises(ValueError, match="Reaction record must reference an 'event_id'"):
        append_evidence(rxn, "reactions", base_dir=tmp_path)


def test_validation_requires_event_and_reaction_linkage(tmp_path):
    val_missing_rxn = {
        "validation_id": "val_1234567890abcdef",
        "event_id": "evt_1234567890abcdef",
        "validated_at": "2026-10-02T09:15:05+07:00",
    }
    with pytest.raises(ValueError, match="Validation record must reference both 'event_id' and 'reaction_id'"):
        append_evidence(val_missing_rxn, "validations", base_dir=tmp_path)

    # Mismatched event_id in create_sample_validation
    event = create_sample_event()
    reaction = create_sample_reaction("evt_different123456")
    with pytest.raises(ValueError, match="does not match Event id"):
        create_sample_validation(event, reaction)


def test_validation_append_idempotency_and_conflict(tmp_path):
    event = create_sample_event()
    reaction = create_sample_reaction(event["event_id"])
    validation = create_sample_validation(event, reaction)

    # First write
    val_path = append_evidence(validation, "validations", base_dir=tmp_path)
    assert val_path.exists()
    mtime1 = val_path.stat().st_mtime

    # Idempotent replay
    val_path_2 = append_evidence(validation, "validations", base_dir=tmp_path)
    assert val_path_2 == val_path
    assert val_path.stat().st_mtime == mtime1

    # Conflicting content fails
    tampered = dict(validation)
    tampered["metrics"] = {"observed_price": 999.99}
    with pytest.raises(FileExistsError, match="Conflict: Evidence file"):
        append_evidence(tampered, "validations", base_dir=tmp_path)


def test_end_to_end_sample_pipeline(tmp_path):
    event = create_sample_event()
    event_path = append_evidence(event, "events", base_dir=tmp_path)
    assert event_path.exists()
    
    reaction = create_sample_reaction(event["event_id"])
    rxn_path = append_evidence(reaction, "reactions", base_dir=tmp_path)
    assert rxn_path.exists()
    
    validation = create_sample_validation(event, reaction)
    val_path = append_evidence(validation, "validations", base_dir=tmp_path)
    assert val_path.exists()
    
    # Verify linkage
    loaded_rxn = json.loads(rxn_path.read_text(encoding="utf-8"))
    assert loaded_rxn["event_id"] == event["event_id"]

    loaded_val = json.loads(val_path.read_text(encoding="utf-8"))
    assert loaded_val["event_id"] == event["event_id"]
    assert loaded_val["reaction_id"] == reaction["reaction_id"]
    assert loaded_val["data_status"] == "synthetic"
    
    # Second run produces no diffs (idempotent write of same objects)
    event_path_2 = append_evidence(event, "events", base_dir=tmp_path)
    rxn_path_2 = append_evidence(reaction, "reactions", base_dir=tmp_path)
    val_path_2 = append_evidence(validation, "validations", base_dir=tmp_path)
    assert event_path_2 == event_path
    assert rxn_path_2 == rxn_path
    assert val_path_2 == val_path

