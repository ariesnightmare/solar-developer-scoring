# Method Notes: Solar Developer Scoring Model

**Project:** Solar Developer Prioritization for LinkedIn Outreach  
**Analyst:** Jackie Logan outreach prioritization  
**Date:** 2026-05-05  
**Script:** `scripts/score.py`  

---

## 1. Source-to-Normalized Column Mapping

The following mapping converts exact source column names to normalized schema field names:

| Normalized Field | Source Column (exact) |
|------------------|-----------------------|
| `source_row_id` | original row number from source tab (1-indexed) |
| `company_name` | `Name` |
| `company_description` | `Description` |
| `primary_industry` | `Primary Industry` |
| `company_size` | `Size` |
| `company_type` | `Type` |
| `location` | `Location` |
| `country` | `Country` |
| `website` | `Domain` |
| `linkedin_url` | `LinkedIn URL` |
| `source_page_url` | `Link Of_Page` |
| `solar_developer_flag` | `Solar Developer True Or_False` |
| `keyword_flag` | `Contains Relevant Keywords` |
| `utility_check` | `Utility_Check` |
| `residential_mention` | `Residential Mention` |
| `warm_intro_status` | `Find warm intros to company` |
| `connection_strength_normalized` | `Connection Strength Normalized` |
| `connector_overlap` | `Connector Overlap` |
| `internal_connector_owner` | `Internal Connector Owner` |
| `name_of_person_connected` | `Name of Person Connected` |
| `linkedin_url_of_connector` | `Linkedin Url of Connector` |
| `work_email` | `Work Email` |
| `connector_current_company_name` | `Connector Current Company Name` |
| `connector_current_title` | `Connector Current Title` |
| `send_table_data_status` | `Send table data` |
| `referral_request` | `Referral Request` |
| `details` | `Details ` (note: trailing space in source) |

---

## 2. Which Fields Drive Scoring

**Primary scoring inputs (used in the fit model):**
- `Name` — used for name-based signals (roofing, HVAC, contractor indicators in the company name)
- `Description` — primary evidence source; all rows have a description; this is the main discriminator
- `Primary Industry` — taxonomy signal; "Construction" and "Specialty Trade Contractors" are negative signals; "Solar Electric Power Generation" is a positive signal
- `Size` — size band proxy for developer vs. installer profile
- `Type` — "Non Profit" and "Privately Held" with dev signals are positives; "Self Employed" and "Self Owned" are negative signals
- `Location` / `Country` — geographic relevance signal
- `Domain` — used to verify URL exists; not scored directly
- `LinkedIn URL` — used for verification link; not scored directly
- `Solar Developer True Or_False` — treated as soft hint only (uniform in this dataset)
- `Contains Relevant Keywords` — treated as soft hint only (uniform in this dataset)
- `Utility_Check` — triggers additional review flag when TRUE (none in this dataset)
- `Residential Mention` — soft downward signal when combined with no developer/commercial evidence

**Excluded from fit scoring (warm-intro metadata):**
- `Find warm intros to company`
- `Connection Strength Normalized`
- `Connector Overlap`
- `Internal Connector Owner`
- `Name of Person Connected`
- `Linkedin Url of Connector`
- `Work Email`
- `Connector Current Company Name`
- `Connector Current Title`
- `Send table data`
- `Referral Request`
- `Details`

Warm-intro fields are preserved in outputs as metadata but do not influence fit scores. This is a company-fit model, not a relationship-score model.

---

## 3. Data Cleaning Applied

1. All header names trimmed of leading/trailing whitespace (source has trailing space on "Status " and "Details ").
2. Boolean columns (`Solar Developer True Or_False`, `Contains Relevant Keywords`, `Utility_Check`, `Residential Mention`) normalized to uppercase TRUE/FALSE/UNKNOWN.
3. `source_row_id` assigned as the original 1-based row index in the CSV.
4. URLs in `Domain` and `LinkedIn URL` retained as-is from source (not fetched or verified externally).
5. Descriptions with only whitespace treated as empty.
6. Size value "Looks to be polish - very experienced - posted on the Pope" treated as unknown/data error.

---

## 4. Flag Analysis Finding

**Critical:** All four boolean flags (`Solar Developer True Or_False`, `Contains Relevant Keywords`, `Utility_Check`, `Residential Mention`) are effectively constant:
- 661/663 rows: `Solar Developer True Or_False = TRUE`
- 661/663 rows: `Contains Relevant Keywords = TRUE`
- 661/663 rows: `Utility_Check = FALSE`
- 661/663 rows: `Residential Mention = TRUE`

These flags provide zero differentiation. The scoring model relies almost entirely on description text analysis, industry taxonomy, size, and type.

---

## 5. Scoring Approach

All scoring is text-based using keyword and pattern matching on the `Description` field plus structured fields (`Primary Industry`, `Size`, `Type`, `company_name`). No external web requests were made; all evidence comes from source tab fields only.

The model does not hallucinate or invent facts. Where evidence is weak or ambiguous, scores are kept low and rows are flagged for human review.

---

## 6. Calibration: 25-Row Sample Results

A 25-row calibration pass was run before full scoring to validate that:
- Residential installers and contractor-type businesses were not being over-scored
- Community solar and developer-profile companies scored meaningfully higher
- Conservative defaults were appropriate

**Sample calibration findings:**

| Category | Pre-calibration avg | Post-calibration avg |
|----------|--------------------|--------------------|
| Obvious residential/contractor rows | ~28 | ~15 |
| Mixed installer+developer rows | ~42 | ~32 |
| Clear community solar/developer rows | ~72 | ~68 |

**Calibration adjustments made:**
- Reduced base score for rows with roofing/HVAC/contractor name signals from 8 → 3 (business_model_fit)
- Reduced residential-only description score from 5 → 2 (business_model_fit)
- Set minimum community_solar_score to 0 (no partial credit) unless explicit language found
- Applied a size penalty for Self-Employed and Self-Owned type companies
- Introduced a `contractor_penalty` that reduces business_model_fit by up to 8 points when roofing/HVAC/electrical signals appear in both name AND description

**Conservative bias is intentional.** It is better to send a human reviewer to check a borderline company than to flood Jackie's outreach queue with installers.

---

## 7. Tier Definitions

After reviewing the calibrated score distribution:

| Tier | Score Range | Interpretation |
|------|-------------|---------------|
| A | 60–100 | Strong fit — prioritize for outreach |
| B | 40–59 | Moderate fit — worth reviewing |
| C | 20–39 | Weak fit — likely installer or contractor |
| D | 0–19 | Very poor fit — likely false positive or out of scope |

**Threshold adjustment note:** The original spec suggested Tier A = 75–100. After calibration, the score distribution showed that very few companies score above 70 using evidence-only scoring (no web research), so the Tier A threshold was lowered to 60 to produce a usable priority queue. The 75+ bar would have yielded fewer than 10 companies. This is documented here per the spec's instruction to document threshold changes.

---

## 8. Review Queue Criteria

A row is added to `output/review_queue.csv` when any of the following apply:
- `confidence_level = low` (insufficient description evidence)
- Company name or description strongly suggests residential/contractor but `solar_developer_flag = TRUE`
- Size is Self-Employed or 2–10 employees with no developer language
- `utility_check = TRUE` (triggers review per spec)
- Total score is within 5 points of a tier boundary and evidence is ambiguous
- Description is very short (< 100 characters) or highly generic
- The `Primary Industry` suggests off-topic (Oil and Gas, Security, Telecom, etc.)
