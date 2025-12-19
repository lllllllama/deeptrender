"""
Simple venue discovery test - UTF-8 encoded
"""
import sys
sys.path.insert(0, 'src')

from scraper.venue_discovery import VenueDiscovery
from database import get_repository
import random

print("=" * 60)
print("Venue Discovery System Test")
print("=" * 60)

# Test 1: Discovery
print("\n[Test 1] Discovering venues from 2024...")
discovery = VenueDiscovery()
venues = discovery.discover_conferences(min_year=2024, max_year=2024)
print(f"Found {len(venues)} venue-years")

# Group by name
by_name = {}
for v in venues:
    if v.name not in by_name:
        by_name[v.name] = []
    by_name[v.name].append(v)

print(f"Unique venues: {len(by_name)}")

# Test 2: Random samples
print("\n[Test 2] Random sample venues:")
samples = random.sample(list(by_name.keys()), min(5, len(by_name)))
for name in samples:
    v = by_name[name][0]
    print(f"  {name}: {v.domain} (Tier {v.tier})")

# Test 3: Known venues classification
print("\n[Test 3] Known venue classification:")
known = ['ICLR', 'NeurIPS', 'ICML', 'ACL', 'EMNLP']
for name in known:
    if name in by_name:
        v = by_name[name][0]
        print(f"  {name}: domain={v.domain}, tier={v.tier}")

# Test 4: Database save
print("\n[Test 4] Saving to database...")
repo = get_repository()
saved = 0

for name in samples[:3]:
    venues_list = by_name[name]
    v = venues_list[0]
    years = [vv.year for vv in venues_list]
    ids = [vv.venue_id for vv in venues_list]
    
    repo.structured.save_discovered_venue(
        name=name,
        full_name=v.full_name,
        domain=v.domain,
        tier=v.tier,
        venue_type="conference",
        openreview_ids=ids,
        years=years
    )
    saved += 1
    print(f"  Saved: {name}")

print(f"Total saved: {saved}")

# Test 5: Database queries
print("\n[Test 5] Database queries:")
stats = repo.structured.get_venue_stats()
print(f"  Total venues in DB: {stats['total']}")
print(f"  By domain: {stats['by_domain']}")
print(f"  By tier: {stats['by_tier']}")

ml_venues = repo.structured.get_venues_by_domain('ML')
print(f"  ML venues: {len(ml_venues)}")

tier_a = repo.structured.get_venues_by_tier('A')
print(f"  Tier A venues: {len(tier_a)}")

print("\n" + "=" * 60)
print("All tests passed!")
print("=" * 60)
