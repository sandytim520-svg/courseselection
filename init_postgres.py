#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 資料庫初始化腳本
用於在 Render 上初始化資料庫表格和測試數據
使用方法: python init_postgres.py
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 從環境變數取得資料庫連接字串
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ 錯誤: 找不到 DATABASE_URL 環境變數")
    print("請確保在 Render 環境中設定了 DATABASE_URL")
    exit(1)

# Render 的 DATABASE_URL 格式調整
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print("=" * 60)
print("PostgreSQL 資料庫初始化工具")
print("=" * 60)
print(f"\n🔗 連接資料庫...")

try:
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    print("✅ 資料庫連接成功!")
except Exception as e:
    print(f"❌ 資料庫連接失敗: {e}")
    exit(1)

# ========================================
# 刪除舊表格（如果存在）
# ========================================
print("\n🗑️ 清理舊表格...")
try:
    cursor.execute('DROP TABLE IF EXISTS enrollments CASCADE')
    cursor.execute('DROP TABLE IF EXISTS courses CASCADE')
    cursor.execute('DROP TABLE IF EXISTS users CASCADE')
    conn.commit()
    print("✅ 舊表格已清理")
except Exception as e:
    print(f"⚠️ 清理表格時發生錯誤: {e}")
    conn.rollback()

# ========================================
# 創建使用者表
# ========================================
print("\n📋 創建 users 表...")
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            name TEXT DEFAULT '',
            student_id TEXT DEFAULT '',
            department TEXT DEFAULT '',
            class_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            avatar TEXT DEFAULT '🐱',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    print("✅ users 表創建成功")
except Exception as e:
    print(f"❌ 創建 users 表失敗: {e}")
    conn.rollback()
    exit(1)

# ========================================
# 創建課程表
# ========================================
print("\n📋 創建 courses 表...")
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id SERIAL PRIMARY KEY,
            semester TEXT NOT NULL,
            department TEXT NOT NULL,
            grade TEXT,
            course_code TEXT NOT NULL,
            course_name TEXT NOT NULL,
            course_name_en TEXT,
            instructor TEXT,
            credits REAL,
            course_type TEXT,
            classroom TEXT,
            day_time TEXT,
            weekday TEXT,
            period TEXT,
            capacity INTEGER DEFAULT 60,
            enrolled INTEGER DEFAULT 0,
            class_group TEXT,
            remarks TEXT,
            course_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    print("✅ courses 表創建成功")
except Exception as e:
    print(f"❌ 創建 courses 表失敗: {e}")
    conn.rollback()
    exit(1)

# ========================================
# 創建選課記錄表
# ========================================
print("\n📋 創建 enrollments 表...")
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'enrolled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, course_id)
        )
    ''')
    conn.commit()
    print("✅ enrollments 表創建成功")
except Exception as e:
    print(f"❌ 創建 enrollments 表失敗: {e}")
    conn.rollback()
    exit(1)

# ========================================
# 創建索引
# ========================================
print("\n📋 創建索引...")
try:
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_semester ON courses(semester)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_department ON courses(department)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_grade ON courses(grade)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_user ON enrollments(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id)')
    conn.commit()
    print("✅ 索引創建成功")
except Exception as e:
    print(f"⚠️ 創建索引時發生錯誤: {e}")
    conn.rollback()

# ========================================
# 插入測試使用者
# ========================================
print("\n👥 插入測試使用者...")
try:
    # 先檢查是否已有使用者
    cursor.execute('SELECT COUNT(*) as count FROM users')
    result = cursor.fetchone()
    
    if result['count'] == 0:
        test_users = [
            ('student1', 'pass123', 'student', '測試學生1', 'S001', '護理系', '護理一甲', '0912345678', 'student1@ntunhs.edu.tw', '🐱'),
            ('student2', 'pass123', 'student', '測試學生2', 'S002', '健康事業管理系', '健管二甲', '0923456789', 'student2@ntunhs.edu.tw', '🐶'),
            ('admin', 'admin123', 'admin', '系統管理員', 'A001', '資訊中心', '', '0911111111', 'admin@ntunhs.edu.tw', '👨‍💼'),
        ]
        
        for user in test_users:
            cursor.execute('''
                INSERT INTO users (username, password, role, name, student_id, department, class_name, phone, email, avatar)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', user)
        
        conn.commit()
        print(f"✅ 成功插入 {len(test_users)} 個測試使用者")
        print("   - student1 / pass123 (學生)")
        print("   - student2 / pass123 (學生)")
        print("   - admin / admin123 (管理員)")
    else:
        print(f"⚠️ 資料庫已有 {result['count']} 個使用者，跳過插入測試數據")
except Exception as e:
    print(f"❌ 插入測試使用者失敗: {e}")
    conn.rollback()

# ========================================
# 驗證表格
# ========================================
print("\n🔍 驗證資料庫表格...")
try:
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    print("✅ 現有表格:")
    for table in tables:
        print(f"   - {table['table_name']}")
        
    # 檢查各表格的資料數量
    print("\n📊 表格資料統計:")
    cursor.execute('SELECT COUNT(*) as count FROM users')
    print(f"   - users: {cursor.fetchone()['count']} 筆")
    
    cursor.execute('SELECT COUNT(*) as count FROM courses')
    print(f"   - courses: {cursor.fetchone()['count']} 筆")
    
    cursor.execute('SELECT COUNT(*) as count FROM enrollments')
    print(f"   - enrollments: {cursor.fetchone()['count']} 筆")
    
except Exception as e:
    print(f"❌ 驗證失敗: {e}")

# 關閉連接
cursor.close()
conn.close()

print("\n" + "=" * 60)
print("✅ 資料庫初始化完成!")
print("=" * 60)
print("\n📝 測試帳號:")
print("   學生: student1 / pass123")
print("   管理員: admin / admin123")
print("\n💡 提示: 請透過管理介面匯入課程資料")
