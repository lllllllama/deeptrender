"""
测试 DeepTrender 实施的所有功能

验证：
1. 数据库 schema 完整性
2. ArxivAnalysisAgent 功能
3. Repository 新方法
4. API endpoints
"""

import sys
import io
from pathlib import Path

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_database_schema():
    """测试数据库 schema"""
    print("\n" + "=" * 60)
    print("🗄️  测试 1: 数据库 Schema")
    print("=" * 60)

    from database import get_repository

    repo = get_repository()

    # 检查表是否存在
    with repo._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row["name"] for row in cursor.fetchall()]

    required_tables = [
        "raw_papers",
        "papers",
        "venues",
        "paper_sources",
        "paper_keywords",
        "analysis_meta",
        "analysis_venue_summary",
        "analysis_keyword_trends",
        "analysis_arxiv_timeseries",
        "analysis_arxiv_emerging"  # 新增表
    ]

    print("\n检查必需的表:")
    all_present = True
    for table in required_tables:
        present = table in tables
        status = "✅" if present else "❌"
        print(f"  {status} {table}")
        if not present:
            all_present = False

    if all_present:
        print("\n✅ 所有必需的表都存在")
        return True
    else:
        print("\n❌ 缺少某些表")
        return False


def test_repository_methods():
    """测试 Repository 新方法"""
    print("\n" + "=" * 60)
    print("📦 测试 2: Repository 新方法")
    print("=" * 60)

    from database import get_repository

    repo = get_repository()

    # 测试新增的方法
    methods_to_test = [
        ("analysis.save_emerging_topic", "保存新兴主题"),
        ("analysis.save_emerging_topics_batch", "批量保存新兴主题"),
        ("analysis.get_emerging_topics", "获取新兴主题"),
        ("analysis.save_arxiv_timeseries", "保存 arXiv 时间序列"),
        ("analysis.get_arxiv_timeseries", "获取 arXiv 时间序列"),
    ]

    print("\n检查方法是否存在:")
    all_present = True
    for method_path, description in methods_to_test:
        parts = method_path.split(".")
        obj = repo
        try:
            for part in parts:
                obj = getattr(obj, part)
            print(f"  ✅ {description} ({method_path})")
        except AttributeError:
            print(f"  ❌ {description} ({method_path})")
            all_present = False

    if all_present:
        print("\n✅ 所有方法都存在")
        return True
    else:
        print("\n❌ 缺少某些方法")
        return False


def test_arxiv_agent():
    """测试 ArxivAnalysisAgent"""
    print("\n" + "=" * 60)
    print("🤖 测试 3: ArxivAnalysisAgent")
    print("=" * 60)

    try:
        from analysis.arxiv_agent import ArxivAnalysisAgent

        agent = ArxivAnalysisAgent()

        # 检查方法
        methods = [
            ("run", "运行分析"),
            ("run_all_granularities", "运行所有粒度"),
            ("detect_emerging_topics", "识别新兴主题"),
            ("compare_categories", "对比分类"),
            ("_extract_bucket_keywords", "提取关键词"),
            ("_get_keywords_from_db", "从数据库获取关键词"),
            ("_extract_with_yake", "使用 YAKE 提取"),
            ("_extract_with_frequency", "使用词频提取"),
        ]

        print("\n检查 ArxivAnalysisAgent 方法:")
        all_present = True
        for method_name, description in methods:
            if hasattr(agent, method_name):
                print(f"  ✅ {description} ({method_name})")
            else:
                print(f"  ❌ {description} ({method_name})")
                all_present = False

        if all_present:
            print("\n✅ ArxivAnalysisAgent 所有方法都存在")
            return True
        else:
            print("\n❌ ArxivAnalysisAgent 缺少某些方法")
            return False

    except Exception as e:
        print(f"\n❌ 导入 ArxivAnalysisAgent 失败: {e}")
        return False


def test_api_endpoints():
    """测试 API endpoints"""
    print("\n" + "=" * 60)
    print("🌐 测试 4: API Endpoints")
    print("=" * 60)

    try:
        from web.app import create_app

        app = create_app()

        # 检查新增的 API endpoints
        new_endpoints = [
            "/api/arxiv/stats",
            "/api/arxiv/compare",
            "/api/arxiv/emerging",
            "/api/arxiv/papers",
            "/api/arxiv/paper/<arxiv_id>",
            "/api/registry/venues",
        ]

        # 获取所有路由
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(str(rule))

        print("\n检查新增的 API endpoints:")
        all_present = True
        for endpoint in new_endpoints:
            # 简化匹配（忽略参数）
            base_endpoint = endpoint.split("<")[0].rstrip("/")
            found = any(base_endpoint in route for route in routes)
            status = "✅" if found else "❌"
            print(f"  {status} {endpoint}")
            if not found:
                all_present = False

        if all_present:
            print("\n✅ 所有 API endpoints 都存在")
            return True
        else:
            print("\n❌ 缺少某些 API endpoints")
            return False

    except Exception as e:
        print(f"\n❌ 创建 Flask app 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_quality_script():
    """测试数据质量检查脚本"""
    print("\n" + "=" * 60)
    print("📊 测试 5: 数据质量检查脚本")
    print("=" * 60)

    try:
        from dq_arxiv import ArxivDataQualityChecker

        checker = ArxivDataQualityChecker()

        # 检查方法
        methods = [
            "run_all_checks",
            "_check_raw_completeness",
            "_check_raw_duplicates",
            "_check_raw_anomalies",
            "_check_analysis_cache",
            "_check_keyword_quality",
        ]

        print("\n检查数据质量检查器方法:")
        all_present = True
        for method_name in methods:
            if hasattr(checker, method_name):
                print(f"  ✅ {method_name}")
            else:
                print(f"  ❌ {method_name}")
                all_present = False

        if all_present:
            print("\n✅ 数据质量检查脚本完整")
            return True
        else:
            print("\n❌ 数据质量检查脚本不完整")
            return False

    except Exception as e:
        print(f"\n❌ 导入数据质量检查脚本失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_main_integration():
    """测试 main.py 集成"""
    print("\n" + "=" * 60)
    print("🔧 测试 6: main.py 集成")
    print("=" * 60)

    try:
        # 读取 main.py 内容
        main_path = Path(__file__).parent / "src" / "main.py"
        with open(main_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查Xiv 分析相关代码
        checks = [
            ("ArxivAnalysisAgent", "导入 ArxivAnalysisAgent"),
            ("arxiv_agent = ArxivAnalysisAgent()", "创建 ArxivAnalysisAgent 实例"),
            ("run_all_granularities", "运行所有粒度分析"),
            ("detect_emerging_topics", "识别新兴主题"),
        ]

        print("\n检查 main.py 集成:")
        all_present = True
        for keyword, description in checks:
            if keyword in content:
                print(f"  ✅ {description}")
            else:
                print(f"  ❌ {description}")
                all_present = False

        if all_present:
            print("\n✅ main.py 已正确集成 arXiv 分析")
            return True
        else:
            print("\n❌ main.py 集成不完整")
            return False

    except Exception as e:
        print(f"\n❌ 读取 main.py 失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🚀 DeepTrender 实施验证测试")
    print("=" * 60)

    results = {
        "数据库 Schema": test_database_schema(),
        "Repository 方法": test_repository_methods(),
        "ArxivAnalysisAgent": test_arxiv_agent(),
        "API Endpoints": test_api_endpoints(),
        "数据质量检查": test_data_quality_script(),
        "main.py 集成": test_main_integration(),
    }

    # 汇总结果
    print("\n" + "=" * 60)
    print("📋 测试汇总")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")

    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！实施完成！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
