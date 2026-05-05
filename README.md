# Solar Developer Scoring

A fit-based prioritization model for solar companies targeted for LinkedIn outreach by Jackie Logan. Scores and ranks 663 companies using a 7-category weighted rubric (100 pts total) focused on community solar, LMI/equity alignment, and project finance relevance.

---

## Project purpose

This is a company-fit model, not a relationship or engagement model. The goal is to identify which solar companies are the best candidates for climate-finance outreach — specifically those with:

- community solar or community-scale development activity
- LMI / underserved-community focus
- project financing relevance
- developer profile (not pure installers or contractors)

---

## Input

| Item | Value |
|------|-------|
| File | `input/Solar Developers No Referrals.csv` |
| Source tab | `Solar Developers No Referrals` |
| Rows | 663 companies |
| Geography | United States only |

Place any updated export from the source spreadsheet at the path above (same filename) before rerunning.

---

## Scoring model

Seven weighted categories sum to 100 points:

| Category | Max |
|----------|-----|
| Business model fit | 25 |
| Community solar / community-scale relevance | 20 |
| LMI / underserved-community alignment | 15 |
| Capital need / financing relevance | 15 |
| Stage / scale / repeatability | 10 |
| Geographic relevance | 5 |
| Strategic / mission alignment | 10 |

**Priority tiers:**

| Tier | Score | Action |
|------|-------|--------|
| A | 60–100 | Strong fit — prioritize for outreach |
| B | 40–59 | Moderate fit — review before outreach |
| C | 20–39 | Weak fit — likely installer or contractor |
| D | 0–19 | Very poor fit — likely false positive |

Scoring is text-based using description keyword analysis plus structured fields (industry, size, type, location). No external web research is performed.

See `output/scoring_rubric.md` for full criteria and `output/method_notes.md` for column mapping and calibration details.

---

## Outputs

| File | Description |
|------|-------------|
| `output/developers_scored.csv` | All 663 companies scored and sorted by total_score descending |
| `output/top_50_priority.csv` | Top Tier A+B companies (up to 50 rows) |
| `output/review_queue.csv` | Rows flagged for human review before outreach |
| `output/developers_scored.json` | Full scored dataset as JSON |
| `output/source_inspection.md` | Data quality and column analysis |
| `output/method_notes.md` | Column mapping, calibration, and methodology |
| `output/scoring_rubric.md` | Scoring criteria by category |
| `site/data/developers_scored.json` | JSON copy for the review site |

---

## How to rerun

```bash
python3 scripts/score.py
```

Requirements: Python 3.9+, standard library only (csv, json, re, pathlib). No external packages needed.

---

## Review site

A static GitHub Pages site is in `site/`. It provides:

- Summary counts by tier
- Searchable, filterable company table
- Detail modal with score breakdown, evidence notes, suggested LinkedIn angle, and target titles
- Review queue section with reason notes

### Run locally

```bash
cd site
python3 -m http.server 8000
# then open http://localhost:8000
```

---

## GitHub Pages deployment

Push to `main`. The workflow at `.github/workflows/deploy-pages.yml` publishes the `site/` directory automatically via GitHub Actions.

**Setup steps (one-time):**
1. Go to your repo → Settings → Pages
2. Set Source to **GitHub Actions**
3. Push to `main` to trigger the first deploy

The deployed URL will be `https://<your-username>.github.io/<repo-name>/`.

---

## Important notes

- **Human review required before any outreach.** The review queue flags borderline, small, residential, contractor, and duplicate entries.
- **Source flags are not reliable.** All four boolean flags in the source tab (Solar Developer, Keywords, Residential Mention, Utility Check) are nearly uniform (661/663 rows all TRUE for most flags). Scoring relies on description analysis.
- **No hallucination.** All evidence is source-tab only. Where evidence is weak, scores are conservative and rows are flagged for review.
