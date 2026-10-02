"""
Core evidence models, hashing, timestamp validation, and append-only storage logic
for the set-prediction-reaction system.
"""

import json
import hashlib
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def validate_iso8601_tz(timestamp_str: str) -> datetime:
    """
    Validates that a timestamp string is a valid ISO-8601 datetime
    with an explicit timezone offset. Raises ValueError if naive or invalid.
    """
    if not isinstance(timestamp_str, str):
        raise ValueError(f"Timestamp must be a string, got {type(timestamp_str)}")
    
    try:
        dt = datetime.fromisoformat(timestamp_str)
    except Exception as e:
        raise ValueError(f"Invalid ISO-8601 timestamp '{timestamp_str}': {e}")
    
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Timestamp '{timestamp_str}' is timezone-naive. Explicit timezone offset required.")
    
    return dt


def canonical_json_bytes(data: Dict[str, Any]) -> bytes:
    """
    Produces deterministic canonical JSON bytes (sorted keys, compact separators).
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_event_id(event_dict: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA-256 event ID over stable fields:
    source, published_at, ticker, title, content_hash.
    Format: 'evt_' + first 16 hex characters.
    """
    stable_fields = {
        "source": event_dict.get("source"),
        "published_at": event_dict.get("published_at"),
        "ticker": event_dict.get("ticker"),
        "title": event_dict.get("title"),
        "content_hash": event_dict.get("content_hash"),
    }
    # Validate timestamps before hashing
    validate_iso8601_tz(stable_fields["published_at"])
    
    digest = hashlib.sha256(canonical_json_bytes(stable_fields)).hexdigest()
    return f"evt_{digest[:16]}"


def compute_reaction_id(reaction_dict: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA-256 reaction ID over stable fields:
    event_id, window, observed_at, ticker.
    Format: 'rxn_' + first 16 hex characters.
    """
    stable_fields = {
        "event_id": reaction_dict.get("event_id"),
        "window": reaction_dict.get("window"),
        "observed_at": reaction_dict.get("observed_at"),
        "ticker": reaction_dict.get("ticker"),
    }
    validate_iso8601_tz(stable_fields["observed_at"])
    
    digest = hashlib.sha256(canonical_json_bytes(stable_fields)).hexdigest()
    return f"rxn_{digest[:16]}"


def append_evidence(record: Dict[str, Any], evidence_type: str, base_dir: Path = Path(".")) -> Path:
    """
    Appends an evidence record in an append-only, idempotent manner.
    evidence_type: 'events' or 'reactions'.
    Rules:
    1. Computes deterministic target path based on date partition and record ID.
    2. If file does not exist, writes atomically.
    3. If file exists with identical canonical content, returns path (idempotent no-op).
    4. If file exists with conflicting content, raises FileExistsError (fails loudly).
    """
    if evidence_type not in ("events", "reactions"):
        raise ValueError(f"Invalid evidence_type: {evidence_type}. Must be 'events' or 'reactions'.")
    
    if evidence_type == "events":
        record_id = record.get("event_id")
        dt_str = record.get("published_at")
    else:
        record_id = record.get("reaction_id")
        dt_str = record.get("observed_at")
        
        # Verify event_id linkage exists
        if not record.get("event_id"):
            raise ValueError("Reaction record must reference an 'event_id'.")

    if not record_id:
        raise ValueError(f"Record is missing required identifier for type {evidence_type}.")
    
    dt = validate_iso8601_tz(dt_str)
    date_partition = dt.strftime("%Y-%m-%d")
    
    target_dir = base_dir / evidence_type / date_partition
    target_file = target_dir / f"{record_id}.json"
    
    new_canonical = canonical_json_bytes(record)
    
    if target_file.exists():
        existing_content = target_file.read_bytes()
        if existing_content == new_canonical:
            # Idempotent match
            return target_file
        else:
            raise FileExistsError(
                f"Conflict: Evidence file '{target_file}' already exists with DIFFERENT content. "
                "Historical evidence cannot be overwritten or modified."
            )
            
    # Write atomically
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Use temporary file in target directory for atomic replace
    fd, tmp_path_str = tempfile.mkstemp(dir=target_dir, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(new_canonical)
        os.replace(tmp_path_str, target_file)
    except Exception as e:
        if os.path.exists(tmp_path_str):
            os.remove(tmp_path_str)
        raise RuntimeError(f"Failed to write evidence atomically: {e}")
        
    return target_file


def create_sample_event() -> Dict[str, Any]:
    """Creates a deterministic synthetic sample event record."""
    title = "Sample event: PTT quarterly outlook update"
    content_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()
    published_at = "2026-10-02T09:00:00+07:00"
    captured_at = "2026-10-02T09:00:05+07:00"
    
    partial = {
        "source": "sample",
        "source_type": "news",
        "ticker": "PTT",
        "title": title,
        "url": None,
        "published_at": published_at,
        "captured_at": captured_at,
        "content_hash": content_hash,
        "schema_version": 1,
        "data_status": "synthetic",
    }
    event_id = compute_event_id(partial)
    event_record = {"event_id": event_id, **partial}
    return event_record


def create_sample_reaction(event_id: str) -> Dict[str, Any]:
    """Creates a deterministic synthetic sample reaction record linked to an event."""
    observed_at = "2026-10-02T09:15:00+07:00"
    window = "15m"
    ticker = "PTT"
    
    partial = {
        "event_id": event_id,
        "ticker": ticker,
        "observed_at": observed_at,
        "price": 25.10,
        "volume": 1500000,
        "benchmark": {
            "symbol": "SET",
            "value": 1420.50
        },
        "window": window,
        "schema_version": 1,
        "data_status": "synthetic",
    }
    reaction_id = compute_reaction_id(partial)
    reaction_record = {"reaction_id": reaction_id, **partial}
    return reaction_record
