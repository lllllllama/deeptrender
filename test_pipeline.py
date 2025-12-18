import sys
sys.path.insert(0, 'src')

# 测试新的管线
print('=== 测试完整管线 ===')

# 1. 测试 AnalysisAgent
from agents.analysis_agent import AnalysisAgent
agent = AnalysisAgent()
# 已经提取过，应该返回 0
result = agent.run(method='yake', limit=100)
print(f'AnalysisAgent: {result}')

# 2. 测试新的 emerging keywords
from analysis.statistics import KeywordAnalyzer
analyzer = KeywordAnalyzer()
emerging = analyzer.get_emerging_keywords(min_count=3, top_n=10)
print(f'Emerging keywords: {emerging}')

# 3. 测试详细 emerging
detailed = analyzer.get_emerging_keywords_detailed(min_count=3, top_n=5)
for item in detailed:
    kw = item['keyword']
    is_new = '🆕' if item['is_new'] else ''
    growth = f"{item['growth']:.1f}x" if item['growth'] else 'NEW'
    print(f'  {is_new} {kw}: {growth} (count={item["count"]})')
