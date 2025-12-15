#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北護課程查詢系統 - 資料庫建立腳本
從Excel檔案匯入課程資料到SQLite資料庫
"""

import sqlite3
import pandas as pd
import os
from pathlib import Path

# 設定路徑 - 使用相對路徑，資料庫和Excel檔案放在同一目錄
SCRIPT_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = SCRIPT_DIR  # Excel檔案放在腳本同目錄
DB_PATH = SCRIPT_DIR / 'database.db'  # 資料庫也放在同目錄

# 定義系所對照表
DEPARTMENT_MAPPING = {
    '護理系': '護理系',
    '高齡健康照護系': '高齡健康照護系',
    '護理助產及婦女健康系': '護理助產及婦女健康系',
    '醫護教育暨數位學習系': '醫護教育暨數位學習系',
    '中西醫結合護理研究所': '中西醫結合護理研究所',
    '中西醫結合護理研究所(舊)': '中西醫結合護理研究所(舊)',
    '健康科技學院(不分系)': '健康科技學院(不分系)',
    '健康事業管理系': '健康事業管理系',
    '資訊管理系': '資訊管理系',
    '休閒產業與健康促進系': '休閒產業與健康促進系',
    '長期照護系': '長期照護系',
    '語言治療與聽力學系': '語言治療與聽力學系',
    '國際健康科技碩士學位學程': '國際健康科技碩士學位學程',
    '人類發展與健康學院(不分系)': '人類發展與健康學院(不分系)',
    '嬰幼兒保育系': '嬰幼兒保育系',
    '運動保健系': '運動保健系',
    '生死與健康心理諮商系': '生死與健康心理諮商系',
    '高齡健康暨運動保健技優專班': '高齡健康暨運動保健技優專班',
    '智慧健康科技技優專班': '智慧健康科技技優專班',
    '人工智慧與健康大數據研究所': '人工智慧與健康大數據研究所'
}

def create_tables(conn):
    """建立資料庫表格"""
    cursor = conn.cursor()
    
    # 刪除舊表格
    cursor.execute('DROP TABLE IF EXISTS enrollments')
    cursor.execute('DROP TABLE IF EXISTS courses')
    cursor.execute('DROP TABLE IF EXISTS users')
    
    # 建立使用者表
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 建立課程表 (包含大綱所需欄位)
    cursor.execute('''
        CREATE TABLE courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    # 建立選課記錄表
    cursor.execute('''
        CREATE TABLE enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            status TEXT DEFAULT 'enrolled',
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id),
            UNIQUE(user_id, course_id)
        )
    ''')
    
    # 建立索引
    cursor.execute('CREATE INDEX idx_courses_semester ON courses(semester)')
    cursor.execute('CREATE INDEX idx_courses_department ON courses(department)')
    cursor.execute('CREATE INDEX idx_courses_grade ON courses(grade)')
    cursor.execute('CREATE INDEX idx_enrollments_user ON enrollments(user_id)')
    
    conn.commit()
    print("✅ 資料表建立成功")

def insert_test_users(conn):
    """插入測試使用者"""
    cursor = conn.cursor()
    
    users = [
        ('student1', 'pass123', 'student'),
        ('student2', 'pass123', 'student'),
        ('admin', 'admin123', 'admin')
    ]
    
    cursor.executemany(
        'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
        users
    )
    conn.commit()
    print(f"✅ 插入 {len(users)} 個測試使用者")

def extract_day_time(time_str):
    """從時間字串提取星期和時間"""
    if pd.isna(time_str) or time_str == '':
        return ''
    
    # 將完整時間資訊轉換為簡潔格式
    # 例如: "星期一(1,2)" -> "週一 1-2"
    import re
    
    time_str = str(time_str)
    days = {
        '星期一': '週一', '星期二': '週二', '星期三': '週三',
        '星期四': '週四', '星期五': '週五', '星期六': '週六',
        '星期日': '週日'
    }
    
    for old, new in days.items():
        time_str = time_str.replace(old, new)
    
    return time_str

def format_day_time(day_of_week, period):
    """組合星期和節次成為時間字串"""
    if not day_of_week and not period:
        return ''
    
    # 星期轉換
    day_map = {
        '1': '週一', '2': '週二', '3': '週三', 
        '4': '週四', '5': '週五', '6': '週六', 
        '7': '週日', '0': '週日'
    }
    
    day_str = day_map.get(str(day_of_week), '')
    
    if day_str and period:
        # 處理節次,例如 "6,7" -> "6-7"
        period_str = str(period).replace(',', '-')
        return f"{day_str} {period_str}"
    elif day_str:
        return day_str
    elif period:
        return f"節次 {period}"
    
    return ''

def get_department_name(dept_code, dept_code_mapping):
    """根據系所代碼取得系所名稱"""
    # 完整系所代碼對照表
    dept_mapping = {
        # 護理學院 (11xxx)
        '11120': '護理系',
        '11140': '護理系',
        '11161': '護理助產及婦女健康系',
        '11162': '護理助產及婦女健康系',
        '11163': '護理助產及婦女健康系',
        '11164': '護理助產及婦女健康系',
        '11165': '護理助產及婦女健康系',
        '11166': '護理助產及婦女健康系',
        '11167': '護理助產及婦女健康系',
        '11168': '護理助產及婦女健康系',
        '11169': '中西醫結合護理研究所',
        '11170': '中西醫結合護理研究所',
        '11190': '護理系',
        '11230': '護理系',
        '11330': '護理系',
        '11461': '高齡健康照護系',
        '11462': '高齡健康照護系',
        '11463': '高齡健康照護系',
        '11464': '高齡健康照護系',
        '11465': '高齡健康照護系',
        '11466': '高齡健康照護系',
        '11467': '高齡健康照護系',
        '11468': '高齡健康照護系',
        '11860': '醫護教育暨數位學習系',
        '11870': '醫護教育暨數位學習系',
        
        # 跨系所或學院 (1Cxxx, 1Dxxx, 13xxx)
        '1C120': '護理學院(不分系)',
        '1C160': '護理學院(不分系)',
        '1C330': '護理學院(不分系)',
        '1C860': '護理學院(不分系)',
        '1D110': '護理學院(不分系)',
        '1D120': '護理學院(不分系)',
        '1D160': '護理學院(不分系)',
        '13140': '護理學院(不分系)',
        '13160': '護理學院(不分系)',
        
        # 健康科技學院 (2xxxx)
        '20160': '健康科技學院(不分系)',
        '21120': '健康事業管理系',
        '21140': '健康事業管理系',
        '21160': '健康事業管理系',
        '21330': '健康事業管理系',
        '21460': '健康事業管理系',
        '22140': '資訊管理系',
        '22160': '資訊管理系',
        '23140': '長期照護系',
        '23160': '長期照護系',
        '23460': '長期照護系',
        '24120': '休閒產業與健康促進系',
        '24150': '休閒產業與健康促進系',
        '24160': '休閒產業與健康促進系',
        '25140': '語言治療與聽力學系',
        '25161': '語言治療與聽力學系',
        '25162': '語言治療與聽力學系',
        '26860': '健康科技學院(不分系)',
        
        # 人類發展與健康學院 (3xxxx)
        '30860': '人類發展與健康學院(不分系)',
        '31120': '嬰幼兒保育系',
        '31140': '嬰幼兒保育系',
        '31160': '嬰幼兒保育系',
        '31180': '嬰幼兒保育系',
        '32140': '運動保健系',
        '32160': '運動保健系',
        '32460': '運動保健系',
        '32860': '高齡健康暨運動保健技優專班',
        '33140': '生死與健康心理諮商系',
        '33161': '生死與健康心理諮商系',
        '33162': '生死與健康心理諮商系',
        
        # 研究所 (4xxxx)
        '41140': '中西醫結合護理研究所(舊)',
        '42140': '國際健康科技碩士學位學程',
        '43160': '人工智慧與健康大數據研究所',
    }
    
    # 如果在對照表中找到
    if dept_code in dept_mapping:
        return dept_mapping[dept_code]
    
    # 如果在已知對照表中
    if dept_code in dept_code_mapping:
        return dept_code_mapping[dept_code]
    
    # 根據代碼前綴猜測學院
    if dept_code.startswith('11') or dept_code.startswith('1'):
        return '護理學院'
    elif dept_code.startswith('2'):
        return '健康科技學院'
    elif dept_code.startswith('3'):
        return '人類發展與健康學院'
    elif dept_code.startswith('4'):
        return '研究所課程'
    
    return f'其他({dept_code})'

def extract_grade(course_name, course_code):
    """從課程名稱或代碼提取年級"""
    # 嘗試從課程代碼提取年級
    if pd.notna(course_code):
        code_str = str(course_code)
        # 假設課程代碼格式中可能包含年級資訊
        if len(code_str) >= 2:
            first_digit = code_str[0]
            if first_digit.isdigit() and 1 <= int(first_digit) <= 4:
                return first_digit
    
    # 從課程名稱中找尋年級關鍵字
    if pd.notna(course_name):
        name_str = str(course_name)
        for grade in ['一', '二', '三', '四']:
            if f'{grade}年級' in name_str:
                return str(['一', '二', '三', '四'].index(grade) + 1)
    
    return ''

def process_excel_file(file_path, semester):
    """處理單個Excel檔案"""
    print(f"\n📖 讀取檔案: {file_path.name} (學期: {semester})")
    
    try:
        # 讀取Excel檔案 - header在第3列,然後第一列資料是欄位名稱
        df = pd.read_excel(file_path, header=3)
        
        # 第一列是真正的欄位名稱
        if len(df) > 0:
            column_names = df.iloc[0].tolist()
            df = df.iloc[1:].reset_index(drop=True)
            df.columns = column_names
        
        print(f"   原始資料: {len(df)} 列")
        
        # 建立系所代碼對照表
        dept_code_mapping = {}
        
        courses = []
        
        for idx, row in df.iterrows():
            # 提取課程資訊
            course_code = str(row.get('科目代碼(新碼全碼)', '')).strip() if pd.notna(row.get('科目代碼(新碼全碼)')) else ''
            course_name = str(row.get('科目中文名稱', '')).strip() if pd.notna(row.get('科目中文名稱')) else ''
            course_name_en = str(row.get('科目英文名稱', '')).strip() if pd.notna(row.get('科目英文名稱')) else ''
            instructor = str(row.get('授課教師姓名', '')).strip() if pd.notna(row.get('授課教師姓名')) else ''
            dept_code = str(row.get('系所代碼', '')).strip() if pd.notna(row.get('系所代碼')) else ''
            credits = row.get('學分數', 0)
            course_type = str(row.get('課別名稱', '')).strip() if pd.notna(row.get('課別名稱')) else ''
            classroom = str(row.get('上課地點', '')).strip() if pd.notna(row.get('上課地點')) else ''
            day_of_week = str(row.get('上課星期', '')).strip() if pd.notna(row.get('上課星期')) else ''
            period_str = str(row.get('上課節次', '')).strip() if pd.notna(row.get('上課節次')) else ''
            grade_num = str(row.get('年級', '')).strip() if pd.notna(row.get('年級')) else ''
            class_group = str(row.get('上課班組', '')).strip() if pd.notna(row.get('上課班組')) else ''
            remarks = str(row.get('課表備註', '')).strip() if pd.notna(row.get('課表備註')) else ''
            course_summary = str(row.get('課程中文摘要', '')).strip() if pd.notna(row.get('課程中文摘要')) else ''
            student_count = row.get('上課人數', 60)
            
            # 跳過空白課程
            if not course_name or course_name == '':
                continue
            
            # 處理年級
            grade = grade_num if grade_num and grade_num.isdigit() else ''
            
            # 組合時間資訊 (星期 + 節次)
            day_time = format_day_time(day_of_week, period_str)
            
            # 取得系所名稱
            department = get_department_name(dept_code, dept_code_mapping)
            
            # 處理學分
            try:
                credits = float(credits) if pd.notna(credits) else 0.0
            except:
                credits = 0.0
            
            # 處理容量
            try:
                capacity = int(student_count) if pd.notna(student_count) else 60
            except:
                capacity = 60
            
            course = (
                semester,           # semester
                department,         # department
                grade,             # grade
                course_code,       # course_code
                course_name,       # course_name
                course_name_en,    # course_name_en
                instructor,        # instructor
                credits,           # credits
                course_type,       # course_type
                classroom,         # classroom
                day_time,          # day_time
                day_of_week,       # weekday (原始星期數字)
                period_str,        # period (原始節次)
                capacity,          # capacity
                0,                 # enrolled (預設0人)
                class_group,       # class_group (上課班組)
                remarks,           # remarks (課表備註)
                course_summary     # course_summary (課程摘要)
            )
            
            courses.append(course)
        
        print(f"   ✅ 處理完成: {len(courses)} 筆有效課程")
        return courses
        
    except Exception as e:
        print(f"   ❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """主程式"""
    print("=" * 60)
    print("北護課程查詢系統 - 資料庫建立工具")
    print("=" * 60)
    
    # 連接資料庫
    conn = sqlite3.connect(DB_PATH)
    print(f"\n📁 資料庫位置: {DB_PATH}")
    print(f"📁 搜尋目錄: {UPLOAD_DIR}")
    
    # 建立表格
    create_tables(conn)
    
    # 插入測試使用者
    insert_test_users(conn)
    
    # 自動搜尋所有課程查詢Excel檔案
    print("\n🔍 搜尋Excel檔案...")
    all_courses = []
    
    # 列出目錄中所有檔案
    all_files = list(UPLOAD_DIR.glob('*.xls')) + list(UPLOAD_DIR.glob('*.xlsx'))
    print(f"   找到 {len(all_files)} 個Excel檔案")
    
    for file_path in all_files:
        filename = file_path.name
        print(f"   - {filename}")
        
        # 從檔名提取學期 (例如: 課程查詢_1142.xls -> 1142)
        semester = None
        if '1142' in filename:
            semester = '1142'
        elif '1141' in filename:
            semester = '1141'
        elif '1132' in filename:
            semester = '1132'
        elif '1131' in filename:
            semester = '1131'
        else:
            # 嘗試從檔名提取4位數字作為學期
            import re
            match = re.search(r'(\d{4})', filename)
            if match:
                semester = match.group(1)
            else:
                semester = '1142'  # 預設學期
                print(f"     ⚠️ 無法識別學期，使用預設值: {semester}")
        
        print(f"     學期: {semester}")
        courses = process_excel_file(file_path, semester)
        all_courses.extend(courses)
    
    if not all_files:
        print("\n❌ 沒有找到任何Excel檔案！")
        print("   請確認Excel檔案放在以下目錄:")
        print(f"   {UPLOAD_DIR}")
    
    # 插入課程資料
    if all_courses:
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO courses (
                semester, department, grade, course_code, course_name,
                course_name_en, instructor, credits, course_type, classroom, 
                day_time, weekday, period, capacity, enrolled, 
                class_group, remarks, course_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', all_courses)
        conn.commit()
        print(f"\n✅ 成功插入 {len(all_courses)} 筆課程資料")
    
    # 顯示統計資訊
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM courses')
    total_courses = cursor.fetchone()[0]
    
    cursor.execute('SELECT semester, COUNT(*) FROM courses GROUP BY semester')
    semester_stats = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(DISTINCT department) FROM courses')
    total_departments = cursor.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("📊 資料庫統計")
    print("=" * 60)
    print(f"總課程數: {total_courses}")
    print(f"系所數量: {total_departments}")
    print("\n各學期課程數:")
    for semester, count in semester_stats:
        print(f"  {semester}: {count} 筆")
    
    # 顯示系所列表
    cursor.execute('SELECT DISTINCT department FROM courses ORDER BY department')
    departments = [row[0] for row in cursor.fetchall()]
    print(f"\n系所列表 ({len(departments)}):")
    for dept in departments:
        print(f"  - {dept}")
    
    conn.close()
    print("\n✅ 資料庫建立完成!")
    print(f"📁 資料庫檔案: {DB_PATH}")

if __name__ == '__main__':
    main()