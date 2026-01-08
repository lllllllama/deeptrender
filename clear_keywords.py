import sqlite3
import sys
sys.path.insert(0, 'src')
from config import DATABASE_PATH

# 清除旧的 YAKE 关键词（重新用新过滤器提取）
conn = sqlite3.connect(DATABASE_PATH)
conn.execute("DELETE FROM paper_keywords WHERE method = 'yake'")
conn.commit()
print('已清除旧的 YAKE 关键词')

cur = conn.execute('SELECT COUNT(*) FROM paper_keywords')
print(f'剩余关键词: {cur.fetchone()[0]}')
conn.close()
