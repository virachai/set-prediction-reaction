"""
Pipeline runner script for set-prediction-reaction.
Executes the minimal offline flow:
source event -> normalize -> compute event_id -> append event -> create reaction -> append reaction.
"""

import argparse
import sys
from pathlib import Path

from scripts.evidence import (
    create_sample_event,
    create_sample_reaction,
    append_evidence,
)


def run_pipeline(sample: bool = True) -> None:
    if not sample:
        print("Error: Only --sample is supported in this offline experimental phase.", file=sys.stderr)
        sys.exit(1)

    print("Running set-prediction-reaction offline pipeline (--sample)...")
    
    # 1. Create and write event evidence
    event = create_sample_event()
    event_path = append_evidence(event, "events")
    print(f"[+] Event evidence written: {event_path} (ID: {event['event_id']})")
    
    # 2. Create and write reaction evidence linked to event
    reaction = create_sample_reaction(event["event_id"])
    reaction_path = append_evidence(reaction, "reactions")
    print(f"[+] Reaction evidence written: {reaction_path} (ID: {reaction['reaction_id']}, Event ID: {event['event_id']})")
    
    print("Pipeline execution completed successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the set-prediction-reaction evidence pipeline.")
    parser.add_argument("--sample", action="store_true", help="Run with synthetic sample source data.")
    args = parser.parse_args()

    if not args.sample:
        parser.print_help()
        sys.exit(1)

    try:
        run_pipeline(sample=args.sample)
    except Exception as e:
        print(f"Pipeline execution failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
