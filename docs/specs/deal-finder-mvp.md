# Deal Finder MVP — Spec

> Auto-scan NS property listings, score for investment potential, deliver daily digest.
> Created: 2026-04-05

## Data Source

**Primary: Realtor.ca undocumented API**
- Endpoint: `POST https://api37.realtor.ca/Listing.svc/PropertySearch_Post`
- Returns JSON with full listing details
- Search by lat/long bounding box + filters (price, property type, etc.)
- Details: `GET https://api37.realtor.ca/Listing.svc/PropertyDetails?PropertyId={id}&ReferenceNumber={mls}`
- Reference: https://github.com/Froren/realtorca (npm wrapper documenting the API)
- No auth required, no API key — public endpoints backing realtor.ca frontend

**Why not ViewPoint.ca:**
- No API, heavy JS rendering, would need Playwright
- ToS likely prohibits scraping
- Same underlying MLS data as realtor.ca anyway (NSAR feed)

**Future supplement: PVSC assessments**
- Nova Scotia property assessments are public
- Can cross-reference listing price vs assessment value for gap analysis

## Architecture

```
deal_finder/
├── __init__.py
├── __main__.py          # CLI entry: python -m deal_finder
├── cli.py               # Click CLI commands
├── api.py               # Realtor.ca API client
├── scorer.py            # Investment scoring engine
├── config.py            # Config loading
├── models.py            # Data models (dataclasses)
└── utils.py             # Helpers (formatting, etc.)

config/
└── deal_finder.yaml     # Regions, weights, filters

results/                 # Scan output (gitignored)
└── YYYY-MM-DD.json

tests/
└── test_scorer.py       # Scorer unit tests
```

## Regions (Bounding Boxes)

Pre-configured NS regions:

| Region | Lat Min | Lat Max | Lon Min | Lon Max |
|--------|---------|---------|---------|---------|
| South Shore | 43.8 | 44.7 | -65.5 | -63.8 |
| Halifax | 44.5 | 44.8 | -63.7 | -63.4 |
| Lunenburg County | 44.1 | 44.6 | -64.7 | -64.1 |
| Chester/Mahone Bay | 44.3 | 44.6 | -64.4 | -64.0 |

## API Client (`api.py`)

### `search_listings(region, filters) -> list[Listing]`

POST to realtor.ca with:
```json
{
  "CultureId": 1,
  "ApplicationId": 37,
  "PropertySearchTypeId": 1,
  "LongitudeMin": -64.7,
  "LongitudeMax": -64.1,
  "LatitudeMin": 44.1,
  "LatitudeMax": 44.6,
  "PriceMin": 200000,
  "PriceMax": 600000,
  "TransactionTypeId": 2,
  "BuildingTypeId": 0,
  "RecordsPerPage": 50,
  "CurrentPage": 1
}
```

TransactionTypeId: 2 = For Sale
BuildingTypeId: 0 = All, 1 = House, 2 = Duplex, 3 = Triplex, etc.

Handle pagination (loop CurrentPage until no more results).

### `get_details(property_id, mls_number) -> ListingDetail`

GET details for deeper data (lot size, year built, full description).

## Data Model (`models.py`)

```python
@dataclass
class Listing:
    mls_number: str
    address: str
    city: str
    price: int
    property_type: str        # "Single Family", "Duplex", "Triplex", etc.
    bedrooms: int
    bathrooms: int
    lot_size_sqft: float | None
    lot_size_acres: float | None
    year_built: int | None
    days_on_market: int | None
    listing_url: str
    description: str          # Full listing description text
    assessment_value: int | None
    price_changes: list[dict] | None  # [{date, old_price, new_price}]
    latitude: float
    longitude: float
    raw: dict                 # Full API response for this listing
```

## Scoring Engine (`scorer.py`)

Each listing scored 0-100 based on weighted criteria:

### Criteria

| Criterion | Weight | How to Score |
|-----------|--------|-------------|
| Multi-unit potential | 25% | property_type == Duplex/Triplex/Fourplex → 80-100. "Legal non-conforming" or "2 unit" in description → 60. Single family → 20. |
| Rental income offset | 25% | Price-to-rent ratio estimate. Use regional avg rents (config). Lower ratio = higher score. |
| ADU/expansion potential | 15% | lot_size > 0.25 acres → 90. > 0.15 → 70. > 0.1 → 50. < 0.1 → 20. |
| Renovation/deal signals | 15% | Keywords in description: "estate", "as-is", "handyman", "potential", "investor", "needs work" → +20 each (cap 100). DOM > 60 → +30. Price reduction → +20. |
| STR potential | 10% | Proximity to tourist towns (Lunenburg, Chester, Mahone Bay, Peggy's Cove). Config list of tourist lat/longs, score by distance. |
| Value signals | 10% | Assessment gap: (assessment - price) / assessment. Positive gap (underpriced vs assessment) = higher score. |

### Output

```python
@dataclass
class ScoredListing:
    listing: Listing
    total_score: float          # 0-100
    scores: dict[str, float]    # per-criterion scores
    highlights: list[str]       # human-readable reasons
    tier: str                   # "A" (80+), "B" (60-79), "C" (40-59), "D" (<40)
```

## CLI Commands

```bash
# Scan a region
python -m deal_finder scan --region south-shore --max-price 600000 --min-price 200000

# Scan with property type filter
python -m deal_finder scan --region lunenburg --type duplex

# Score an existing results file
python -m deal_finder score results/2026-04-05.json

# Top 5 digest (one-liner per listing)
python -m deal_finder digest --top 5

# Full pipeline: scan + score + digest
python -m deal_finder run --region south-shore
```

## Config (`config/deal_finder.yaml`)

```yaml
regions:
  south-shore:
    lat_min: 43.8
    lat_max: 44.7
    lon_min: -65.5
    lon_max: -63.8
  halifax:
    lat_min: 44.5
    lat_max: 44.8
    lon_min: -63.7
    lon_max: -63.4
  lunenburg:
    lat_min: 44.1
    lat_max: 44.6
    lon_min: -64.7
    lon_max: -64.1

defaults:
  price_min: 200000
  price_max: 600000
  records_per_page: 50

scoring:
  weights:
    multi_unit: 0.25
    rental_income: 0.25
    adu_potential: 0.15
    deal_signals: 0.15
    str_potential: 0.10
    value_signals: 0.10
  
  rental_estimates:  # Monthly rent by bedrooms, South Shore NS
    1: 1200
    2: 1600
    3: 2000
    4: 2400
  
  tourist_towns:  # lat, lon for STR scoring
    - name: Lunenburg
      lat: 44.3725
      lon: -64.3168
    - name: Chester
      lat: 44.5419
      lon: -64.2383
    - name: Mahone Bay
      lat: 44.4494
      lon: -64.3831
    - name: Peggys Cove
      lat: 44.4917
      lon: -63.9181

api:
  base_url: https://api37.realtor.ca/Listing.svc
  culture_id: 1
  application_id: 37
  request_delay_seconds: 1.0  # Be polite
```

## MVP Scope (what to build now)

1. ✅ API client with search + pagination + details
2. ✅ Data models
3. ✅ Scoring engine with all 6 criteria
4. ✅ CLI with scan, score, digest, run commands
5. ✅ Config file
6. ✅ Scorer tests
7. ✅ requirements.txt
8. ✅ Save results to JSON

## NOT in MVP

- Daily cron / Telegram digest (V2)
- PVSC assessment cross-reference (V2)
- Price history tracking / new listing alerts (V2)
- Full evaluation trigger ("analyze this one") (V2)
- Map visualization (V2)

## Testing

```python
# test_scorer.py
def test_duplex_scores_high_multi_unit():
    listing = make_listing(property_type="Duplex")
    scores = score_listing(listing, config)
    assert scores.scores["multi_unit"] >= 80

def test_large_lot_scores_high_adu():
    listing = make_listing(lot_size_acres=0.3)
    scores = score_listing(listing, config)
    assert scores.scores["adu_potential"] >= 90

def test_estate_sale_keywords():
    listing = make_listing(description="Estate sale, sold as-is")
    scores = score_listing(listing, config)
    assert scores.scores["deal_signals"] >= 40

def test_underpriced_vs_assessment():
    listing = make_listing(price=300000, assessment_value=400000)
    scores = score_listing(listing, config)
    assert scores.scores["value_signals"] >= 80

def test_tier_assignment():
    # Score 85 = Tier A
    # Score 65 = Tier B
    # Score 45 = Tier C
    # Score 25 = Tier D
```

## Dependencies

```
requests>=2.31
click>=8.1
pyyaml>=6.0
```

## Risk

- Realtor.ca could change/block their API (unlikely for personal use, no aggressive rate)
- API response format could change (pin to known fields, handle missing gracefully)
- Rental estimates are rough (use conservative defaults, make configurable)
