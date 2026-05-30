#!/usr/bin/env python3
# run_pipeline.py – Orchestrates the full ETL pipeline
"""
Usage:
    python run_pipeline.py            # full run
    python run_pipeline.py --dry-run  # extract + transform only, skip load
"""

import argparse
import time
from etl.extract   import extract_all
from etl.transform import transform_all
from etl.load      import load_all
from etl.logger    import get_logger

log = get_logger("pipeline")


def run(dry_run: bool = False) -> None:
    start = time.perf_counter()
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║   Supply Chain ETL Pipeline  – starting                 ║")
    log.info("╚══════════════════════════════════════════════════════════╝")

    sources     = extract_all()
    transformed = transform_all(sources)

    issues = transformed.get("_validation_issues", [])
    if issues:
        log.warning(f"{len(issues)} validation issue(s) found – see warnings above")

    if dry_run:
        log.info("Dry-run mode: skipping LOAD phase")
    else:
        load_all(transformed)

    elapsed = time.perf_counter() - start
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info(f"║   Pipeline finished in {elapsed:.1f}s                         ║")
    log.info("╚══════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supply Chain ETL Pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run extract + transform only, skip load")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
