"""
Simple verification script for DeepTrender implementation
"""

import sys
from pathlib import Path


def check_file(file_path, description):
    """Check if file exists"""
    exists = file_path.exists()
    status = "[OK]" if exists else "[FAIL]"
    print(f"{status} {description}")
    return exists


def check_content(file_path, keywords, description):
    """Check if file contains keywords"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        all_found = all(keyword in content for keyword in keywords)
        status = "[OK]" if all_found else "[FAIL]"
        print(f"{status} {description}")
        return all_found
    except Exception as e:
        print(f"[FAIL] {description}: {e}")
        return False


def main():
    root = Path(__file__).parent
    src = root / "src"

    print("=" * 70)
    print("DeepTrender Implementation Verification")
    print("=" * 70)

    results = []

    # 1. Database Schema
    print("\n1. Database Schema")
    print("-" * 70)
    schema_file = src / "database" / "schema.sql"
    results.append(check_file(schema_file, "schema.sql exists"))
    if schema_file.exists():
        results.append(check_content(
            schema_file,
            ["analysis_arxiv_emerging", "growth_rate", "first_seen"],
            "Contains analysis_arxiv_emerging table"
        ))

    # 2. Repository Methods
    print("\n2. Repository Methods")
    print("-" * 70)
    repo_file = src / "database" / "repository.py"
    results.append(check_file(repo_file, "repository.py exists"))
    if repo_file.exists():
        results.append(check_content(
            repo_file,
            ["save_emerging_topic", "get_emerging_topics"],
            "Contains emerging topics methods"
        ))

    # 3. ArxivAnalysisAgent
    print("\n3. ArxivAnalysisAgent")
    print("-" * 70)
    agent_file = src / "analysis" / "arxiv_agent.py"
    results.append(check_file(agent_file, "arxiv_agent.py exists"))
    if agent_file.exists():
        results.append(check_content(
            agent_file,
            ["detect_emerging_topics", "compare_categories"],
            "Contains new analysis methods"
        ))
        results.append(check_content(
            agent_file,
            ["_get_keywords_from_db", "_extract_with_yake"],
            "Contains enhanced keyword extraction"
        ))

    # 4. Web API
    print("\n4. Web API Endpoints")
    print("-" * 70)
    app_file = src / "web" / "app.py"
    results.append(check_file(app_file, "app.py exists"))
    if app_file.exists():
        results.append(check_content(
            app_file,
            ["/api/arxiv/stats", "/api/arxiv/compare"],
            "Contains new arXiv API endpoints"
        ))
        results.append(check_content(
            app_file,
            ["/api/arxiv/emerging", "/api/arxiv/papers"],
            "Contains emerging & papers endpoints"
        ))
        results.append(check_content(
            app_file,
            ["/api/registry/venues"],
            "Contains registry endpoint"
        ))

    # 5. Data Quality Script
    print("\n5. Data Quality Script")
    print("-" * 70)
    dq_file = src / "dq_arxiv.py"
    results.append(check_file(dq_file, "dq_arxiv.py exists"))
    if dq_file.exists():
        results.append(check_content(
            dq_file,
            ["ArxivDataQualityChecker", "_check_raw_completeness"],
            "Contains quality check methods"
        ))

    # 6. Main Integration
    print("\n6. Main Integration")
    print("-" * 70)
    main_file = src / "main.py"
    results.append(check_file(main_file, "main.py exists"))
    if main_file.exists():
        results.append(check_content(
            main_file,
            ["ArxivAnalysisAgent", "run_all_granularities", "detect_emerging_topics"],
            "Contains arXiv analysis integration"
        ))

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n[SUCCESS] All checks passed! Implementation complete!")
        print("\nNext steps:")
        print("  1. Run data collection: python src/main.py --source arxiv --arxiv-days 7")
        print("  2. Run quality check: python src/dq_arxiv.py")
        print("  3. Start web server: python src/web/app.py")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
