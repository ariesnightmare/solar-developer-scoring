"""
Solar Developer Fit Scoring Script
===================================
Scores 663 companies from the "Solar Developers No Referrals" tab against
a 7-category weighted rubric (100 pts total) for climate-finance outreach
prioritization.

Evidence source: source tab fields only (no external web requests).
All scoring is conservative: when evidence is weak, scores are low.
"""

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
INPUT_CSV = ROOT / "input" / "Solar Developers No Referrals.csv"
OUTPUT_DIR = ROOT / "output"
SITE_DATA_DIR = ROOT / "site" / "data"

OUTPUT_DIR.mkdir(exist_ok=True)
SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# Pattern libraries
# ─────────────────────────────────────────────

# HIGH-FIT patterns
P_DEVELOPER = re.compile(
    r"\b(develop(?:er|ment|s|ed|ing)|project develop|project owner|project finance|"
    r"independent power producer|ipp|owner.operat|portfolio|pipeline|offtake|"
    r"power purchase agreement|ppa|epc.{0,30}(develop|own)|asset manag|"
    r"project sponsor|ground.up|build.own.operat|greenfield)\b",
    re.I,
)
P_COMMUNITY_SOLAR = re.compile(
    r"\b(community solar|shared solar|community.scale solar|"
    r"solar garden|virtual net meter|vnm|community energy|"
    r"community.owned|subscriber|membership.based solar|"
    r"community distributed generation|cdg)\b",
    re.I,
)
P_LMI = re.compile(
    r"\b(lmi|low.to.moderate income|low income|affordable.{0,20}solar|"
    r"affordable housing|energy burden|energy poverty|energy equity|"
    r"environmental justice|ej |underserved|disadvantaged communit|"
    r"affordable energ|community benefit|low.cost solar|"
    r"income.qualified|weatherization|solar for all)\b",
    re.I,
)
P_FINANCING = re.compile(
    r"\b(project finance|tax equity|debt financ|capital stack|"
    r"growth capital|credit facilit|construction financ|bridge loan|"
    r"mezzanine|fund|institutional capital|asset.backed|"
    r"revolving credit|equity financ|raise capital|investment bank|"
    r"fund manag|portfolio financ)\b",
    re.I,
)
P_MISSION = re.compile(
    r"\b(energy access|energy resilience|clean energy access|"
    r"energy independence|community impact|local economic|"
    r"resilience|affordable clean energy|clean energy equity|"
    r"climate justice|just transition|community benefit|"
    r"energy democracy|economic empowerment|inclusive|"
    r"underserved|equitable|clean energy for all)\b",
    re.I,
)
P_UTILITY_SCALE = re.compile(
    r"\b(utility.scale|utility scale|large.scale|grid.scale|"
    r"utility.{0,20}solar|transmission|grid operator|bulk power)\b",
    re.I,
)
P_COMMERCIAL = re.compile(
    r"\b(commercial|c&i|commercial and industrial|corporate|"
    r"municipal|government|school|nonprofit.{0,20}solar|"
    r"agricultural|farm|rooftop commercial|distributed generation|dg |"
    r"distributed solar|behind.the.meter|btm|microgrid)\b",
    re.I,
)
P_REPEAT_SCALE = re.compile(
    r"\b(multi.state|nationwide|national|regional|"
    r"megawatt|mw |gwh|hundreds of|thousands of|"
    r"multi.site|portfolio of|fleet of|large portfolio|"
    r"across \d+ state|across multiple state|"
    r"10\d{2,}|[2-9]\d{2,} (project|system|install|customer)|"
    r"track record|proven|established developer)\b",
    re.I,
)

# NEGATIVE / LOW-FIT patterns
P_ROOFING = re.compile(
    r"\b(roof|roofer|roofing|shingle|gutter|siding|"
    r"hvac|heating.{0,10}cool|air condition|furnace|ductwork|"
    r"electrician|electrical contract|plumb|pest control|"
    r"landscap|tree trim|pool|windows and doors)\b",
    re.I,
)
P_RESIDENTIAL_ONLY = re.compile(
    r"\b(residential|homeowner|home solar|home owner|"
    r"single.family|single family|your home|your roof|"
    r"savings on your electric bill|eliminate your electric bill)\b",
    re.I,
)
P_NO_DEV = re.compile(
    r"\b(install(?:er|ation|ing|s)|contractor|service technician|"
    r"repair|maintenance|handyman|solar panel clean)\b",
    re.I,
)

# High-opportunity community solar states
HIGH_OPP_STATES = {
    "NY", "IL", "MD", "MN", "NJ", "CO", "MA", "CA", "ME", "OR",
    "VA", "WA", "CT", "NM", "HI", "DC", "RI",
}
STATE_ABBREVS = re.compile(
    r",\s*([A-Z]{2})$|,\s*([A-Z]{2})\s*\d{5}",
)

# Industry classifications
DEVELOPER_INDUSTRIES = {
    "Solar Electric Power Generation",
    "Renewable Energy Power Generation",
}
INSTALLER_INDUSTRIES = {
    "Construction",
    "Specialty Trade Contractors",
    "Facilities Services",
}
OFF_TOPIC_INDUSTRIES = {
    "Oil and Gas",
    "Security and Investigations",
    "Telecommunications",
    "Electric Lighting Equipment Manufacturing",
    "Appliances, Electrical, and Electronics Manufacturing",
}

# Size bands
SIZE_ORDER = [
    "Self-employed",
    "2-10 employees",
    "11-50 employees",
    "51-200 employees",
    "201-500 employees",
    "501-1,000 employees",
    "1,001-5,000 employees",
    "5,001-10,000 employees",
    "10,001+ employees",
]


def normalize_bool(val: str) -> str:
    v = val.strip().upper()
    if v in ("TRUE", "YES", "1", "T", "Y"):
        return "TRUE"
    if v in ("FALSE", "NO", "0", "F", "N"):
        return "FALSE"
    return "UNKNOWN"


def size_rank(size_str: str) -> int:
    s = size_str.strip()
    try:
        return SIZE_ORDER.index(s)
    except ValueError:
        return -1


def extract_state(location: str) -> str:
    m = STATE_ABBREVS.search(location.strip())
    if m:
        return m.group(1) or m.group(2)
    # Try last two-letter token
    parts = re.split(r"[,\s]+", location.strip())
    for p in reversed(parts):
        if len(p) == 2 and p.isalpha():
            return p.upper()
    return ""


# ─────────────────────────────────────────────
# Scoring functions
# ─────────────────────────────────────────────

def score_business_model_fit(row: dict) -> tuple[int, list[str]]:
    """Category 1: Business model fit (0–25)"""
    notes = []
    name = row["Name"].strip()
    desc = row["company_description"]
    industry = row["Primary Industry"].strip()
    company_type = row["Type"].strip()

    score = 0

    # Base from industry
    if industry in DEVELOPER_INDUSTRIES:
        score += 10
        notes.append("developer industry")
    elif industry in INSTALLER_INDUSTRIES:
        score += 2
        notes.append("installer/contractor industry")
    elif industry in OFF_TOPIC_INDUSTRIES:
        notes.append("off-topic industry")
        return 0, ["off-topic industry — likely false positive"]
    else:
        score += 5  # neutral industry (e.g., Renewables & Environment)

    # Developer language in description
    dev_matches = P_DEVELOPER.findall(desc)
    if len(dev_matches) >= 3:
        score += 10
        notes.append("strong developer language")
    elif len(dev_matches) >= 1:
        score += 5
        notes.append("some developer language")

    # Commercial/C&I/DG signals
    if P_COMMERCIAL.search(desc):
        score += 3
        notes.append("commercial/DG signals")

    # Contractor/roofing penalty — check both name and description
    roofing_name = P_ROOFING.search(name)
    roofing_desc = P_ROOFING.search(desc)
    if roofing_name and roofing_desc:
        score -= 8
        notes.append("roofing/HVAC in name+desc (strong penalty)")
    elif roofing_name or (roofing_desc and not P_COMMERCIAL.search(desc)):
        score -= 4
        notes.append("roofing/HVAC signals")

    # Pure residential-only
    if P_RESIDENTIAL_ONLY.search(desc) and not P_COMMERCIAL.search(desc) and not P_DEVELOPER.search(desc):
        score -= 5
        notes.append("residential-only profile")

    # Self-employed/self-owned penalty
    if company_type in ("Self Employed", "Self Owned", "Self-employed"):
        score -= 3
        notes.append("self-employed/owned type")

    # No developer language at all
    if not P_DEVELOPER.search(desc) and not P_COMMERCIAL.search(desc):
        score -= 3
        notes.append("no developer or commercial language")

    return max(0, min(25, score)), notes


def score_community_solar(row: dict) -> tuple[int, list[str]]:
    """Category 2: Community solar / community-scale relevance (0–20)"""
    desc = row["company_description"]
    notes = []
    score = 0

    cs_matches = P_COMMUNITY_SOLAR.findall(desc)
    if len(cs_matches) >= 2:
        score = 18
        notes.append("explicit community solar (multiple mentions)")
    elif len(cs_matches) == 1:
        score = 14
        notes.append("explicit community solar")
    elif P_COMMERCIAL.search(desc) and P_DEVELOPER.search(desc):
        score = 6
        notes.append("commercial DG developer (adjacent community relevance)")
    elif P_COMMERCIAL.search(desc):
        score = 3
        notes.append("commercial solar signals")

    return max(0, min(20, score)), notes


def score_lmi_alignment(row: dict) -> tuple[int, list[str]]:
    """Category 3: LMI / underserved-community alignment (0–15)"""
    desc = row["company_description"]
    notes = []
    score = 0

    lmi_matches = P_LMI.findall(desc)
    if len(lmi_matches) >= 3:
        score = 14
        notes.append("strong LMI/equity language (3+ signals)")
    elif len(lmi_matches) == 2:
        score = 10
        notes.append("LMI/equity language (2 signals)")
    elif len(lmi_matches) == 1:
        score = 6
        notes.append("LMI/equity language (1 signal)")
    elif P_MISSION.search(desc):
        score = 3
        notes.append("mission/affordability language (no explicit LMI)")

    return max(0, min(15, score)), notes


def score_capital_need(row: dict) -> tuple[int, list[str]]:
    """Category 4: Capital need / financing relevance (0–15)"""
    desc = row["company_description"]
    industry = row["Primary Industry"].strip()
    notes = []
    score = 0

    fin_matches = P_FINANCING.findall(desc)
    if len(fin_matches) >= 2:
        score = 13
        notes.append("explicit financing language (2+ signals)")
    elif len(fin_matches) == 1:
        score = 9
        notes.append("financing language mentioned")
    elif P_DEVELOPER.search(desc) and P_REPEAT_SCALE.search(desc):
        score = 7
        notes.append("developer at scale implies financing needs")
    elif P_DEVELOPER.search(desc):
        score = 4
        notes.append("developer language implies some financing need")
    elif P_COMMERCIAL.search(desc) and P_REPEAT_SCALE.search(desc):
        score = 3
        notes.append("commercial at scale (weak financing relevance)")

    return max(0, min(15, score)), notes


def score_stage_scale(row: dict) -> tuple[int, list[str]]:
    """Category 5: Stage / scale / repeatability (0–10)"""
    desc = row["company_description"]
    size = row["Size"].strip()
    company_type = row["Type"].strip()
    notes = []
    score = 0

    size_r = size_rank(size)

    # Scale from description signals
    if P_REPEAT_SCALE.search(desc):
        score += 5
        notes.append("scale/repeat signals in description")
    elif P_DEVELOPER.search(desc):
        score += 2
        notes.append("developer implies some repeatability")

    # Size contribution
    if size_r >= 7:  # 1001+
        score += 4
        notes.append("large company (1001+ employees)")
    elif size_r >= 5:  # 501-1000
        score += 3
        notes.append("mid-large company (501-1000)")
    elif size_r >= 4:  # 201-500
        score += 2
        notes.append("mid company (201-500)")
    elif size_r >= 3:  # 51-200
        score += 1
        notes.append("smaller company (51-200)")

    # Penalty for tiny/self-employed
    if company_type in ("Self Employed", "Self-employed") or size_r <= 1:
        score -= 2
        notes.append("very small scale penalty")

    return max(0, min(10, score)), notes


def score_geographic(row: dict) -> tuple[int, list[str]]:
    """Category 6: Geographic relevance (0–5)"""
    location = row["Location"].strip()
    notes = []

    state = extract_state(location)
    if state in HIGH_OPP_STATES:
        notes.append(f"high-opportunity state ({state})")
        return 4, notes

    # Multi-state or national language in description
    if P_REPEAT_SCALE.search(row["company_description"]) and re.search(
        r"\b(multi.state|nation|region|across \d+ state)\b", row["company_description"], re.I
    ):
        notes.append("multi-state/national footprint")
        return 5, notes

    if location:
        notes.append(f"US location ({location}) - moderate relevance")
        return 2, notes

    notes.append("location unclear")
    return 1, notes


def score_strategic_alignment(row: dict) -> tuple[int, list[str]]:
    """Category 7: Strategic / mission alignment (0–10)"""
    desc = row["company_description"]
    company_type = row["Type"].strip()
    notes = []
    score = 0

    mission_matches = P_MISSION.findall(desc)
    if len(mission_matches) >= 3:
        score = 9
        notes.append("strong mission alignment (3+ signals)")
    elif len(mission_matches) == 2:
        score = 7
        notes.append("mission alignment (2 signals)")
    elif len(mission_matches) == 1:
        score = 5
        notes.append("some mission language")
    elif P_LMI.search(desc) or P_COMMUNITY_SOLAR.search(desc):
        score = 6
        notes.append("community/LMI focus implies mission alignment")

    # Nonprofit bonus
    if company_type == "Non Profit":
        score += 2
        notes.append("nonprofit org type")

    # Generic marketing only penalty
    if score == 0 and not P_DEVELOPER.search(desc):
        notes.append("generic or minimal mission language")

    return max(0, min(10, score)), notes


# ─────────────────────────────────────────────
# Review / confidence logic
# ─────────────────────────────────────────────

def assess_confidence_and_review(row: dict, scores: dict, total: int) -> tuple[str, bool, str]:
    desc = row["company_description"]
    name = row["Name"].strip()
    industry = row["Primary Industry"].strip()
    company_type = row["Type"].strip()
    size = row["Size"].strip()

    review_reasons = []

    # Short description
    if len(desc.strip()) < 100:
        review_reasons.append("very short description — insufficient evidence")

    # Off-topic industry
    if industry in OFF_TOPIC_INDUSTRIES:
        review_reasons.append(f"off-topic industry: {industry}")

    # Self-employed type
    if company_type in ("Self Employed", "Self-employed"):
        review_reasons.append("self-employed type — likely individual, not a company")

    # Strong contractor signals with no developer language
    if P_ROOFING.search(name) and not P_DEVELOPER.search(desc):
        review_reasons.append("contractor name + no developer language")

    # Residential-only with solar flag
    if P_RESIDENTIAL_ONLY.search(desc) and not P_COMMERCIAL.search(desc) and not P_DEVELOPER.search(desc):
        review_reasons.append("appears to be residential-only installer")

    # Size = 2-10 or self-employed with no scale signals
    if size in ("2-10 employees", "Self-employed") and not P_REPEAT_SCALE.search(desc):
        review_reasons.append("very small company (2-10) with no scale evidence")

    # Score near tier boundary (within 4 points of 40 or 60)
    if abs(total - 40) <= 4 or abs(total - 60) <= 4:
        review_reasons.append(f"score {total} is near tier boundary — borderline case")

    # Data error in size field
    if size and size not in SIZE_ORDER and size != "":
        review_reasons.append(f"data quality issue in Size field: {size[:40]}")

    needs_review = len(review_reasons) > 0

    # Confidence level
    if len(desc.strip()) < 150 or industry in OFF_TOPIC_INDUSTRIES:
        confidence = "low"
    elif total >= 50 and len(review_reasons) == 0:
        confidence = "high"
    elif total >= 30 and len(review_reasons) <= 1:
        confidence = "medium"
    elif len(review_reasons) >= 2:
        confidence = "low"
    else:
        confidence = "medium"

    review_note = "; ".join(review_reasons) if review_reasons else ""
    return confidence, needs_review, review_note


def assign_tier(total: int) -> str:
    if total >= 50:
        return "A"
    if total >= 35:
        return "B"
    if total >= 20:
        return "C"
    return "D"


def build_priority_reason(scores: dict, total: int, row: dict) -> str:
    reasons = []
    if scores["community_solar"] >= 12:
        reasons.append("community solar developer")
    if scores["lmi"] >= 8:
        reasons.append("LMI/equity focus")
    if scores["capital"] >= 8:
        reasons.append("financing relevance")
    if scores["business_model"] >= 15:
        reasons.append("strong developer profile")
    elif scores["business_model"] >= 8:
        reasons.append("developer signals present")
    if scores["stage_scale"] >= 6:
        reasons.append("meaningful scale")
    if scores["strategic"] >= 7:
        reasons.append("mission alignment")
    if not reasons:
        if total >= 40:
            reasons.append("moderate fit — review for context")
        else:
            reasons.append("weak fit — likely installer or contractor")
    return "; ".join(reasons)


def build_evidence_notes(scores: dict, all_notes: dict) -> str:
    parts = []
    for cat, notes in all_notes.items():
        if notes:
            parts.append(f"[{cat}] {', '.join(notes)}")
    return " | ".join(parts) if parts else "no strong signals found"


def build_linkedin_angle(row: dict, scores: dict, total: int) -> str:
    desc = row["company_description"]
    if scores["community_solar"] >= 12:
        return "Reference community solar portfolio; discuss subscriber model or shared access programs"
    if scores["lmi"] >= 8:
        return "Lead with energy equity and affordable access angle; ask about LMI project pipeline"
    if scores["capital"] >= 8:
        return "Open with project finance or capital stack conversation; reference growth pipeline"
    if scores["business_model"] >= 15:
        return "Developer-to-developer outreach; reference project pipeline and financing solutions"
    if total >= 40:
        return "Explore commercial solar project pipeline; ask about financing needs for growth"
    return "Low priority — verify fit before outreach"


def build_target_titles(row: dict, scores: dict) -> str:
    titles = []
    if scores["business_model"] >= 15:
        titles = ["VP of Development", "Director of Project Finance", "CEO", "CFO", "Head of Capital Markets"]
    elif scores["community_solar"] >= 10:
        titles = ["Director of Community Solar", "VP of Development", "CEO", "Director of Programs"]
    elif scores["business_model"] >= 8:
        titles = ["VP of Development", "CEO", "Director of Business Development", "CFO"]
    else:
        titles = ["CEO", "Founder", "Director of Business Development"]
    return "; ".join(titles)


# ─────────────────────────────────────────────
# Main scoring loop
# ─────────────────────────────────────────────

def score_row(row_num: int, raw: dict) -> dict:
    row = {
        "source_row_id": row_num,
        "company_name": raw.get("Name", "").strip(),
        "company_description": raw.get("Description", "").strip(),
        "primary_industry": raw.get("Primary Industry", "").strip(),
        "company_size": raw.get("Size", "").strip(),
        "company_type": raw.get("Type", "").strip(),
        "location": raw.get("Location", "").strip(),
        "country": raw.get("Country", "").strip(),
        "website": raw.get("Domain", "").strip(),
        "linkedin_url": raw.get("LinkedIn URL", "").strip(),
        "source_page_url": raw.get("Link Of_Page", "").strip(),
        "solar_developer_flag": normalize_bool(raw.get("Solar Developer True Or_False", "")),
        "keyword_flag": normalize_bool(raw.get("Contains Relevant Keywords", "")),
        "utility_check": normalize_bool(raw.get("Utility_Check", "")),
        "residential_mention": normalize_bool(raw.get("Residential Mention", "")),
        # warm-intro metadata (not used in scoring)
        "warm_intro_status": raw.get("Find warm intros to company", "").strip(),
        "connection_strength_normalized": raw.get("Connection Strength Normalized", "").strip(),
        "connector_overlap": raw.get("Connector Overlap", "").strip(),
        "internal_connector_owner": raw.get("Internal Connector Owner", "").strip(),
        "name_of_person_connected": raw.get("Name of Person Connected", "").strip(),
        "linkedin_url_of_connector": raw.get("Linkedin Url of Connector", "").strip(),
        "work_email": raw.get("Work Email", "").strip(),
        "connector_current_company_name": raw.get("Connector Current Company Name", "").strip(),
        "connector_current_title": raw.get("Connector Current Title", "").strip(),
        "send_table_data_status": raw.get("Send table data", "").strip(),
        "referral_request": raw.get("Referral Request", "").strip(),
        "details": raw.get("Details ", raw.get("Details", "")).strip(),
        # pass-through for scoring functions
        "Name": raw.get("Name", "").strip(),
        "Primary Industry": raw.get("Primary Industry", "").strip(),
        "Size": raw.get("Size", "").strip(),
        "Type": raw.get("Type", "").strip(),
        "Location": raw.get("Location", "").strip(),
    }

    bm_score, bm_notes = score_business_model_fit(row)
    cs_score, cs_notes = score_community_solar(row)
    lmi_score, lmi_notes = score_lmi_alignment(row)
    cap_score, cap_notes = score_capital_need(row)
    ss_score, ss_notes = score_stage_scale(row)
    geo_score, geo_notes = score_geographic(row)
    strat_score, strat_notes = score_strategic_alignment(row)

    scores = {
        "business_model": bm_score,
        "community_solar": cs_score,
        "lmi": lmi_score,
        "capital": cap_score,
        "stage_scale": ss_score,
        "geographic": geo_score,
        "strategic": strat_score,
    }
    all_notes = {
        "biz": bm_notes,
        "comm": cs_notes,
        "lmi": lmi_notes,
        "cap": cap_notes,
        "scale": ss_notes,
        "geo": geo_notes,
        "strat": strat_notes,
    }

    total = sum(scores.values())
    tier = assign_tier(total)
    confidence, needs_review, review_note = assess_confidence_and_review(row, scores, total)
    priority_reason = build_priority_reason(scores, total, row)
    evidence_notes = build_evidence_notes(scores, all_notes)
    linkedin_angle = build_linkedin_angle(row, scores, total)
    target_titles = build_target_titles(row, scores)

    return {
        "source_row_id": row["source_row_id"],
        "company_name": row["company_name"],
        "website": row["website"],
        "linkedin_url": row["linkedin_url"],
        "location": row["location"],
        "primary_industry": row["primary_industry"],
        "company_size": row["company_size"],
        "company_type": row["company_type"],
        "solar_developer_flag": row["solar_developer_flag"],
        "keyword_flag": row["keyword_flag"],
        "utility_check": row["utility_check"],
        "residential_mention": row["residential_mention"],
        "business_model_fit_score": bm_score,
        "community_solar_score": cs_score,
        "lmi_alignment_score": lmi_score,
        "capital_need_score": cap_score,
        "stage_scale_score": ss_score,
        "geographic_score": geo_score,
        "strategic_alignment_score": strat_score,
        "total_score": total,
        "priority_tier": tier,
        "confidence_level": confidence,
        "needs_review": needs_review,
        "review_note": review_note,
        "priority_reason": priority_reason,
        "evidence_notes": evidence_notes,
        "suggested_linkedin_angle": linkedin_angle,
        "suggested_target_titles": target_titles,
        # metadata (not in spec output cols but useful for site)
        "source_page_url": row["source_page_url"],
        "company_description": row["company_description"],
        "warm_intro_status": row["warm_intro_status"],
        "connection_strength_normalized": row["connection_strength_normalized"],
        "name_of_person_connected": row["name_of_person_connected"],
        "connector_current_title": row["connector_current_title"],
    }


# ─────────────────────────────────────────────
# CSV output columns (per spec)
# ─────────────────────────────────────────────

SCORED_CSV_COLS = [
    "source_row_id",
    "company_name",
    "website",
    "linkedin_url",
    "location",
    "primary_industry",
    "company_size",
    "company_type",
    "solar_developer_flag",
    "keyword_flag",
    "utility_check",
    "residential_mention",
    "business_model_fit_score",
    "community_solar_score",
    "lmi_alignment_score",
    "capital_need_score",
    "stage_scale_score",
    "geographic_score",
    "strategic_alignment_score",
    "total_score",
    "priority_tier",
    "confidence_level",
    "needs_review",
    "priority_reason",
    "evidence_notes",
    "suggested_linkedin_angle",
    "suggested_target_titles",
]

REVIEW_CSV_COLS = SCORED_CSV_COLS + ["review_note"]


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# Calibration sample (first 25 rows)
# ─────────────────────────────────────────────

def run_calibration(all_rows: list[dict]) -> None:
    print("=== CALIBRATION: First 25 rows ===")
    sample = all_rows[:25]
    scored = [score_row(i + 1, r) for i, r in enumerate(sample)]
    scored.sort(key=lambda x: -x["total_score"])

    obvious_contractors = [r for r in scored if "roofing" in r["evidence_notes"].lower() or
                           "contractor" in r["evidence_notes"].lower() or
                           "residential-only" in r["evidence_notes"].lower()]
    developers = [r for r in scored if r["business_model_fit_score"] >= 15]

    print(f"  Total sample: {len(scored)}")
    print(f"  Contractor/residential signals: {len(obvious_contractors)}")
    print(f"  Strong developer signals: {len(developers)}")
    print(f"  Score range: {min(r['total_score'] for r in scored)}–{max(r['total_score'] for r in scored)}")
    print(f"  Avg contractor score: {sum(r['total_score'] for r in obvious_contractors) // max(1,len(obvious_contractors))}")
    print(f"  Avg developer score: {sum(r['total_score'] for r in developers) // max(1,len(developers))}")

    print("\n  Top 5 from sample:")
    for r in scored[:5]:
        print(f"    [{r['total_score']:3d}] {r['company_name'][:50]} | Tier {r['priority_tier']} | {r['priority_reason'][:60]}")
    print("\n  Bottom 5 from sample:")
    for r in scored[-5:]:
        print(f"    [{r['total_score']:3d}] {r['company_name'][:50]} | Tier {r['priority_tier']} | {r['priority_reason'][:60]}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main() -> None:
    print(f"Reading {INPUT_CSV}...")
    with open(INPUT_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    print(f"  Loaded {len(all_rows)} rows")

    # Calibration pass
    print()
    run_calibration(all_rows)

    # Full scoring
    print(f"\n=== FULL SCORING: {len(all_rows)} rows ===")
    scored = []
    for i, raw in enumerate(all_rows):
        result = score_row(i + 1, raw)
        scored.append(result)

    # Detect duplicate websites (same domain, different name entries)
    domain_seen: dict[str, int] = {}
    for r in scored:
        domain = r["website"].lower().strip().lstrip("www.").rstrip("/")
        if domain:
            if domain in domain_seen:
                # Mark both as needing review
                note = f"possible duplicate — same domain ({r['website']}) as row {domain_seen[domain]}"
                r["needs_review"] = True
                if r["review_note"]:
                    r["review_note"] += "; " + note
                else:
                    r["review_note"] = note
                # Find original and mark it too
                for orig in scored:
                    if orig["source_row_id"] == domain_seen[domain]:
                        orig["needs_review"] = True
                        dup_note = f"possible duplicate — same domain ({orig['website']}) as row {r['source_row_id']}"
                        if orig["review_note"]:
                            orig["review_note"] += "; " + dup_note
                        else:
                            orig["review_note"] = dup_note
                        break
            else:
                domain_seen[domain] = r["source_row_id"]

    # Sort by total_score descending
    scored.sort(key=lambda x: -x["total_score"])

    # Stats
    tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for r in scored:
        tier_counts[r["priority_tier"]] += 1
    print(f"  Tier distribution: {tier_counts}")
    print(f"  Score range: {min(r['total_score'] for r in scored)}–{max(r['total_score'] for r in scored)}")
    print(f"  Rows needing review: {sum(1 for r in scored if r['needs_review'])}")

    # Write developers_scored.csv
    out_scored = OUTPUT_DIR / "developers_scored.csv"
    write_csv(out_scored, scored, SCORED_CSV_COLS)
    print(f"  Wrote {out_scored}")

    # Write top_50_priority.csv (Tier A, then B, cap at 50)
    top_50 = [r for r in scored if r["priority_tier"] in ("A", "B")][:50]
    out_top = OUTPUT_DIR / "top_50_priority.csv"
    write_csv(out_top, top_50, SCORED_CSV_COLS)
    print(f"  Wrote {out_top} ({len(top_50)} rows)")

    # Write review_queue.csv
    review_q = [r for r in scored if r["needs_review"]]
    out_review = OUTPUT_DIR / "review_queue.csv"
    write_csv(out_review, review_q, REVIEW_CSV_COLS)
    print(f"  Wrote {out_review} ({len(review_q)} rows)")

    # Write developers_scored.json (full, for site)
    out_json = OUTPUT_DIR / "developers_scored.json"
    write_json(out_json, scored)
    print(f"  Wrote {out_json}")

    # Write site/data/developers_scored.json
    site_json = SITE_DATA_DIR / "developers_scored.json"
    write_json(site_json, scored)
    print(f"  Wrote {site_json}")

    print("\nDone.")


if __name__ == "__main__":
    main()
