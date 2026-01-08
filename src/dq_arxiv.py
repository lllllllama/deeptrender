"""
arXiv 数据质量检查脚本

根据 agent.md 文档的 QA 检查清单验证数据质量。
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from database import get_repository


class ArxivDataQualityChecker:
    """arXiv 数据质量检查器"""

    def __init__(self):
        self.repo = get_repository()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "summary": {
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }

    def run_all_checks(self) -> Dict:
        """运行所有质量检查"""
        print("=" * 60)
        print("arXiv Data Quality Check")
        print("=" * 60)
        print()

        # Raw Layer 检查
        print("Raw Layer Checks")
        print("-" * 40)
        self._check_raw_completeness()
        self._check_raw_duplicates()
        self._check_raw_anomalies()
        print()

        # Analysis Layer 检查
        print("Analysis Layer Checks")
        print("-" * 40)
        self._check_analysis_cache()
        self._check_keyword_quality()
        print()

        # 生成报告
        self._generate_summary()

        return self.results

    def _check_raw_completeness(self):
        """检查 Raw 层数据完整性"""
        check_name = "raw_completeness"

        with self.repo._get_connection() as conn:
            cursor = conn.cursor()

            # 总数
            cursor.execute("SELECT COUNT(*) as total FROM raw_papers WHERE source = 'arxiv'")
            total = cursor.fetchone()["total"]

            # title 非空率
            cursor.execute("""
                SELECT COUNT(*) as count FROM raw_papers
                WHERE source = 'arxiv' AND (title IS NULL OR title = '')
            """)
            title_null = cursor.fetchone()["count"]
            title_rate = (total - title_null) / total * 100 if total > 0 else 0

            # abstract 非空率
            cursor.execute("""
                SELECT COUNT(*) as count FROM raw_papers
                WHERE source = 'arxiv' AND (abstract IS NULL OR abstract = '')
            """)
            abstract_null = cursor.fetchone()["count"]
            abstract_rate = (total - abstract_null) / total * 100 if total > 0 else 0

            # year 可解析率
            cursor.execute("""
                SELECT COUNT(*) as count FROM raw_papers
                WHERE source = 'arxiv' AND (year IS NULL OR year = 0)
            """)
            year_null = cursor.fetchone()["count"]
            year_rate = (total - year_null) / total * 100 if total > 0 else 0

            # retrieved_at 必填
            cursor.execute("""
                SELECT COUNT(*) as count FROM raw_papers
                WHERE source = 'arxiv' AND retrieved_at IS NULL
            """)
            retrieved_null = cursor.fetchone()["count"]
            retrieved_rate = (total - retrieved_null) / total * 100 if total > 0 else 0

        # 评估结果
        checks = {
            "title_non_null_rate": {
                "value": round(title_rate, 2),
                "threshold": 99.0,
                "passed": title_rate >= 99.0
            },
            "abstract_non_null_rate": {
                "value": round(abstract_rate, 2),
                "threshold": 95.0,
                "passed": abstract_rate >= 95.0
            },
            "year_parseable_rate": {
                "value": round(year_rate, 2),
                "threshold": 99.0,
                "passed": year_rate >= 99.0
            },
            "retrieved_at_filled": {
                "value": round(retrieved_rate, 2),
                "threshold": 100.0,
                "passed": retrieved_rate == 100.0
            }
        }

        self.results["checks"][check_name] = {
            "total_papers": total,
            "checks": checks
        }

        # 打印结果
        print(f"  Total papers: {total}")
        for key, check in checks.items():
            status = "[PASS]" if check["passed"] else "[FAIL]"
            print(f"  {status} {key}: {check['value']}% (threshold: {check['threshold']}%)")
            self._update_summary(check["passed"])

    def _check_raw_duplicates(self):
        """检查 Raw 层重复数据"""
        check_name = "raw_duplicates"

        with self.repo._get_connection() as conn:
            cursor = conn.cursor()

            # (source, source_paper_id) 重复
            cursor.execute("""
                SELECT source, source_paper_id, COUNT(*) as count
                FROM raw_papers
                WHERE source = 'arxiv'
                GROUP BY source, source_paper_id
                HAVING count > 1
            """)
            duplicates = cursor.fetchall()
            duplicate_count = len(duplicates)

            # title+abstract 哈希重复（简化版：只检查 title）
            cursor.execute("""
                SELECT title, COUNT(*) as count
                FROM raw_papers
                WHERE source = 'arxiv' AND title IS NOT NULL AND title != ''
                GROUP BY LOWER(title)
                HAVING count > 1
            """)
            title_duplicates = cursor.fetchall()
            title_dup_count = len(title_duplicates)

            cursor.execute("SELECT COUNT(*) as total FROM raw_papers WHERE source = 'arxiv'")
            total = cursor.fetchone()["total"]
            dup_rate = title_dup_count / total * 100 if total > 0 else 0

        checks = {
            "unique_constraint_violations": {
                "value": duplicate_count,
                "threshold": 0,
                "passed": duplicate_count == 0
            },
            "title_duplicate_rate": {
                "value": round(dup_rate, 2),
                "threshold": 3.0,
                "passed": dup_rate < 3.0
            }
        }

        self.results["checks"][check_name] = {
            "checks": checks,
            "duplicate_examples": [
                {"title": row["title"], "count": row["count"]}
                for row in title_duplicates[:5]
            ]
        }

        # 打印结果
        for key, check in checks.items():
            status = "[PASS]" if check["passed"] else "[FAIL]"
            print(f"  {status} {key}: {check['value']} (threshold: {check['threshold']})")
            self._update_summary(check["passed"])

    def _check_raw_anomalies(self):
        """检查 Raw 层异常数据"""
        check_name = "raw_anomalies"

        with self.repo._get_connection() as conn:
            cursor = conn.cursor()

            # 异常年份（< 1990 或 > 当前年份 + 1）
            current_year = datetime.now().year
            cursor.execute("""
                SELECT COUNT(*) as count FROM raw_papers
                WHERE source = 'arxiv' AND (year < 1990 OR year > ?)
            """, (current_year + 1,))
            anomaly_year = cursor.fetchone()["count"]

            # 异常标题长度（< 10 或 > 500）
            cursor.execute("""
                SELECT COUNT(*) as count FROM raw_papers
                WHERE source = 'arxiv' AND (LENGTH(title) < 10 OR LENGTH(title) > 500)
            """)
            anomaly_title = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as total FROM raw_papers WHERE source = 'arxiv'")
            total = cursor.fetchone()["total"]
            anomaly_rate = (anomaly_year + anomaly_title) / total * 100 if total > 0 else 0

        checks = {
            "anomaly_rate": {
                "value": round(anomaly_rate, 2),
                "threshold": 1.0,
                "passed": anomaly_rate < 1.0
            },
            "anomaly_year_count": {
                "value": anomaly_year,
                "info": True
            },
            "anomaly_title_count": {
                "value": anomaly_title,
                "info": True
            }
        }

        self.results["checks"][check_name] = {"checks": checks}

        # 打印结果
        for key, check in checks.items():
            if check.get("info"):
                print(f"  [INFO] {key}: {check['value']}")
            else:
                status = "[PASS]" if check["passed"] else "[WARN]"
                print(f"  {status} {key}: {check['value']}% (threshold: {check['threshold']}%)")
                if not check["passed"]:
                    self.results["summary"]["warnings"] += 1
                else:
                    self._update_summary(True)

    def _check_analysis_cache(self):
        """检查 Analysis 层缓存"""
        check_name = "analysis_cache"

        with self.repo._get_connection() as conn:
            cursor = conn.cursor()

            # 检查 analysis_arxiv_timeseries 表
            cursor.execute("SELECT COUNT(*) as count FROM analysis_arxiv_timeseries")
            timeseries_count = cursor.fetchone()["count"]

            # 检查 analysis_arxiv_emerging 表
            cursor.execute("SELECT COUNT(*) as count FROM analysis_arxiv_emerging")
            emerging_count = cursor.fetchone()["count"]

            # 检查 analysis_meta 表
            cursor.execute("SELECT COUNT(*) as count FROM analysis_meta WHERE key LIKE 'arxiv%'")
            meta_count = cursor.fetchone()["count"]

        checks = {
            "timeseries_cached": {
                "value": timeseries_count,
                "threshold": 1,
                "passed": timeseries_count > 0
            },
            "emerging_topics_cached": {
                "value": emerging_count,
                "info": True
            },
            "meta_entries": {
                "value": meta_count,
                "info": True
            }
        }

        self.results["checks"][check_name] = {"checks": checks}

        # 打印结果
        for key, check in checks.items():
            if check.get("info"):
                print(f"  [INFO] {key}: {check['value']}")
            else:
                status = "[PASS]" if check["passed"] else "[FAIL]"
                print(f"  {status} {key}: {check['value']} (threshold: > {check['threshold']})")
                self._update_summary(check["passed"])

    def _check_keyword_quality(self):
        """检查关键词质量"""
        check_name = "keyword_quality"

        with self.repo._get_connection() as conn:
            cursor = conn.cursor()

            # 从 analysis_arxiv_timeseries 中抽样检查关键词
            cursor.execute("""
                SELECT top_keywords_json FROM analysis_arxiv_timeseries
                WHERE top_keywords_json IS NOT NULL
                LIMIT 10
            """)

            import json
            import re

            total_keywords = 0
            invalid_keywords = 0

            for row in cursor.fetchall():
                keywords_json = row["top_keywords_json"]
                if keywords_json:
                    keywords = json.loads(keywords_json)
                    for kw_data in keywords:
                        keyword = kw_data.get("keyword", "")
                        total_keywords += 1

                        # 检查是否为纯数字
                        if re.match(r'^\d+$', keyword):
                            invalid_keywords += 1
                        # 检查是否太短
                        elif len(keyword) <= 2:
                            invalid_keywords += 1

            invalid_rate = invalid_keywords / total_keywords * 100 if total_keywords > 0 else 0

        checks = {
            "keyword_quality": {
                "value": round(100 - invalid_rate, 2),
                "threshold": 95.0,
                "passed": invalid_rate < 5.0
            },
            "total_sampled": {
                "value": total_keywords,
                "info": True
            },
            "invalid_count": {
                "value": invalid_keywords,
                "info": True
            }
        }

        self.results["checks"][check_name] = {"checks": checks}

        # 打印结果
        for key, check in checks.items():
            if check.get("info"):
                print(f"  [INFO] {key}: {check['value']}")
            else:
                status = "[PASS]" if check["passed"] else "[FAIL]"
                print(f"  {status} {key}: {check['value']}% (threshold: {check['threshold']}%)")
                self._update_summary(check["passed"])

    def _update_summary(self, passed: bool):
        """更新汇总统计"""
        self.results["summary"]["total_checks"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1

    def _generate_summary(self):
        """生成汇总报告"""
        summary = self.results["summary"]

        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Total checks: {summary['total_checks']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Warnings: {summary['warnings']}")

        pass_rate = summary['passed'] / summary['total_checks'] * 100 if summary['total_checks'] > 0 else 0
        print(f"  Pass rate: {pass_rate:.1f}%")

        if pass_rate >= 95:
            print("\n  [EXCELLENT] Data quality is excellent!")
        elif pass_rate >= 80:
            print("\n  [GOOD] Data quality is good")
        else:
            print("\n  [NEEDS IMPROVEMENT] Data quality needs improvement")

        print("=" * 60)

    def save_report(self, output_path: str = None):
        """保存报告到文件"""
        import json

        if not output_path:
            output_path = f"output/dq_arxiv_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\nReport saved: {output_path}")


def main():
    """主函数"""
    checker = ArxivDataQualityChecker()
    results = checker.run_all_checks()

    # 保存报告
    checker.save_report()

    # 返回退出码
    if results["summary"]["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
