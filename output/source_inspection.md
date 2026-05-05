# Source Inspection: Solar Developers No Referrals

**Tab name:** Solar Developers No Referrals  
**Source file:** `input/Solar Developers No Referrals.csv`  
**Inspection date:** 2026-05-05  
**Total rows:** 663  

---

## 1. Column Inventory

The following 34 columns were found in the source tab (exact names preserved):

| # | Column Name | Coverage |
|---|-------------|----------|
| 1 | Status | sparse |
| 2 | Find companies | sparse |
| 3 | Name | 100% |
| 4 | Description | 100% |
| 5 | Primary Industry | 99.8% |
| 6 | Size | 99.8% |
| 7 | Type | 99.7% |
| 8 | Location | 99.4% |
| 9 | Country | 99.5% |
| 10 | Domain | 99.7% |
| 11 | LinkedIn URL | 99.7% |
| 12 | Solar Developer True Or_False | 99.7% |
| 13 | Contains Relevant Keywords | 99.7% |
| 14 | Link Of_Page | 99.7% |
| 15 | Utility_Check | 99.7% |
| 16 | Residential Mention | 99.7% |
| 17 | Find warm intros to company | sparse |
| 18 | Connection Strength Normalized | sparse |
| 19 | Connector Overlap | sparse |
| 20 | Internal Connector Owner | sparse |
| 21 | Name of Person Connected | sparse |
| 22 | Linkedin Url of Connector | sparse |
| 23 | Work Email | sparse |
| 24 | Connector Current Company Name | sparse |
| 25 | Connector Current Title | sparse |
| 26 | Find Contacts at Company | sparse |
| 27 | Find people at company | sparse |
| 28 | Find people at company (SMB) | sparse |
| 29 | Find people | sparse |
| 30 | Find people at company (2) | sparse |
| 31 | Custom Waterfall | sparse |
| 32 | Send table data | sparse |
| 33 | Referral Request | sparse |
| 34 | Details | sparse |

Note: Columns 17–34 are warm-intro and relationship-management fields. They are excluded from fit scoring per project rules.

---

## 2. Flag Column Analysis

The boolean-style flag columns are nearly uniform across the dataset:

| Column | TRUE | FALSE | Empty |
|--------|------|-------|-------|
| Solar Developer True Or_False | 661 | 0 | 2 |
| Contains Relevant Keywords | 661 | 0 | 2 |
| Utility_Check | 0 | 661 | 2 |
| Residential Mention | 661 | 0 | 2 |

**Critical finding:** All four flag columns are effectively constant. They provide zero differentiation for scoring. `Residential Mention = TRUE` for 661 of 663 rows, yet the dataset clearly contains companies ranging from rooftop installers to project developers to nonprofits. The flags cannot be relied upon as truth; description analysis is the primary scoring signal.

---

## 3. Company Size Distribution

| Size Band | Count | % |
|-----------|-------|---|
| 11–50 employees | 304 | 46% |
| 51–200 employees | 183 | 28% |
| 2–10 employees | 115 | 17% |
| 201–500 employees | 37 | 6% |
| 501–1,000 employees | 8 | 1% |
| 1,001–5,000 employees | 12 | 2% |
| 10,001+ employees | 1 | <1% |
| Self-employed / other | 2 | <1% |
| Missing/data error | 1 | <1% |

The dataset skews small: ~63% of companies have fewer than 50 employees. Many are likely local installers or small contractors, not project developers.

---

## 4. Company Type Distribution

| Type | Count |
|------|-------|
| Privately Held | 518 (78%) |
| Partnership | 64 (10%) |
| Self Owned | 40 (6%) |
| Non Profit | 29 (4%) |
| Self Employed | 10 (2%) |
| Missing | 2 (<1%) |

---

## 5. Primary Industry Distribution (Top 15)

| Industry | Count |
|----------|-------|
| Renewable Energy Semiconductor Manufacturing | 168 |
| Construction | 113 |
| Solar Electric Power Generation | 106 |
| Renewables & Environment | 68 |
| Services for Renewable Energy | 61 |
| Renewable Energy Power Generation | 23 |
| Environmental Services | 19 |
| Utilities | 13 |
| Real Estate | 9 |
| Non-profit Organizations | 8 |
| Oil and Gas | 6 |
| Renewable Energy Equipment Manufacturing | 5 |
| Business Consulting and Services | 5 |
| Specialty Trade Contractors | 5 |
| Facilities Services | 4 |

"Renewable Energy Semiconductor Manufacturing" is likely a LinkedIn taxonomy artifact; many of these are actually solar installers or EPC firms, not manufacturers. "Construction" is a strong residential/contractor signal.

---

## 6. Description Signal Analysis

All 663 rows have a non-empty description (avg. 730 characters). Key signal frequencies from description text:

| Signal Pattern | Matches |
|----------------|---------|
| Community solar explicit mention | 19 |
| LMI / affordable / underserved language | 82 |
| Developer / portfolio / project finance / pipeline | 150 |
| Residential-only (residential + no commercial/community/utility) | 22 |
| Roofing / HVAC / electrical contractor language | 209 |

**Key finding:** ~32% of the dataset (209 rows) contains contractor/roofing/HVAC signals — these are the most common false-positive category. Only 19 companies explicitly mention community solar. Description text is the most reliable scoring signal available.

---

## 7. Geographic Coverage

- All 661 filled rows are United States companies.
- 2 rows have no country value (both likely US given context).
- Location data is city/state format and 99.4% complete.

---

## 8. Data Quality Issues

- **One bad Size value:** "Looks to be polish - very experienced - posted on the Pope" — clearly a data entry error. Treated as unknown size.
- **2 rows with all flags empty:** Source row IDs ~2 and ~3 appear to be near-blank or test rows. Both will be marked for review.
- **Duplicate/near-duplicate companies:** Not formally checked but likely given the data collection methodology.
- **Flag columns are not usable as truth:** See Section 2.

---

## 9. Scoring Implications

Given the above:

1. **Description text is the primary evidence source.** All rows have descriptions; the boolean flags add no differentiation.
2. **Contractor and roofing signals are the most common false-positive driver.** Conservative scoring is warranted for any row mentioning roofing, HVAC, or electrical contracting as a primary business.
3. **Company size correlates inversely with developer profile** in this dataset — larger companies (200+) are more likely to be genuine developers or EPCs; 2–10 employee firms are mostly local installers.
4. **Community solar, LMI, and financing language** are rare and should be rewarded significantly.
5. **Non-profit type** warrants a closer look — many community solar orgs are nonprofits; these may be high-fit.
