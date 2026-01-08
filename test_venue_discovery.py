"""
会议发现系统集成测试

随机抽取会议进行全面测试：
1. 会议发现
2. 分类准确性
3. 数据库保存
4. API 查询
"""

import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.venue_discovery import VenueDiscovery
from database import get_repository


def test_discovery():
    """测试会议发现"""
    print("\n" + "=" * 60)
    print("测试 1: 会议发现")
    print("=" * 60)
    
    discovery = VenueDiscovery()
    venues = discovery.discover_conferences(min_year=2023)
    
    print(f"✓ 发现 {len(venues)} 个会议年份")
    
    # 按名称分组
    unique_venues = {}
    for v in venues:
        if v.name not in unique_venues:
            unique_venues[v.name] = []
        unique_venues[v.name].append(v)
    
    print(f"✓ 独立会议: {len(unique_venues)} 个")
    
    return venues, unique_venues


def test_random_samples(venues, unique_venues):
    """随机抽取会议测试"""
    print("\n" + "=" * 60)
    print("测试 2: 随机抽样验证")
    print("=" * 60)
    
    # 随机选择 5 个会议
    sample_names = random.sample(list(unique_venues.keys()), min(5, len(unique_venues)))
    
    for name in sample_names:
        venue_list = unique_venues[name]
        sample_venue = venue_list[0]
        
        print(f"\n会议: {name}")
        print(f"  全称: {sample_venue.full_name}")
        print(f"  领域: {sample_venue.domain}")
        print(f"  等级: {sample_venue.tier}")
        print(f"  类型: {'Workshop' if sample_venue.is_workshop else 'Conference'}")
        print(f"  年份: {[v.year for v in venue_list]}")
        print(f"  OpenReview IDs: {[v.venue_id for v in venue_list[:2]]}...")
        
        # 验证分类
        if sample_venue.tier not in ['A', 'B', 'C']:
            print(f"  ⚠️ 等级分类异常: {sample_venue.tier}")
        
        if not sample_venue.domain:
            print(f"  ⚠️ 领域未分类")
    
    return sample_names


def test_database_save(unique_venues, sample_names):
    """测试数据库保存"""
    print("\n" + "=" * 60)
    print("测试 3: 数据库保存")
    print("=" * 60)
    
    repo = get_repository()
    
    for name in sample_names:
        venue_list = unique_venues[name]
        venue_obj = venue_list[0]
        
        years = [v.year for v in venue_list]
        openreview_ids = [v.venue_id for v in venue_list]
        
        # 保存
        venue_id = repo.structured.save_discovered_venue(
            name=name,
            full_name=venue_obj.full_name,
            domain=venue_obj.domain,
            tier=venue_obj.tier,
            venue_type="workshop" if venue_obj.is_workshop else "conference",
            openreview_ids=openreview_ids,
            years=years
        )
        
        # 验证读取
        saved_venue = repo.structured.get_venue(venue_id)
        
        if saved_venue:
            print(f"✓ {name}: 保存并读取成功 (ID: {venue_id})")
            
            # 验证字段
            if saved_venue.canonical_name != name:
                print(f"  ⚠️ 名称不匹配")
            if getattr(saved_venue, 'tier', None) != venue_obj.tier:
                print(f"  ⚠️ 等级不匹配")
            
            saved_years = getattr(saved_venue, 'years_available', [])
            if sorted(saved_years) != sorted(years):
                print(f"  ⚠️ 年份不匹配: {saved_years} vs {years}")
        else:
            print(f"✗ {name}: 读取失败")
    
    # 测试统计
    stats = repo.structured.get_venue_stats()
    print(f"\n数据库统计:")
    print(f"  总计: {stats['total']} 个会议")
    print(f"  按领域: {stats['by_domain']}")
    print(f"  按等级: {stats['by_tier']}")


def test_api_queries(sample_names):
    """测试 API 查询"""
    print("\n" + "=" * 60)
    print("测试 4: 查询功能")
    print("=" * 60)
    
    repo = get_repository()
    
    # 测试按名称查询
    for name in sample_names[:2]:
        venue = repo.structured.get_venue_by_name(name)
        if venue:
            print(f"✓ 按名称查询 {name}: 成功")
        else:
            print(f"✗ 按名称查询 {name}: 失败")
    
    # 测试按领域查询
    test_domains = ['ML', 'NLP', 'CV']
    for domain in test_domains:
        venues = repo.structured.get_venues_by_domain(domain)
        print(f"✓ {domain} 领域: {len(venues)} 个会议")
    
    # 测试按等级查询
    for tier in ['A', 'B', 'C']:
        venues = repo.structured.get_venues_by_tier(tier)
        print(f"✓ {tier} 级: {len(venues)} 个会议")


def test_classification_accuracy(unique_venues):
    """测试分类准确性"""
    print("\n" + "=" * 60)
    print("测试 5: 分类准确性检查")
    print("=" * 60)
    
    # 检查已知顶会的分类
    known_venues = {
        'ICLR': {'expected_tier': 'A', 'expected_domain': 'ML'},
        'NeurIPS': {'expected_tier': 'A', 'expected_domain': 'ML'},
        'ACL': {'expected_tier': 'A', 'expected_domain': 'NLP'},
        'EMNLP': {'expected_tier': 'A', 'expected_domain': 'NLP'},
        'AISTATS': {'expected_tier': 'B', 'expected_domain': 'ML'},
        'CoRL': {'expected_tier': 'B', 'expected_domain': 'RL'},
    }
    
    correct_tier = 0
    correct_domain = 0
    total = 0
    
    for name, expected in known_venues.items():
        if name in unique_venues:
            venue = unique_venues[name][0]
            total += 1
            
            tier_match = venue.tier == expected['expected_tier']
            domain_match = expected['expected_domain'] in venue.domain or venue.domain in expected['expected_domain']
            
            if tier_match:
                correct_tier += 1
            if domain_match:
                correct_domain += 1
            
            status = "✓" if (tier_match and domain_match) else "⚠️"
            print(f"{status} {name}:")
            print(f"    等级: {venue.tier} (期望: {expected['expected_tier']}) {'✓' if tier_match else '✗'}")
            print(f"    领域: {venue.domain} (期望: {expected['expected_domain']}) {'✓' if domain_match else '✗'}")
    
    if total > 0:
        print(f"\n准确率:")
        print(f"  等级: {correct_tier}/{total} ({correct_tier/total*100:.1f}%)")
        print(f"  领域: {correct_domain}/{total} ({correct_domain/total*100:.1f}%)")


def main():
    print("=" * 60)
    print("会议发现系统集成测试")
    print("=" * 60)
    
    try:
        # 1. 发现会议
        venues, unique_venues = test_discovery()
        
        # 2. 随机抽样
        sample_names = test_random_samples(venues, unique_venues)
        
        # 3. 数据库保存
        test_database_save(unique_venues, sample_names)
        
        # 4. 查询功能
        test_api_queries(sample_names)
        
        # 5. 分类准确性
        test_classification_accuracy(unique_venues)
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
