"""探索 OpenReview venues"""
import sys
sys.path.insert(0, 'src')
from openreview.api import OpenReviewClient
from collections import Counter

client = OpenReviewClient(baseurl='https://api2.openreview.net')
groups = client.get_group('venues')
venues = groups.members or []

print(f"Total: {len(venues)}")

# 统计主会议
conferences = [v for v in venues if 'Conference' in v and 'Workshop' not in v]
print(f"Conferences: {len(conferences)}")

# 按年份
for year in [2024, 2023, 2022]:
    year_conf = [v for v in conferences if f'/{year}/' in v]
    print(f"\n{year}: {len(year_conf)} conferences")
    for v in sorted(year_conf)[:10]:
        print(f"  {v}")

# 知名会议
print("\n=== Known AI Venues ===")
known = ['ICLR', 'NeurIPS', 'ICML', 'EMNLP', 'AISTATS', 'CoRL', 'UAI', 'COLM', 'ACL', 'NAACL', 'COLT']
for name in known:
    for year in [2024, 2023]:
        matched = [v for v in conferences if name in v and f'/{year}/' in v]
        if matched:
            print(f"{name} {year}: {matched[0]}")
            break
