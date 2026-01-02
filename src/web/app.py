"""
Flask 应用入口

提供 REST API 和静态文件服务。
"""

import sys
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_repository
from analysis import get_analyzer


def create_app():
    """创建 Flask 应用"""
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static"
    )
    CORS(app)
    
    # 获取组件
    repo = get_repository()
    analyzer = get_analyzer()
    
    # ==================== 页面路由 ====================
    
    @app.route("/")
    def index():
        """首页"""
        return send_from_directory(app.static_folder, "index.html")
    
    @app.route("/<path:filename>")
    def serve_static(filename):
        """静态文件"""
        return send_from_directory(app.static_folder, filename)
    
    # ==================== API 路由 ====================
    
    @app.route("/api/stats/overview")
    def api_overview():
        """总览统计"""
        venues = repo.get_all_venues()
        years = repo.get_all_years()
        
        return jsonify({
            "total_papers": repo.get_paper_count(),
            "total_keywords": len(repo.get_top_keywords(limit=100000)),
            "total_venues": len(venues),
            "venues": venues,
            "years": years,
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
        })
    
    @app.route("/api/stats/venues")
    def api_venues():
        """各会议统计"""
        venues = repo.get_all_venues()
        result = []
        
        for venue in venues:
            years = repo.get_all_years(venue)
            paper_count = repo.get_paper_count(venue=venue)
            result.append({
                "name": venue,
                "paper_count": paper_count,
                "years": years,
            })
        
        return jsonify(result)
    
    @app.route("/api/stats/venue/<venue>")
    def api_venue_detail(venue):
        """单会议详情"""
        years = repo.get_all_years(venue)
        yearly_stats = []
        
        for year in sorted(years, reverse=True):
            count = repo.get_paper_count(venue=venue, year=year)
            top_kw = repo.get_top_keywords(venue=venue, year=year, limit=10)
            yearly_stats.append({
                "year": year,
                "paper_count": count,
                "top_keywords": [{"keyword": kw, "count": c} for kw, c in top_kw],
            })
        
        return jsonify({
            "venue": venue,
            "total_papers": repo.get_paper_count(venue=venue),
            "years": years,
            "yearly_stats": yearly_stats,
        })
    
    @app.route("/api/keywords/top")
    def api_top_keywords():
        """Top-K 关键词"""
        venue = request.args.get("venue")
        year = request.args.get("year", type=int)
        limit = request.args.get("limit", 50, type=int)
        
        keywords = repo.get_top_keywords(
            venue=venue,
            year=year,
            limit=limit,
        )
        
        return jsonify([
            {"keyword": kw, "count": count}
            for kw, count in keywords
        ])
    
    @app.route("/api/keywords/trends")
    def api_keyword_trends():
        """关键词趋势"""
        keywords = request.args.getlist("keyword")
        venue = request.args.get("venue")
        
        if not keywords:
            # 默认返回 Top 5 关键词的趋势
            top = repo.get_top_keywords(venue=venue, limit=5)
            keywords = [kw for kw, _ in top]
        
        result = []
        for kw in keywords:
            trend = repo.get_keyword_trend(kw, venue)
            years = sorted(trend.keys())
            result.append({
                "keyword": kw,
                "years": years,
                "counts": [trend[y] for y in years],
            })
        
        return jsonify(result)
    
    @app.route("/api/keywords/comparison")
    def api_comparison():
        """会议对比"""
        year = request.args.get("year", type=int)
        limit = request.args.get("limit", 10, type=int)
        
        if not year:
            years = repo.get_all_years()
            year = max(years) if years else 2024
        
        comparison = repo.get_venue_comparison(year, limit)
        
        return jsonify({
            "year": year,
            "venues": {
                venue: [{"keyword": kw, "count": c} for kw, c in keywords]
                for venue, keywords in comparison.items()
            }
        })
    
    @app.route("/api/keywords/wordcloud")
    def api_wordcloud():
        """词云数据"""
        venue = request.args.get("venue")
        year = request.args.get("year", type=int)
        limit = request.args.get("limit", 100, type=int)
        
        keywords = repo.get_top_keywords(
            venue=venue,
            year=year,
            limit=limit,
        )
        
        # 返回适合词云的格式
        return jsonify([
            {"name": kw, "value": count}
            for kw, count in keywords
        ])
    
    @app.route("/api/keywords/emerging")
    def api_emerging():
        """新兴关键词"""
        result = analyzer.get_emerging_keywords(top_n=20)
        return jsonify(result)
    
    # ==================== 系统 API ====================
    
    @app.route("/api/health")
    def api_health():
        """健康检查"""
        return jsonify({
            "status": "healthy",
            "service": "deeptrender",
        })
    
    @app.route("/api/status")
    def api_status():
        """系统状态"""
        import os
        from datetime import datetime
        
        # 数据库文件信息
        db_path = repo.db_path
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        db_modified = datetime.fromtimestamp(
            os.path.getmtime(db_path)
        ).isoformat() if os.path.exists(db_path) else None
        
        venues = repo.get_all_venues()
        years = repo.get_all_years()
        
        return jsonify({
            "database": {
                "path": str(db_path),
                "size_bytes": db_size,
                "last_modified": db_modified,
            },
            "data": {
                "total_papers": repo.get_paper_count(),
                "total_venues": len(venues),
                "venues": venues,
                "year_range": [min(years), max(years)] if years else None,
            },
            "server_time": datetime.now().isoformat(),
        })
    
    @app.route("/api/refresh", methods=["POST"])
    def api_refresh():
        """手动触发数据刷新（重新加载数据库）"""
        global repo, analyzer
        from database import DatabaseRepository
        from analysis import KeywordAnalyzer
        
        try:
            # 重新创建仓库实例以刷新数据
            repo = DatabaseRepository()
            analyzer = KeywordAnalyzer(repo)
            
            return jsonify({
                "status": "success",
                "message": "Data refreshed",
                "total_papers": repo.get_paper_count(),
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
            }), 500
    
    # ==================== Registry API ====================
    
    @app.route("/api/registry/venues")
    def api_registry_venues():
        """
        会议注册表 API
        
        返回所有注册会议及其统计信息（从缓存读取，秒开）
        """
        from config import VENUES
        
        result = []
        
        # 获取所有 venue summaries 缓存
        all_summaries = repo.analysis.get_all_venue_summaries()
        summary_map = {s["venue"]: s for s in all_summaries if s.get("year") is None}
        
        # 从配置中获取所有会议
        for venue_key, venue_config in VENUES.items():
            venue_name = venue_config.name
            
            # 从缓存获取统计
            summary = summary_map.get(venue_name)
            
            if summary:
                paper_count = summary.get("paper_count", 0)
                top_keywords = summary.get("top_keywords", [])[:10]
            else:
                # 如果没有缓存，实时查询
                paper_count = repo.get_paper_count(venue=venue_name)
                top_kw = repo.get_top_keywords(venue=venue_name, limit=10)
                top_keywords = [{"keyword": kw, "count": c} for kw, c in top_kw]
            
            result.append({
                "name": venue_name,
                "full_name": venue_config.full_name,
                "domain": getattr(venue_config, 'domain', 'ML'),
                "years_supported": venue_config.years,
                "icon_url": f"/static/assets/venues/{venue_name}.svg",
                "paper_count": paper_count,
                "latest_year": max(venue_config.years) if venue_config.years else None,
                "top_keywords": top_keywords
            })
        
        return jsonify({"venues": result})
    
    # ==================== arXiv API ====================
    
    @app.route("/api/arxiv/timeseries")
    def api_arxiv_timeseries():
        """
        arXiv 时间序列 API
        
        GET /api/arxiv/timeseries?granularity=year|week|day&category=cs.LG
        """
        granularity = request.args.get("granularity", "year")
        category = request.args.get("category", "ALL")
        
        # 从缓存读取
        data = repo.analysis.get_arxiv_timeseries(category, granularity)
        
        if not data:
            # 如果没有缓存，返回空数据
            return jsonify({
                "granularity": granularity,
                "category": category,
                "data": [],
                "cached": False
            })
        
        return jsonify({
            "granularity": granularity,
            "category": category,
            "data": data,
            "cached": True
        })
    
    @app.route("/api/arxiv/keywords/trends")
    def api_arxiv_keyword_trends():
        """
        arXiv 关键词趋势 API

        GET /api/arxiv/keywords/trends?granularity=week&keyword=diffusion&category=ALL
        """
        granularity = request.args.get("granularity", "year")
        keyword = request.args.get("keyword")
        category = request.args.get("category", "ALL")

        if not keyword:
            return jsonify({"error": "keyword parameter is required"}), 400

        # 从缓存读取
        data = repo.analysis.get_keyword_trends_cached(
            scope="arxiv",
            keyword=keyword,
            granularity=granularity
        )

        return jsonify({
            "keyword": keyword,
            "granularity": granularity,
            "category": category,
            "data": data
        })

    @app.route("/api/arxiv/stats")
    def api_arxiv_stats():
        """
        arXiv 统计概览 API

        GET /api/arxiv/stats
        """
        # 获取 arXiv 论文总数
        total_papers = repo.raw.get_raw_paper_count(source="arxiv")

        # 按分类统计
        categories_stats = {}
        for category in ["cs.LG", "cs.CL", "cs.CV", "cs.AI", "cs.RO"]:
            # 简单统计：从 raw_papers 中查询
            with repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM raw_papers
                    WHERE source = 'arxiv' AND categories LIKE ?
                """, (f"%{category}%",))
                count = cursor.fetchone()["count"]
                categories_stats[category] = count

        # 获取日期范围
        with repo._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MIN(retrieved_at) as min_date, MAX(retrieved_at) as max_date
                FROM raw_papers
                WHERE source = 'arxiv'
            """)
            row = cursor.fetchone()
            date_range = {
                "min": row["min_date"] if row["min_date"] else None,
                "max": row["max_date"] if row["max_date"] else None
            }

        # 获取最后更新时间
        latest_update = repo.analysis.get_meta("arxiv_last_run_ALL_year")

        return jsonify({
            "total_papers": total_papers,
            "categories": categories_stats,
            "date_range": date_range,
            "latest_update": latest_update
        })

    @app.route("/api/arxiv/compare")
    def api_arxiv_compare():
        """
        arXiv 分类对比 API

        GET /api/arxiv/compare?categories=cs.LG,cs.CV&granularity=year
        """
        from analysis.arxiv_agent import ArxivAnalysisAgent

        categories_str = request.args.get("categories", "cs.LG,cs.CV")
        categories = [c.strip() for c in categories_str.split(",")]
        granularity = request.args.get("granularity", "year")

        agent = ArxivAnalysisAgent()
        result = agent.compare_categories(categories, granularity)

        return jsonify(result)

    @app.route("/api/arxiv/emerging")
    def api_arxiv_emerging():
        """
        arXiv 新兴主题 API

        GET /api/arxiv/emerging?category=ALL&limit=20
        """
        category = request.args.get("category", "ALL")
        limit = request.args.get("limit", 20, type=int)
        min_growth_rate = request.args.get("min_growth_rate", 1.5, type=float)

        # 从数据库读取缓存的新兴主题
        topics = repo.analysis.get_emerging_topics(
            category=category,
            limit=limit,
            min_growth_rate=min_growth_rate
        )

        return jsonify(topics)

    @app.route("/api/arxiv/papers")
    def api_arxiv_papers():
        """
        arXiv 论文列表 API

        GET /api/arxiv/papers?category=cs.LG&limit=20&offset=0
        """
        category = request.args.get("category")
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)

        # 查询论文
        with repo._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM raw_papers WHERE source = 'arxiv'"
            params = []

            if category and category != "ALL":
                query += " AND categories LIKE ?"
                params.append(f"%{category}%")

            # 获取总数
            count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
            cursor.execute(count_query, params)
            total = cursor.fetchone()["total"]

            # 分页查询
            query += " ORDER BY retrieved_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, params)

            papers = []
            for row in cursor.fetchall():
                import json
                papers.append({
                    "arxiv_id": row["source_paper_id"],
                    "title": row["title"],
                    "abstract": row["abstract"],
                    "authors": json.loads(row["authors"]) if row["authors"] else [],
                    "categories": row["categories"],
                    "year": row["year"],
                    "retrieved_at": row["retrieved_at"],
                    "doi": row["doi"],
                    "journal_ref": row["journal_ref"],
                    "comments": row["comments"]
                })

        return jsonify({
            "total": total,
            "limit": limit,
            "offset": offset,
            "papers": papers
        })

    @app.route("/api/arxiv/paper/<arxiv_id>")
    def api_arxiv_paper_detail(arxiv_id):
        """
        arXiv 论文详情 API

        GET /api/arxiv/paper/<arxiv_id>
        """
        # 获取论文
        paper = repo.raw.get_raw_paper_by_source("arxiv", arxiv_id)

        if not paper:
            return jsonify({"error": "Paper not found"}), 404

        # 构建响应
        result = {
            "arxiv_id": paper.source_paper_id,
            "title": paper.title,
            "abstract": paper.abstract,
            "authors": paper.authors,
            "categories": paper.categories,
            "year": paper.year,
            "doi": paper.doi,
            "journal_ref": paper.journal_ref,
            "comments": paper.comments,
            "retrieved_at": paper.retrieved_at.isoformat() if paper.retrieved_at else None,
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            "abs_url": f"https://arxiv.org/abs/{arxiv_id}"
        }

        # 尝试获取关键词（如果已结构化）
        paper_id = repo.structured.find_paper_by_title(paper.title)
        if paper_id:
            keywords = repo.analysis.get_paper_keywords(paper_id)
            result["keywords"] = [kw.keyword for kw in keywords[:10]]
        else:
            result["keywords"] = []

        # TODO: 获取相关论文（基于关键词相似度）
        result["related_papers"] = []

        return jsonify(result)
    
    @app.route("/api/analysis/meta")
    def api_analysis_meta():
        """获取分析元信息"""
        meta = repo.analysis.get_all_meta()
        return jsonify(meta)
    
    # ==================== Venue Discovery API ====================
    
    @app.route("/api/venues/discover", methods=["POST"])
    def api_discover_venues():
        """动态发现会议并保存到数据库"""
        from scraper.venue_discovery import VenueDiscovery
        
        min_year = request.json.get("min_year", 2022) if request.json else 2022
        include_workshops = request.json.get("include_workshops", False) if request.json else False
        
        try:
            discovery = VenueDiscovery()
            venues = discovery.discover_conferences(
                min_year=min_year,
                include_workshops=include_workshops
            )
            
            # 保存到数据库
            saved_count = 0
            for v in venues:
                # 按会议名称分组，合并年份
                existing_venues = {}
                for venue in venues:
                    if venue.name not in existing_venues:
                        existing_venues[venue.name] = {
                            "openreview_ids": [],
                            "years": []
                        }
                    existing_venues[venue.name]["openreview_ids"].append(venue.venue_id)
                    existing_venues[venue.name]["years"].append(venue.year)
                
                # 批量保存
                for name, data in existing_venues.items():
                    venue_obj = next((v for v in venues if v.name == name), None)
                    if venue_obj:
                        repo.structured.save_discovered_venue(
                            name=name,
                            full_name=venue_obj.full_name,
                            domain=venue_obj.domain,
                            tier=venue_obj.tier,
                            venue_type="workshop" if venue_obj.is_workshop else "conference",
                            openreview_ids=data["openreview_ids"],
                            years=sorted(set(data["years"]), reverse=True)
                        )
                        saved_count += 1
            
            summary = discovery.get_summary_by_domain(venues)
            
            return jsonify({
                "status": "success",
                "discovered": len(venues),
                "saved": saved_count,
                "summary": summary
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    @app.route("/api/venues/stats")
    def api_venue_stats():
        """会议统计"""
        stats = repo.structured.get_venue_stats()
        return jsonify(stats)
    
    @app.route("/api/venues/by-domain")
    def api_venues_by_domain():
        """按领域获取会议"""
        domain = request.args.get("domain")
        if not domain:
            return jsonify({"error": "domain parameter required"}), 400
        
        venues_list = repo.structured.get_venues_by_domain(domain)
        result = []
        for v in venues_list:
            result.append({
                "name": v.canonical_name,
                "full_name": v.full_name,
                "domain": v.domain,
                "tier": getattr(v, 'tier', 'C'),
                "years": getattr(v, 'years_available', []),
                "openreview_ids": getattr(v, 'openreview_ids', []),
            })
        return jsonify({"domain": domain, "venues": result})
    
    @app.route("/api/venues/by-tier")
    def api_venues_by_tier():
        """按等级获取会议"""
        tier = request.args.get("tier", "A")
        
        venues_list = repo.structured.get_venues_by_tier(tier)
        result = []
        for v in venues_list:
            result.append({
                "name": v.canonical_name,
                "full_name": v.full_name,
                "domain": v.domain,
                "tier": getattr(v, 'tier', 'C'),
                "years": getattr(v, 'years_available', []),
                "paper_count": repo.get_paper_count(venue=v.canonical_name),
            })
        return jsonify({"tier": tier, "venues": result})
    
    @app.route("/api/venues/explorer")
    def api_venue_explorer():
        """会议浏览器 - 完整数据"""
        venues_list = repo.structured.get_all_venues()
        
        result = {
            "total": len(venues_list),
            "venues": [],
            "by_domain": {},
            "by_tier": {}
        }
        
        for v in venues_list:
            venue_data = {
                "name": v.canonical_name,
                "full_name": v.full_name,
                "domain": v.domain,
                "tier": getattr(v, 'tier', 'C'),
                "type": v.venue_type,
                "years": getattr(v, 'years_available', []),
                "paper_count": repo.get_paper_count(venue=v.canonical_name),
                "openreview_ids": getattr(v, 'openreview_ids', [])[:3],  # 只返回前3个
            }
            result["venues"].append(venue_data)
            
            # 按领域分组
            domain = v.domain or "General"
            if domain not in result["by_domain"]:
                result["by_domain"][domain] = []
            result["by_domain"][domain].append(venue_data)
            
            # 按等级分组
            tier = getattr(v, 'tier', 'C')
            if tier not in result["by_tier"]:
                result["by_tier"][tier] = []
            result["by_tier"][tier].append(venue_data)
        
        return jsonify(result)
    
    return app


def run_server(host="0.0.0.0", port=5000, debug=True):
    """运行服务器"""
    app = create_app()
    print(f"\n🌐 启动 Web 服务器: http://localhost:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
