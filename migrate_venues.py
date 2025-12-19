"""
数据库迁移脚本 - 添加会议发现相关字段

添加字段:
- tier (等级)
- openreview_ids (OpenReview ID 列表)
- years_available (可用年份)
- discovered_at (发现时间)
"""

import sqlite3
from pathlib import Path


def migrate():
    db_path = Path("data/keywords.db")
    
    if not db_path.exists():
        print("❌ 数据库不存在")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("开始迁移数据库...")
    
    # 检查当前字段
    cursor.execute("PRAGMA table_info(venues)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"现有字段: {existing_columns}")
    
    # 需要添加的字段
    new_columns = {
        'tier': "TEXT CHECK(tier IN ('A', 'B', 'C')) DEFAULT 'C'",
        'openreview_ids': "TEXT",
        'years_available': "TEXT",
        'discovered_at': "DATETIME"
    }
    
    # 添加缺失的字段
    for col_name, col_def in new_columns.items():
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE venues ADD COLUMN {col_name} {col_def}"
                cursor.execute(sql)
                print(f"✓ 添加字段: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"✗ 添加字段 {col_name} 失败: {e}")
        else:
            print(f"- 字段已存在: {col_name}")
    
    # 更新 domain 字段注释（如果需要扩展值）
    # SQLite 不支持修改列定义，所以这只是文档说明
    
    conn.commit()
    
    # 验证迁移
    cursor.execute("PRAGMA table_info(venues)")
    final_columns = [row[1] for row in cursor.fetchall()]
    print(f"\n迁移后字段: {final_columns}")
    
    conn.close()
    print("\n✅ 迁移完成")
    return True


if __name__ == "__main__":
    migrate()
