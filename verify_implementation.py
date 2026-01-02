"""
验证 DeepTrender 实施完成情况

不导入模块，只检查文件和代码结构
"""

import sys
from pathlib import Path


def check_file_exists(file_path: Path, description: str) -> bool:
    """检查文件是否存在"""
    exists = file_path.exists()
    status = "✓" if exists else "✗"
    print(f"  [{status}] {description}: {file_path.name}")
    return exists


def check_code_contains(file_path: Path, keywords: list, description: str) -> bool:
    """检查代码是否包含关键字"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        all_found = all(keyword in content for keyword in keywords)
        status = "✓" if all_found else "✗"
        print(f"  [{status}] {description}")

        if not all_found:
            missing = [k for k in keywords if k not in content]
            print(f"      缺失: {', '.join(missing)}")

        return all_found
    except Exception as e:
        print(f"  [✗] {description}: 读取失败 ({e})")
        return False


def main():
    root = Path(__file__).parent
    src = root / "src"

    print("=" * 70)
    print("DeepTrender 实施验证")
    print("=" * 70)

    results = {}

    # 1. 数据库 Schema
    print("\n1. 数据库 Schema")
    print("-" * 70)
    schema_file = src / "database" / "schema.sql"
    results["schema_file"] = check_file_exists(schema_file, "schema.sql 文件")
    if schema_file.exists():
        results["schema_emerging"] = check_code_contains(
            schema_file,
            ["analysis_arxiv_emerging", "growth_rate", "first_seen", "trend"],
            "包含 analysis_arxiv_emerging 表定义"
        )

    # 2. Repository 方法
    print("\n2. Repository 新方法")
    print("-" * 70)
    repo_file = src / "database" / "repository.py"
    results["repo_file"] = check_file_exists(repo_file, "repository.py 文件")
    if repo_file.exists():
        results["repo_emerging"] = check_code_contains(
            repo_file,
            ["save_emerging_topic", "save_emerging_topics_batch", "get_emerging_topics"],
            "包含新兴主题相关方法"
        )

    # 3. ArxivAnalysisAgent
    print("\n3. ArxivAnalysisAgent 增强")
    print("-" * 70)
    agent_file = src / "analysis" / "arxiv_agent.py"
    results["agent_file"] = check_file_exists(agent_file, "arxiv_agent.py 文件")
    if agent_file.exists():
        results["agent_detect"] = check_code_contains(
            agent_file,
            ["detect_emerging_topics", "growth_rate", "threshold"],
            "包含 detect_emerging_topics 方法"
        )
        results["agent_compare"] = check_code_contains(
            agent_file,
            ["compare_categories", "overlap", "unique"],
            "包含 compare_categories 方法"
        )
        results["agent_keywords"] = check_code_contains(
            agent_file,
            ["_get_keywords_from_db", "_extract_with_yake", "_extract_with_frequency"],
            "包含增强的关键词提取方法"
        )

    # 4. Web API
    print("\n4. Web API Endpoints")
    print("-" * 70)
    app_file = src / "web" / "app.py"
    results["app_file"] = check_file_exists(app_file, "app.py 文件")
    if app_file.exists():
        results["api_stats"] = check_code_contains(
            app_file,
            ["/api/arxiv/stats", "total_papers", "categories_stats"],
            "包含 /api/arxiv/stats endpoint"
        )
        results["api_compare"] = check_code_contains(
            app_file,
            ["/api/arxiv/compare", "ArxivAnalysisAgent", "compare_categories"],
            "包含 /api/arxiv/compare endpoint"
        )
        results["api_emerging"] = check_code_contains(
            app_file,
            ["/api/arxiv/emerging", "get_emerging_topics"],
            "包含 /api/arxiv/emerging endpoint"
        )
        results["api_papers"] = check_code_contains(
            app_file,
            ["/api/arxiv/papers", "limit", "offset"],
            "包含 /api/arxiv/papers endpoint"
        )
        results["api_paper_detail"] = check_code_contains(
            app_file,
            ["/api/arxiv/paper/<arxiv_id>", "pdf_url", "abs_url"],
            "包含 /api/arxiv/paper/<arxiv_id> endpoint"
        )
        results["api_registry"] = check_code_contains(
            app_file,
            ["/api/registry/venues", "VENUES", "venue_config"],
            "包含 /api/registry/venues endpoint"
        )

    # 5. 数据质量检查
    print("\n5. 数据质量检查脚本")
    print("-" * 70)
    dq_file = src / "dq_arxiv.py"
    results["dq_file"] = check_file_exists(dq_file, "dq_arxiv.py 文件")
    if dq_file.exists():
        results["dq_checks"] = check_code_contains(
            dq_file,
            ["ArxivDataQualityChecker", "_check_raw_completeness",
             "_check_raw_duplicates", "_check_analysis_cache", "_check_keyword_quality"],
            "包含完整的质量检查方法"
        )

    # 6. main.py 集成
    print("\n6. main.py 集成")
    print("-" * 70)
    main_file = src / "main.py"
    results["main_file"] = check_file_exists(main_file, "main.py 文件")
    if main_file.exists():
        results["main_arxiv"] = check_code_contains(
            main_file,
            ["ArxivAnalysisAgent", "run_all_granularities", "detect_emerging_topics"],
            "包含 arXiv 分析集成"
        )

    # 汇总结果
    print("\n" + "=" * 70)
    print("验证汇总")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    categories = {
        "数据库": ["schema_file", "schema_emerging"],
        "Repository": ["repo_file", "repo_emerging"],
        "ArxivAgent": ["agent_file", "agent_detect", "agent_compare", "agent_keywords"],
        "Web API": ["app_file", "api_stats", "api_compare", "api_emerging",
                    "api_papers", "api_paper_detail", "api_registry"],
        "数据质量": ["dq_file", "dq_checks"],
        "主程序": ["main_file", "main_arxiv"]
    }

    for category, keys in categories.items():
        cat_passed = sum(1 for k in keys if results.get(k, False))
        cat_total = len(keys)
        status = "✓" if cat_passed == cat_total else "✗"
        print(f"  [{status}] {category}: {cat_passed}/{cat_total}")

    print(f"\n总体通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n✓ 所有检查通过！实施完成！")
        print("\n下一步:")
        print("  1. 运行数据采集: python src/main.py --source arxiv --arxiv-days 7")
        print("  2. 运行数据质量检查: python src/dq_arxiv.py")
        print("  3. 启动 Web 服务: python src/web/app.py")
        return 0
    else:
        print(f"\n✗ {total - passed} 个检查失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
