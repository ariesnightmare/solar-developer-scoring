# Scoring Rubric: Solar Developer Fit Model

**Version:** 1.0  
**Total possible score:** 100  
**Purpose:** Prioritize solar companies for personalized LinkedIn outreach focused on climate finance, community solar, and LMI/underserved-community impact.

---

## Overview

Seven weighted categories sum to a maximum of 100 points. All scores are integers. Evidence is drawn from source tab fields only (description, industry, size, type, name). No external web research was performed; scores reflect source-available evidence only.

| # | Category | Max Points |
|---|----------|------------|
| 1 | Business model fit | 25 |
| 2 | Community solar / community-scale relevance | 20 |
| 3 | LMI / underserved-community alignment | 15 |
| 4 | Capital need / financing relevance | 15 |
| 5 | Stage / scale / repeatability | 10 |
| 6 | Geographic relevance | 5 |
| 7 | Strategic / mission alignment | 10 |
| | **Total** | **100** |

---

## Category 1: Business Model Fit (0–25)

Measures whether the company operates as a solar project developer rather than a pure installer or contractor.

| Score Range | Criteria |
|-------------|----------|
| 20–25 | Clear developer profile: project ownership, EPC at scale, independent power producer, utility-scale or community-scale developer language; evidence of portfolio or pipeline management |
| 13–19 | Mixed signals: some developer language alongside installation; commercial or C&I focus with project complexity; EPC with repeat client base |
| 6–12 | Primarily an installer with minor developer hints; commercial solar mentioned alongside residential; some project complexity implied |
| 1–5 | Pure residential installer; solar as add-on to roofing/HVAC/electrical; no developer language |
| 0 | Obvious false positive: non-solar company, out-of-scope business, or data entry error |

**Negative modifiers applied:**
- Company name contains roofing/HVAC/electrical contractor terms AND description confirms contractor focus: –5 to –8 points
- Type = Self-Employed or Self-Owned: –3 points
- Primary Industry = Construction + no developer language: –3 points
- Primary Industry = Specialty Trade Contractors: –5 points

---

## Category 2: Community Solar / Community-Scale Relevance (0–20)

Measures explicit evidence of community solar programs, shared solar, or subscriber-based community-scale projects.

| Score Range | Criteria |
|-------------|----------|
| 16–20 | Explicit community solar program; shared solar; subscriber model; community-focused solar access language |
| 10–15 | Community-scale development implied; serves municipalities, co-ops, or community organizations; distributed generation with community language |
| 5–9 | Commercial/C&I distributed generation with adjacent community relevance; multi-site solar with some community benefit language |
| 1–4 | Vague community or social benefit language without evidence of community solar programs |
| 0 | No evidence of community solar or community-scale relevance |

---

## Category 3: LMI / Underserved-Community Alignment (0–15)

Measures explicit evidence of serving low-to-moderate income households, underserved communities, or addressing energy equity.

| Score Range | Criteria |
|-------------|----------|
| 12–15 | Explicit LMI, low-income, affordable housing solar, energy burden, environmental justice, or underserved-community language |
| 7–11 | Affordability focus; local community economic development; accessible energy language without explicit LMI terminology |
| 3–6 | Some social benefit language; mission-oriented without explicit LMI focus |
| 1–2 | Generic "clean energy for all" type language only |
| 0 | No evidence |

---

## Category 4: Capital Need / Financing Relevance (0–15)

Measures whether the company's model implies a meaningful capital need that would make project finance, tax equity, or growth financing conversations relevant.

| Score Range | Criteria |
|-------------|----------|
| 12–15 | Explicit project finance references; tax equity; capital stack; debt financing; growth capital; pipeline expansion; or large-scale repeat project needs described |
| 7–11 | Signs of repeat projects at scale that imply ongoing financing needs; multi-MW pipeline implied; developer or owner-operator language |
| 3–6 | Some evidence of recurring project activity but financing need not explicit |
| 1–2 | Minimal repeat project signals |
| 0 | One-off installer model; no evidence of financing relevance |

---

## Category 5: Stage / Scale / Repeatability (0–10)

Measures whether the company has achieved enough scale or demonstrates enough repeatability to justify outreach.

| Score Range | Criteria |
|-------------|----------|
| 8–10 | Multi-project footprint; national or regional developer; 200+ employees or explicit multi-state presence; recurring development activity described |
| 5–7 | Some evidence of scale; multi-site or multi-client; growing pipeline; 50–200 employees with meaningful project history |
| 2–4 | Limited evidence of scale; regional or local presence with some repeat work |
| 0–1 | Tiny local installer; single-market; no evidence of repeatability |

---

## Category 6: Geographic Relevance (0–5)

Measures whether the company's geography aligns with markets where distributed and community solar activity is strategically relevant.

| Score Range | Criteria |
|-------------|----------|
| 4–5 | Active in high-opportunity states for community solar (NY, IL, MD, MN, NJ, CO, MA, CA, etc.) or explicitly multi-state |
| 2–3 | Geography plausible but not especially strategic; Sunbelt commercial solar markets |
| 0–1 | Geography unclear, less relevant, or heavily concentrated in lower-opportunity markets |

---

## Category 7: Strategic / Mission Alignment (0–10)

Measures whether the company's stated mission or values align with community impact, resilience, affordability, or local economic development beyond generic sustainability language.

| Score Range | Criteria |
|-------------|----------|
| 8–10 | Explicit mission language around community impact, energy access, resilience, affordability, local economic development, or equity |
| 5–7 | Some mission language beyond generic sustainability; evidence of values alignment |
| 2–4 | Generic sustainability or clean energy language; no clear mission differentiation |
| 0–1 | Marketing copy only; no meaningful mission signal |

---

## Priority Tiers

| Tier | Score Range | Action |
|------|-------------|--------|
| A | 60–100 | Strong fit — prioritize for personalized LinkedIn outreach |
| B | 40–59 | Moderate fit — review before outreach; may be worth pursuing |
| C | 20–39 | Weak fit — likely installer or contractor; low priority |
| D | 0–19 | Very poor fit — likely false positive or out of scope |

*Note: Tier A threshold adjusted from 75 (spec default) to 60 based on calibration against source-only evidence. See `output/method_notes.md` Section 7.*

---

## Confidence Levels

| Level | Meaning |
|-------|---------|
| high | Description is detailed and evidence is clear; score reflects strong confidence |
| medium | Moderate evidence; some ambiguity remains |
| low | Thin evidence, very short description, or conflicting signals; human review recommended |

---

## Review Queue Triggers

Any of the following flags a row for human review regardless of score:

- `confidence_level = low`
- Company is primarily a residential installer or roofing/HVAC/electrical contractor
- Description < 100 characters
- Primary industry is off-topic (Oil and Gas, Security, Telecom, etc.)
- Type = Self-Employed
- Total score near a tier boundary with ambiguous evidence
- Name or description suggests possible data entry error
