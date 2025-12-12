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
            "service": "depthtrender",
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
    
    return app


def run_server(host="0.0.0.0", port=5000, debug=True):
    """运行服务器"""
    app = create_app()
    print(f"\n🌐 启动 Web 服务器: http://localhost:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
