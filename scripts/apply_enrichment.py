"""
Apply Enrichment Script
========================
Merges enriched website signals into the scored dataset and rebuilds
all output files (CSV, JSON, site data).

Run this after enrich.py has finished:
    python3 scripts/apply_enrichment.py
"""

import csv
import json
from pathlib import Path

ROOT          = Path(__file__).parent.parent
SCORED_JSON   = ROOT / "output" / "developers_scored.json"
ENRICHED_JSON = ROOT / "output" / "enriched_signals.json"
OUTPUT_DIR    = ROOT / "output"
SITE_DATA_DIR = ROOT / "site" / "data"

SCORED_CSV_COLS = [
    "source_row_id", "company_name", "website", "linkedin_url", "location",
    "primary_industry", "company_size", "company_type",
    "solar_developer_flag", "keyword_flag", "utility_check", "residential_mention",
    "business_model_fit_score", "community_solar_score", "lmi_alignment_score",
    "capital_need_score", "stage_scale_score", "geographic_score",
    "strategic_alignment_score", "ecosystem_signal_score",
    "web_enrichment_bonus",
    "total_score", "priority_tier", "confidence_level", "needs_review",
    "priority_reason", "evidence_notes",
    "web_enrichment_notes", "states_mentioned", "mw_scale",
    "suggested_linkedin_angle", "suggested_target_titles",
]

REVIEW_CSV_COLS = SCORED_CSV_COLS + ["review_note"]


def assign_tier(total: int) -> str:
    if total >= 50:
        return "A"
    if total >= 35:
        return "B"
    if total >= 20:
        return "C"
    return "D"


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


def main():
    # Load base scores
    print(f"Loading {SCORED_JSON}...")
    with open(SCORED_JSON, "r") as f:
        companies = json.load(f)

    # Load enrichment signals
    if not ENRICHED_JSON.exists():
        print(f"No enrichment file found at {ENRICHED_JSON}. Run enrich.py first.")
        return

    print(f"Loading {ENRICHED_JSON}...")
    with open(ENRICHED_JSON, "r") as f:
        enriched = json.load(f)

    enriched_count = 0
    for c in companies:
        name = c["company_name"]
        signals = enriched.get(name, {})

        bonus = signals.get("enrichment_bonus", 0)
        notes = signals.get("enrichment_notes", [])
        states = signals.get("states_mentioned", [])
        mw = signals.get("mw_mentioned", 0)

        # Only apply bonus to companies that were actually enriched
        c["web_enrichment_bonus"] = bonus
        c["web_enrichment_notes"] = "; ".join(notes) if notes else ""
        c["states_mentioned"] = ", ".join(states) if states else ""
        c["mw_scale"] = f"{mw:.0f} MW" if mw > 0 else ""

        if signals.get("fetch_success"):
            # Recalculate total with web bonus added
            base = (
                c.get("business_model_fit_score", 0) +
                c.get("community_solar_score", 0) +
                c.get("lmi_alignment_score", 0) +
                c.get("capital_need_score", 0) +
                c.get("stage_scale_score", 0) +
                c.get("geographic_score", 0) +
                c.get("strategic_alignment_score", 0) +
                c.get("ecosystem_signal_score", 0)
            )
            c["total_score"] = base + bonus
            c["priority_tier"] = assign_tier(c["total_score"])
            enriched_count += 1

            # Update evidence notes to include web signals
            if notes and notes != ["site reachable but no strong signals found"]:
                existing = c.get("evidence_notes", "")
                c["evidence_notes"] = existing + " | [web] " + "; ".join(notes[:3])

    # Sort by updated total_score
    companies.sort(key=lambda x: -x["total_score"])

    # Stats
    tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for c in companies:
        tier_counts[c["priority_tier"]] += 1

    print(f"\nEnriched {enriched_count} companies with web data.")
    print(f"Tier distribution: {tier_counts}")
    print(f"Score range: {min(c['total_score'] for c in companies)}–{max(c['total_score'] for c in companies)}")

    # Write outputs
    write_json(OUTPUT_DIR / "developers_scored.json", companies)
    print(f"Updated {OUTPUT_DIR / 'developers_scored.json'}")

    write_csv(OUTPUT_DIR / "developers_scored.csv", companies, SCORED_CSV_COLS)
    print(f"Updated {OUTPUT_DIR / 'developers_scored.csv'}")

    top_50 = [c for c in companies if c["priority_tier"] in ("A", "B")][:50]
    write_csv(OUTPUT_DIR / "top_50_priority.csv", top_50, SCORED_CSV_COLS)
    print(f"Updated top_50_priority.csv ({len(top_50)} rows)")

    review_q = [c for c in companies if c.get("needs_review")]
    write_csv(OUTPUT_DIR / "review_queue.csv", review_q, REVIEW_CSV_COLS)
    print(f"Updated review_queue.csv ({len(review_q)} rows)")

    write_json(SITE_DATA_DIR / "developers_scored.json", companies)
    print(f"Updated site/data/developers_scored.json")

    print("\nDone. Now run:")
    print("  git add -A && git commit -m 'Apply web enrichment' && git push")
    print("to push the updated scores live.")


if __name__ == "__main__":
    main()
