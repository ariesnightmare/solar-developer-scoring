# CLAUDE.md — Solar Developer Scoring Project

## Project purpose

Score and rank solar companies from the **Solar Developers No Referrals** tab for personalized LinkedIn outreach by Jackie Logan. The goal is climate-finance prioritization, not list-building or engagement scoring.

## Source input

- File: `input/Solar Developers No Referrals.csv`
- Tab name: `Solar Developers No Referrals`
- 663 rows, 34 columns
- All rows are US companies

## How to rerun scoring

```bash
python3 scripts/score.py
```

This reads `input/Solar Developers No Referrals.csv`, runs calibration on the first 25 rows, scores all 663, and writes:

- `output/developers_scored.csv`
- `output/top_50_priority.csv`
- `output/review_queue.csv`
- `output/developers_scored.json`
- `site/data/developers_scored.json`

## Key design decisions

- **Source flags are not truth.** All four boolean flags (Solar Developer, Keywords, Residential Mention, Utility Check) are uniform across 661/663 rows. Scoring is driven by description text analysis.
- **Conservative scoring.** When evidence is thin, scores stay low. Better to flag for review than to flood the outreach queue with false positives.
- **No web research.** All evidence comes from source-tab fields only. Do not hallucinate.
- **Tier A threshold is 60**, not 75, because source-only scoring compresses the top of the range.

## Output columns

See `output/scoring_rubric.md` for category definitions.
See `output/method_notes.md` for column mapping and calibration details.

## Site

`site/index.html` is a static GitHub Pages site with search, tier filter, review queue section, and detail modals. Data is loaded from `site/data/developers_scored.json`.

## Deployment

Push to `main`. GitHub Actions (`.github/workflows/deploy-pages.yml`) publishes the `site/` directory automatically.
