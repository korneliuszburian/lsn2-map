"""CLI entry point for the generator deployment mapping pipeline."""

from __future__ import annotations

import argparse
import sys

from src.clean_clients import clean_clients
from src.enrich import enrich_clients
from src.export import export_outputs
from src.postal_reference import load_postal_reference
from src.qa import run_quality_checks


def main() -> None:
    parser = argparse.ArgumentParser(description="North America Generator Deployment Mapping Pipeline")
    parser.add_argument("--input", required=True, help="Path to input Excel workbook")
    parser.add_argument("--output", default="data/output", help="Output directory")
    parser.add_argument("--reference-sheet", default="02_Postal_Reference_MOCK", help="Sheet with postal reference data")
    args = parser.parse_args()

    print(f"Loading clients from {args.input}...")
    clients = clean_clients(args.input)
    input_row_count = len(clients)
    print(f"  Loaded {input_row_count} rows")

    print("Loading postal reference...")
    reference = load_postal_reference(excel_path=args.input, sheet=args.reference_sheet, clients=clients)
    print(f"  Reference has {len(reference)} unique geo_keys")

    print("Enriching clients with geocode data...")
    enriched = enrich_clients(clients, reference)
    matched = (enriched["geocode_status"] == "matched").sum()
    print(f"  Matched: {matched}/{input_row_count} ({matched / input_row_count:.1%})")

    print("Running QA checks...")
    exceptions = run_quality_checks(enriched)
    print(f"  Exceptions: {len(exceptions)}")

    print(f"Exporting to {args.output}/...")
    summary = export_outputs(enriched, exceptions, args.output, input_row_count)
    print("  clients_enriched.xlsx")
    print("  clients_geocoded.csv")
    print("  clients.geojson")
    print("  geocode_exceptions.csv")
    print("  run_summary.json")

    print(f"\nMatch rate: {summary['match_rate']:.1%}")
    if summary["match_rate"] < 0.98:
        print("WARNING: Match rate below 98% target", file=sys.stderr)

    print("Done.")


if __name__ == "__main__":
    main()
