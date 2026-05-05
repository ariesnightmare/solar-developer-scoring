"""
Web Enrichment Script
======================
Visits the top N companies by current score, fetches their public websites,
and extracts additional signals that weren't in the LinkedIn descriptions.

Saves progress incrementally — safe to interrupt and resume.
Run time: ~5-10 seconds per company (polite rate limiting).

Usage:
    python3 scripts/enrich.py            # enriches top 100
    python3 scripts/enrich.py --top 50   # enriches top 50
    python3 scripts/enrich.py --resume   # skips already-enriched companies
"""

import json
import re
import sys
import time
import argparse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

ROOT        = Path(__file__).parent.parent
SCORED_JSON = ROOT / "output" / "developers_scored.json"
ENRICHED_JSON = ROOT / "output" / "enriched_signals.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

FETCH_TIMEOUT  = 12   # seconds per request
RATE_LIMIT     = 4    # seconds between companies
PAGE_PATHS     = [
    "",                   # homepage
    "/about",
    "/about-us",
    "/our-story",
    "/who-we-are",
    "/projects",
    "/our-projects",
    "/portfolio",
    "/our-work",
    "/what-we-do",
    "/team",
    "/leadership",
    "/our-team",
    "/impact",
    "/news",
    "/press",
]
MAX_PAGES_PER_SITE = 5   # stop after finding this many pages with content
MAX_TEXT_CHARS     = 15000  # cap text per site to avoid huge pages


# ─────────────────────────────────────────────
# HTML text extractor
# ─────────────────────────────────────────────

class TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "head", "meta", "link"}

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip == 0:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self):
        return " ".join(self.text_parts)


def extract_text(html_bytes: bytes) -> str:
    try:
        html = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""
    parser = TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.get_text()


# ─────────────────────────────────────────────
# Fetch helpers
# ─────────────────────────────────────────────

def normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    if not domain:
        return ""
    if not domain.startswith("http"):
        domain = "https://" + domain
    # strip trailing slash and path
    parsed = urlparse(domain)
    return f"{parsed.scheme}://{parsed.netloc}"


def fetch_page(url: str) -> str:
    """Fetch a single page and return its text. Returns '' on any error."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            if resp.status != 200:
                return ""
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/" not in content_type:
                return ""
            raw = resp.read(200_000)  # max 200KB per page
            return extract_text(raw)
    except (URLError, HTTPError, OSError, TimeoutError):
        return ""
    except Exception:
        return ""


def fetch_site(base_url: str) -> str:
    """Fetch multiple pages from a site and return combined text."""
    all_text = []
    pages_fetched = 0

    for path in PAGE_PATHS:
        if pages_fetched >= MAX_PAGES_PER_SITE:
            break
        url = base_url.rstrip("/") + path
        text = fetch_page(url)
        if len(text) > 100:  # only count pages with real content
            all_text.append(text)
            pages_fetched += 1
        time.sleep(0.5)  # small delay between pages on same site

    combined = " ".join(all_text)
    return combined[:MAX_TEXT_CHARS]


# ─────────────────────────────────────────────
# Enrichment signal patterns
# ─────────────────────────────────────────────

# MW / GW numbers (project scale evidence)
P_MW = re.compile(r"(\d[\d,]*\.?\d*)\s*(MW|megawatt|GW|gigawatt)", re.I)

# Named government programs
P_GOV_PROGRAMS = re.compile(
    r"\b(inflation reduction act|ira |doe loan|doe grant|usda reap|reap grant|"
    r"hud |liheap|low income home energy|department of energy|"
    r"community development financial|cdfi|new market tax credit|nmtc|"
    r"opportunity zone|justice40|j40|clean energy fund|green bank|"
    r"state energy office|public utility commission|puc )\b",
    re.I,
)

# Named utility partners
P_UTILITY = re.compile(
    r"\b(eversource|national grid|con edison|duke energy|dominion|"
    r"xcel energy|pge|pg&e|pacific gas|southern company|nextera|"
    r"enel|avangrid|ameren|entergy|exelon|pseg|dte energy|"
    r"green mountain power|green mountain|efficiency vermont|"
    r"rocky mountain power|puget sound|seattle city light|"
    r"los angeles dwr|ladwp|sacramento muni|smud)\b",
    re.I,
)

# Press / media mentions on the site itself
P_PRESS = re.compile(
    r"\b(featured in|as seen in|covered by|press release|in the news|"
    r"media coverage|bloomberg|reuters|associated press|new york times|"
    r"wall street journal|washington post|forbes|fortune|"
    r"greentech media|pv magazine|canary media|utility dive|"
    r"solar power world|renewable energy world|e&e news|"
    r"podcast|webinar|panel|keynote|speaker|conference|"
    r"seia|solar united|irec|vote solar|clean energy states)\b",
    re.I,
)

# Specific community solar program names
P_CS_PROGRAMS = re.compile(
    r"\b(community solar|shared solar|solar garden|virtual net meter|"
    r"community distributed generation|cdg|"
    r"low.income solar|solar for all|affordable solar|"
    r"community choice|cca |community choice aggregation)\b",
    re.I,
)

# Project finance / capital signals
P_FINANCE_DEEP = re.compile(
    r"\b(tax equity|project finance|debt financ|construction loan|"
    r"bridge financ|mezzanine|preferred equity|yieldco|"
    r"power purchase agreement|ppa|offtake|"
    r"institutional investor|asset manag|fund manag|"
    r"raise capital|series [abc]|seed round|growth equity)\b",
    re.I,
)

# Named team / leadership signals (indicators of visible people)
P_LEADERSHIP = re.compile(
    r"\b(our team|our leadership|meet the team|founders?|co.founder|"
    r"chief executive|chief financial|chief operating|"
    r"vp of development|director of|head of|managing director|"
    r"years? of experience|background in|previously at|formerly)\b",
    re.I,
)

# Awards and recognition
P_AWARDS = re.compile(
    r"\b(award.winning|award winner|recognized by|named (?:a |one of|among)|"
    r"best of|top \d+|inc \d+|fast company|b corp|certified b|"
    r"accredited|certified|iso \d+)\b",
    re.I,
)

# States served (multi-state is a scale signal)
P_STATES = re.compile(
    r"\b(Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|"
    r"Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|"
    r"Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|"
    r"Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|"
    r"New Hampshire|New Jersey|New Mexico|New York|North Carolina|"
    r"North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|"
    r"South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|"
    r"Virginia|Washington|West Virginia|Wisconsin|Wyoming)\b",
    re.I,
)


def extract_signals(text: str) -> dict:
    """Extract enrichment signals from fetched website text."""
    if not text:
        return {"fetch_success": False}

    # MW totals
    mw_matches = P_MW.findall(text)
    total_mw = 0
    for num_str, unit in mw_matches:
        try:
            val = float(num_str.replace(",", ""))
            if "GW" in unit.upper():
                val *= 1000
            total_mw += val
        except ValueError:
            pass

    # State mentions (unique)
    states_found = list(set(m.group(0).title() for m in re.finditer(P_STATES, text)))

    return {
        "fetch_success": True,
        "text_length": len(text),
        "mw_mentioned": round(total_mw, 1),
        "mw_raw_mentions": len(mw_matches),
        "states_mentioned": states_found[:20],  # cap at 20
        "states_count": len(states_found),
        "gov_program_signals": len(P_GOV_PROGRAMS.findall(text)),
        "utility_partner_signals": len(P_UTILITY.findall(text)),
        "press_media_signals": len(P_PRESS.findall(text)),
        "community_solar_signals": len(P_CS_PROGRAMS.findall(text)),
        "finance_signals": len(P_FINANCE_DEEP.findall(text)),
        "leadership_signals": len(P_LEADERSHIP.findall(text)),
        "award_signals": len(P_AWARDS.findall(text)),
    }


def compute_enrichment_bonus(signals: dict) -> tuple[int, list[str]]:
    """Convert signals into a bonus score (0-20) and reason notes."""
    if not signals.get("fetch_success"):
        return 0, ["website not reachable"]

    bonus = 0
    notes = []

    # MW scale evidence
    mw = signals.get("mw_mentioned", 0)
    if mw >= 100:
        bonus += 5
        notes.append(f"large MW footprint ({mw:.0f}+ MW mentioned)")
    elif mw >= 10:
        bonus += 3
        notes.append(f"meaningful MW scale ({mw:.0f} MW mentioned)")
    elif mw > 0:
        bonus += 1
        notes.append(f"some MW scale ({mw:.0f} MW mentioned)")

    # Multi-state presence
    states = signals.get("states_count", 0)
    if states >= 8:
        bonus += 4
        notes.append(f"multi-state presence ({states} states)")
    elif states >= 4:
        bonus += 2
        notes.append(f"regional presence ({states} states)")
    elif states >= 2:
        bonus += 1
        notes.append(f"multi-state hints ({states} states)")

    # Government programs
    gov = signals.get("gov_program_signals", 0)
    if gov >= 2:
        bonus += 4
        notes.append("multiple government program references")
    elif gov == 1:
        bonus += 2
        notes.append("government program reference")

    # Utility partners
    util = signals.get("utility_partner_signals", 0)
    if util >= 2:
        bonus += 3
        notes.append("named utility partnerships")
    elif util == 1:
        bonus += 1
        notes.append("utility partner mentioned")

    # Press / media / industry
    press = signals.get("press_media_signals", 0)
    if press >= 3:
        bonus += 3
        notes.append("strong press/media/industry presence")
    elif press >= 1:
        bonus += 1
        notes.append("some press or industry mentions")

    # Community solar programs on site
    cs = signals.get("community_solar_signals", 0)
    if cs >= 3:
        bonus += 3
        notes.append("community solar programs prominently featured")
    elif cs >= 1:
        bonus += 1
        notes.append("community solar mentioned on site")

    # Finance signals
    fin = signals.get("finance_signals", 0)
    if fin >= 2:
        bonus += 2
        notes.append("project finance language on site")
    elif fin == 1:
        bonus += 1
        notes.append("financing language on site")

    # Awards
    if signals.get("award_signals", 0) >= 1:
        bonus += 1
        notes.append("awards or recognition mentioned")

    if not notes:
        notes.append("site reachable but no strong signals found")

    return min(20, bonus), notes


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=100, help="How many companies to enrich")
    parser.add_argument("--resume", action="store_true", help="Skip already-enriched companies")
    args = parser.parse_args()

    # Load scored data
    print(f"Loading {SCORED_JSON}...")
    with open(SCORED_JSON, "r") as f:
        all_companies = json.load(f)

    # Take top N by total_score
    target = all_companies[:args.top]
    print(f"Targeting top {len(target)} companies by score.")

    # Load existing enrichment if resuming
    existing: dict[str, dict] = {}
    if ENRICHED_JSON.exists():
        with open(ENRICHED_JSON, "r") as f:
            existing = json.load(f)
        print(f"Found {len(existing)} previously enriched companies.")

    results = dict(existing)
    to_process = [c for c in target if c["company_name"] not in results] if args.resume else target

    print(f"Companies to process: {len(to_process)}")
    print(f"Estimated time: {len(to_process) * (RATE_LIMIT + 3) // 60}–{len(to_process) * (RATE_LIMIT + 8) // 60} minutes")
    print()

    for i, company in enumerate(to_process):
        name    = company["company_name"]
        domain  = company.get("website", "")
        score   = company["total_score"]
        base_url = normalize_domain(domain)

        print(f"[{i+1:3d}/{len(to_process)}] {name[:50]:<50} score={score}", end=" ", flush=True)

        if not base_url:
            print("— no website, skipping")
            results[name] = {"fetch_success": False, "reason": "no website"}
            continue

        print(f"→ {base_url}", end=" ", flush=True)
        text = fetch_site(base_url)
        signals = extract_signals(text)
        bonus, notes = compute_enrichment_bonus(signals)
        signals["enrichment_bonus"] = bonus
        signals["enrichment_notes"] = notes
        signals["base_url"] = base_url

        results[name] = signals

        status = f"✓ bonus=+{bonus}" if signals["fetch_success"] else "✗ unreachable"
        print(f"| {status} | {', '.join(notes[:2])}")

        # Save progress after every company
        with open(ENRICHED_JSON, "w") as f:
            json.dump(results, f, indent=2)

        # Rate limit between companies
        if i < len(to_process) - 1:
            time.sleep(RATE_LIMIT)

    print(f"\nDone. Enriched {len(results)} companies total.")
    print(f"Results saved to {ENRICHED_JSON}")
    print()
    print("Next step: run  python3 scripts/apply_enrichment.py  to update scores.")


if __name__ == "__main__":
    main()
