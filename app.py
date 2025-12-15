# ==========================================================
# 北護課程查詢系統 - Flask後端程式 (PostgreSQL版)
# 支援 Render PostgreSQL 資料庫
# ==========================================================

from flask import Flask, request, jsonify, session, render_template, redirect
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import pandas as pd

# 判斷是否使用 PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL (Render)
    import psycopg2
    from psycopg2.extras import RealDictCursor
    USE_POSTGRES = True
    # Render 的 DATABASE_URL 格式可能需要調整
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
else:
    # 本地 SQLite
    import sqlite3
    USE_POSTGRES = False
    DATABASE = 'database.db'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ntunhs_course_system_2024_secret_key')

# 檔案上傳設定
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024  # 300 MB

# 建立上傳資料夾
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ========================================
# 資料庫連接函數
# ========================================
def get_db():
    """取得資料庫連接"""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=None, fetch=False, fetchone=False):
    """執行查詢的通用函數"""
    conn = get_db()
    if USE_POSTGRES:
        cursor = conn.cursor()
        # PostgreSQL 使用 %s 而不是 ?
        query = query.replace('?', '%s')
        cursor.execute(query, params or ())
        if fetchone:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
        conn.commit()
        cursor.close()
        conn.close()
        return result
    else:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        if fetchone:
            result = cursor.fetchone()
            result = dict(result) if result else None
        elif fetch:
            result = [dict(row) for row in cursor.fetchall()]
        else:
            result = cursor.lastrowid
        conn.commit()
        conn.close()
        return result

def init_db():
    """初始化資料庫 - 創建表格和添加新欄位"""
    print("[init_db] 開始初始化資料庫...")
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            print("[init_db] 使用 PostgreSQL 模式")
            
            # PostgreSQL 創建表格
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
            print("[init_db] users 表創建/檢查完成")
            
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
            print("[init_db] courses 表創建/檢查完成")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enrollments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
                    status TEXT DEFAULT 'enrolled',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            print("[init_db] enrollments 表創建/檢查完成")
            
            # 創建索引
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_semester ON courses(semester)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_department ON courses(department)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_user ON enrollments(user_id)')
                conn.commit()
                print("[init_db] 索引創建完成")
            except Exception as e:
                print(f"[init_db] 創建索引時發生錯誤（可能已存在）: {e}")
                conn.rollback()
            
            # 嘗試添加 avatar 欄位（如果不存在）
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar TEXT DEFAULT '🐱'")
                conn.commit()
            except Exception as e:
                print(f"[init_db] avatar 欄位可能已存在: {e}")
                conn.rollback()
            
            # 檢查是否需要插入預設使用者
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()
            if USE_POSTGRES:
                user_count = user_count['count'] if isinstance(user_count, dict) else user_count[0]
            else:
                user_count = user_count[0] if user_count else 0
            
            if user_count == 0:
                print("[init_db] 插入預設使用者...")
                cursor.execute('''
                    INSERT INTO users (username, password, role, name, student_id, department, avatar)
                    VALUES 
                        ('student1', 'pass123', 'student', '測試學生', 'S001', '護理系', '🐱'),
                        ('admin', 'admin123', 'admin', '系統管理員', 'A001', '資訊中心', '👨‍💼')
                ''')
                conn.commit()
                print("[init_db] 預設使用者插入完成")
                
        else:
            print("[init_db] 使用 SQLite 模式")
            # SQLite
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS courses (
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enrollments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'enrolled',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (course_id) REFERENCES courses(id)
                )
            ''')
            
            # 嘗試添加新欄位（SQLite 不支援 IF NOT EXISTS）
            columns_to_add = ['name', 'student_id', 'department', 'class_name', 'phone', 'email', 'avatar']
            for col in columns_to_add:
                try:
                    default_val = "'🐱'" if col == 'avatar' else "''"
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT {default_val}")
                except: 
                    pass
        
        conn.commit()
        cursor.close()
        conn.close()
        print("[init_db] 資料庫初始化完成!")
        
    except Exception as e:
        print(f"[init_db] 初始化資料庫時發生錯誤: {e}")
        import traceback
        traceback.print_exc()

# 初始化資料庫
print("[APP] 應用程式啟動，開始初始化資料庫...")
init_db()

# ========================================
# 路由: 首頁 (登入頁面)
# ========================================
@app.route('/')
def index():
    """登入頁面 - 根據session自動跳轉"""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect('/admin')
        else:
            return redirect('/student')
    return render_template('index.html')

# ========================================
# 路由: 學生頁面
# ========================================
@app.route('/student')
def student_page():
    """學生頁面"""
    if 'user_id' not in session:
        return redirect('/')
    if session.get('role') != 'student':
        return redirect('/admin')
    return render_template('student.html')

# ========================================
# 路由: 訪客頁面
# ========================================
@app.route('/guest')
def guest_page():
    """訪客頁面 - 可瀏覽但不能儲存"""
    return render_template('guest.html')

# ========================================
# 路由: 資料庫初始化 (免費方案用)
# ========================================
@app.route('/api/init-database')
def init_database_api():
    """
    手動初始化資料庫的 API 端點
    訪問 /api/init-database 即可初始化
    適用於 Render 免費方案（無法使用 Shell）
    """
    results = []
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            results.append("✅ PostgreSQL 連接成功")
            
            # 創建 users 表
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
            results.append("✅ users 表創建成功")
            
            # 創建 courses 表
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
            results.append("✅ courses 表創建成功")
            
            # 創建 enrollments 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enrollments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
                    status TEXT DEFAULT 'enrolled',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            results.append("✅ enrollments 表創建成功")
            
            # 創建索引
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_semester ON courses(semester)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_courses_department ON courses(department)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_enrollments_user ON enrollments(user_id)')
                conn.commit()
                results.append("✅ 索引創建成功")
            except Exception as e:
                results.append(f"⚠️ 索引可能已存在: {str(e)}")
                conn.rollback()
            
            # 檢查並插入預設使用者
            cursor.execute('SELECT COUNT(*) as count FROM users')
            user_count = cursor.fetchone()
            count = user_count['count'] if isinstance(user_count, dict) else user_count[0]
            
            if count == 0:
                cursor.execute('''
                    INSERT INTO users (username, password, role, name, student_id, department, avatar)
                    VALUES 
                        ('student1', 'pass123', 'student', '測試學生', 'S001', '護理系', '🐱'),
                        ('admin', 'admin123', 'admin', '系統管理員', 'A001', '資訊中心', '👨‍💼')
                ''')
                conn.commit()
                results.append("✅ 預設使用者創建成功 (student1/pass123, admin/admin123)")
            else:
                results.append(f"ℹ️ 已有 {count} 個使用者，跳過創建預設使用者")
            
            # 統計資料
            cursor.execute('SELECT COUNT(*) as count FROM courses')
            course_count = cursor.fetchone()
            course_count = course_count['count'] if isinstance(course_count, dict) else course_count[0]
            results.append(f"📊 目前課程數量: {course_count}")
            
        else:
            results.append("ℹ️ 使用 SQLite 模式（本地開發）")
            init_db()
            results.append("✅ SQLite 資料庫初始化完成")
        
        cursor.close()
        conn.close()
        
        # 返回 HTML 格式的結果
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>資料庫初始化結果</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #2d5a27; }
                .result { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 5px; }
                .success { color: #28a745; }
                .info { color: #17a2b8; }
                .warning { color: #ffc107; }
                a { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #2d5a27; color: white; text-decoration: none; border-radius: 5px; }
                a:hover { background: #1e3d1a; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🗄️ 資料庫初始化結果</h1>
                %s
                <a href="/">← 返回登入頁面</a>
            </div>
        </body>
        </html>
        ''' % ''.join([f'<div class="result">{r}</div>' for r in results])
        
        return html
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>資料庫初始化錯誤</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                h1 {{ color: #dc3545; }}
                pre {{ background: #f8f9fa; padding: 15px; overflow-x: auto; border-radius: 5px; }}
                a {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #2d5a27; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>❌ 初始化失敗</h1>
                <p>錯誤訊息: {str(e)}</p>
                <pre>{error_detail}</pre>
                <a href="/">← 返回登入頁面</a>
            </div>
        </body>
        </html>
        '''
        return html

# ========================================
# 路由: 管理者頁面
# ========================================
@app.route('/admin')
def admin_page():
    """管理者頁面"""
    if 'user_id' not in session:
        return redirect('/')
    if session.get('role') != 'admin':
        return redirect('/student')
    return render_template('admin.html')

# ========================================
# API: 登入
# ========================================
@app.route('/api/login', methods=['POST'])
def login():
    """使用者登入"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': '請輸入帳號和密碼'})
    
    user = execute_query(
        'SELECT * FROM users WHERE username = ? AND password = ?',
        (username, password), fetchone=True
    )
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['name'] = user.get('name') or user['username']
        session['avatar'] = user.get('avatar') or '🐱'
        
        return jsonify({
            'success': True,
            'message': '登入成功',
            'role': user['role'],
            'user_id': user['id'],
            'username': user['username'],
            'name': user.get('name') or user['username'],
            'avatar': user.get('avatar') or '🐱'
        })
    else:
        return jsonify({'success': False, 'message': '帳號或密碼錯誤'})

# ========================================
# API: 登出
# ========================================
@app.route('/api/logout', methods=['POST'])
def logout():
    """使用者登出"""
    session.clear()
    return jsonify({'success': True, 'message': '登出成功'})

# ========================================
# API: 取得個人檔案
# ========================================
@app.route('/api/profile', methods=['GET'])
def get_profile():
    """取得個人檔案"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '請先登入'})
    
    user = execute_query(
        'SELECT id, username, role, name, student_id, department, class_name, phone, email, avatar FROM users WHERE id = ?',
        (session['user_id'],), fetchone=True
    )
    
    if user:
        return jsonify({
            'success': True,
            'profile': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'name': user.get('name') or user['username'],
                'student_id': user.get('student_id') or user['username'],
                'department': user.get('department') or '',
                'class_name': user.get('class_name') or '',
                'phone': user.get('phone') or '',
                'email': user.get('email') or '',
                'avatar': user.get('avatar') or '🐱'
            }
        })
    else:
        return jsonify({'success': False, 'message': '找不到使用者'})

# ========================================
# API: 更新個人檔案 (學生可改電話、電子郵件、頭貼)
# ========================================
@app.route('/api/profile', methods=['PUT'])
def update_profile():
    """更新個人檔案"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '請先登入'})
    
    data = request.json
    phone = data.get('phone', '')
    email = data.get('email', '')
    avatar = data.get('avatar', '')
    
    if avatar:
        execute_query(
            'UPDATE users SET phone = ?, email = ?, avatar = ? WHERE id = ?',
            (phone, email, avatar, session['user_id'])
        )
        session['avatar'] = avatar
    else:
        execute_query(
            'UPDATE users SET phone = ?, email = ? WHERE id = ?',
            (phone, email, session['user_id'])
        )
    
    return jsonify({'success': True, 'message': '更新成功'})

# ========================================
# API: 變更密碼
# ========================================
@app.route('/api/change-password', methods=['POST'])
def change_password():
    """變更密碼"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '請先登入'})
    
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    if not old_password or not new_password:
        return jsonify({'success': False, 'message': '請填寫所有欄位'})
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '新密碼與確認密碼不一致'})
    
    user = execute_query(
        'SELECT password FROM users WHERE id = ?',
        (session['user_id'],), fetchone=True
    )
    
    if user['password'] != old_password:
        return jsonify({'success': False, 'message': '舊密碼錯誤'})
    
    execute_query(
        'UPDATE users SET password = ? WHERE id = ?',
        (new_password, session['user_id'])
    )
    
    return jsonify({'success': True, 'message': '密碼變更成功'})

# ========================================
# API: 忘記密碼 - 驗證身份
# ========================================
@app.route('/api/forgot-password/verify', methods=['POST'])
def forgot_password_verify():
    """忘記密碼 - 驗證ID/學號和電話"""
    data = request.json
    student_id = data.get('student_id', '')
    phone = data.get('phone', '')
    
    if not student_id or not phone:
        return jsonify({'success': False, 'message': '請輸入學號和電話'})
    
    # 可以用 username 或 student_id 來查找
    user = execute_query(
        'SELECT id, username, name FROM users WHERE (username = ? OR student_id = ?) AND phone = ?',
        (student_id, student_id, phone), fetchone=True
    )
    
    if user:
        return jsonify({
            'success': True,
            'message': '驗證成功',
            'user_id': user['id'],
            'name': user.get('name') or user['username']
        })
    else:
        return jsonify({'success': False, 'message': '學號或電話錯誤'})

# ========================================
# API: 忘記密碼 - 重設密碼
# ========================================
@app.route('/api/forgot-password/reset', methods=['POST'])
def forgot_password_reset():
    """忘記密碼 - 重設密碼"""
    data = request.json
    user_id = data.get('user_id')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    if not user_id or not new_password:
        return jsonify({'success': False, 'message': '請填寫所有欄位'})
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '新密碼與確認密碼不一致'})
    
    execute_query(
        'UPDATE users SET password = ? WHERE id = ?',
        (new_password, user_id)
    )
    
    return jsonify({'success': True, 'message': '密碼重設成功，請重新登入'})

# ========================================
# API: 取得系所列表
# ========================================
@app.route('/api/departments', methods=['GET'])
def get_departments():
    """取得所有系所"""
    departments = execute_query(
        'SELECT DISTINCT department FROM courses WHERE department IS NOT NULL ORDER BY department',
        fetch=True
    )
    
    dept_list = [d['department'] for d in departments]
    
    # 如果資料庫中沒有課程，提供預設系所列表
    if not dept_list:
        dept_list = [
            '護理系',
            '護理系博士班',
            '護理系碩士班',
            '高齡健康照護系',
            '長期照護系',
            '健康事業管理系',
            '資訊管理系',
            '嬰幼兒保育系',
            '語言治療與聽力學系',
            '語言治療與聽力學系碩士班',
            '運動保健系',
            '休閒產業與健康促進系',
            '生死與健康心理諮商系',
            '人工智慧與健康大數據研究所',
            '通識教育中心',
            '體育室',
            '學士後多元專長',
            '學士後學位學程'
        ]
    
    return jsonify({'success': True, 'departments': dept_list})

# ========================================
# API: 取得學期列表
# ========================================
@app.route('/api/semesters', methods=['GET'])
def get_semesters():
    """取得所有學期"""
    semesters = execute_query(
        'SELECT DISTINCT semester FROM courses WHERE semester IS NOT NULL ORDER BY semester DESC',
        fetch=True
    )
    
    semester_list = [s['semester'] for s in semesters]
    return jsonify({'success': True, 'semesters': semester_list})

# ========================================
# API: 搜尋課程
# ========================================
@app.route('/api/courses', methods=['GET'])
def search_courses():
    """搜尋課程"""
    keyword = request.args.get('keyword', '')
    semester = request.args.get('semester', '')
    department = request.args.get('department', '')
    grade = request.args.get('grade', '')
    course_type = request.args.get('type', '')
    weekday = request.args.get('weekday', '')
    period = request.args.get('period', '')
    degree = request.args.get('degree', '')
    category = request.args.get('category', '')
    
    # 建立查詢
    query = 'SELECT * FROM courses WHERE 1=1'
    params = []
    
    if keyword:
        query += ' AND (course_name LIKE ? OR instructor LIKE ? OR classroom LIKE ?)'
        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
    
    if semester:
        query += ' AND semester = ?'
        params.append(semester)
    
    if department:
        query += ' AND department = ?'
        params.append(department)
    
    if grade:
        query += ' AND grade = ?'
        params.append(grade)
    
    if course_type:
        query += ' AND course_type = ?'
        params.append(course_type)
    
    # 星期篩選
    if weekday:
        weekdays = weekday.split(',')
        if USE_POSTGRES:
            weekday_conditions = ' OR '.join(['weekday = %s' for _ in weekdays])
        else:
            weekday_conditions = ' OR '.join(['weekday = ?' for _ in weekdays])
        query += f' AND ({weekday_conditions})'
        params.extend(weekdays)
    
    # 節次篩選
    if period:
        periods = period.split(',')
        period_conditions = []
        for p in periods:
            if USE_POSTGRES:
                period_conditions.append("(',' || period || ',' LIKE %s)")
            else:
                period_conditions.append("(',' || period || ',' LIKE ?)")
            params.append(f'%,{p},%')
        query += f' AND ({" OR ".join(period_conditions)})'
    
    # 學制篩選
    if degree:
        degrees = degree.split(',')
        degree_conditions = []
        for d in degrees:
            if d == '四技':
                degree_conditions.append("SUBSTR(course_code, 3, 2) = '14'")
            elif d == '二技':
                degree_conditions.append("SUBSTR(course_code, 3, 2) = '12'")
            elif d == '二技(三年)' or d == '二技(二年)':
                degree_conditions.append("(SUBSTR(course_code, 3, 2) = '33' OR SUBSTR(course_code, 3, 2) = '23')")
            elif d == '碩士班':
                degree_conditions.append("(SUBSTR(course_code, 3, 2) = '16' OR SUBSTR(course_code, 3, 2) = '46' OR SUBSTR(course_code, 3, 2) = '86')")
            elif d == '博士班':
                degree_conditions.append("(SUBSTR(course_code, 3, 2) = '17' OR SUBSTR(course_code, 3, 2) = '87')")
            elif d == '學士後系':
                degree_conditions.append("SUBSTR(course_code, 3, 2) = '19'")
            elif d == '學士後多元專長':
                degree_conditions.append("SUBSTR(course_code, 3, 2) = '15'")
            elif d == '學士後學位學程':
                degree_conditions.append("SUBSTR(course_code, 3, 2) = '18'")
        if degree_conditions:
            query += f' AND ({" OR ".join(degree_conditions)})'
    
    # 課程內容分類篩選
    if category:
        categories = category.split(',')
        category_conditions = []
        for c in categories:
            if c == '跨校':
                category_conditions.append("remarks LIKE '%跨校%'")
            elif c == '跨域課程':
                category_conditions.append("remarks LIKE '%跨域%'")
            elif c == '全英語授課':
                category_conditions.append("(remarks LIKE '%全英語%' OR remarks LIKE '%全英文%')")
            elif c == 'EMI全英語授課':
                category_conditions.append("remarks LIKE '%EMI%'")
            elif c == '同步遠距教學':
                category_conditions.append("remarks LIKE '%同步遠距%'")
            elif c == '非同步遠距教學':
                category_conditions.append("remarks LIKE '%非同步遠距%'")
            elif c == '混合式遠距教學':
                category_conditions.append("remarks LIKE '%混合式遠距%'")
            elif c == '遠距教學課程':
                category_conditions.append("remarks LIKE '%遠距教學%'")
            elif c == '遠距輔助課程':
                category_conditions.append("remarks LIKE '%遠距輔助%'")
        if category_conditions:
            query += f' AND ({" OR ".join(category_conditions)})'
    
    query += ' ORDER BY semester DESC, course_code'
    
    courses = execute_query(query, params, fetch=True)
    
    return jsonify({
        'success': True,
        'items': courses,
        'count': len(courses)
    })

# ========================================
# API: 加入收藏/選課
# ========================================
@app.route('/api/enroll', methods=['POST'])
def enroll_course():
    """加入收藏或選課"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '請先登入'})
    
    data = request.json
    course_id = data.get('course_id')
    status = data.get('status', 'enrolled')
    
    if not course_id:
        return jsonify({'success': False, 'message': '缺少課程ID'})
    
    existing = execute_query(
        'SELECT * FROM enrollments WHERE user_id = ? AND course_id = ?',
        (session['user_id'], course_id), fetchone=True
    )
    
    if existing:
        execute_query(
            'UPDATE enrollments SET status = ? WHERE user_id = ? AND course_id = ?',
            (status, session['user_id'], course_id)
        )
        message = '更新成功'
    else:
        execute_query(
            'INSERT INTO enrollments (user_id, course_id, status) VALUES (?, ?, ?)',
            (session['user_id'], course_id, status)
        )
        message = '加入成功'
    
    return jsonify({'success': True, 'message': message})

# ========================================
# API: 取得收藏/預選清單
# ========================================
@app.route('/api/enrollments', methods=['GET'])
def get_enrollments():
    """取得使用者的收藏和預選課程"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '請先登入'})
    
    status = request.args.get('status', '')
    
    if status:
        query = '''
            SELECT e.id as enrollment_id, e.status, c.* 
            FROM enrollments e 
            JOIN courses c ON e.course_id = c.id 
            WHERE e.user_id = ? AND e.status = ?
            ORDER BY c.semester DESC, c.course_code
        '''
        enrollments = execute_query(query, (session['user_id'], status), fetch=True)
    else:
        query = '''
            SELECT e.id as enrollment_id, e.status, c.* 
            FROM enrollments e 
            JOIN courses c ON e.course_id = c.id 
            WHERE e.user_id = ?
            ORDER BY c.semester DESC, c.course_code
        '''
        enrollments = execute_query(query, (session['user_id'],), fetch=True)
    
    return jsonify({
        'success': True,
        'items': enrollments,
        'count': len(enrollments)
    })

# ========================================
# API: 刪除收藏/預選
# ========================================
@app.route('/api/enroll/<int:enrollment_id>', methods=['DELETE'])
def delete_enrollment(enrollment_id):
    """刪除收藏或預選"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '請先登入'})
    
    execute_query(
        'DELETE FROM enrollments WHERE id = ? AND user_id = ?',
        (enrollment_id, session['user_id'])
    )
    
    return jsonify({'success': True, 'message': '刪除成功'})

# ========================================
# API: 取得單一課程
# ========================================
@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """取得單一課程資料"""
    course = execute_query(
        'SELECT * FROM courses WHERE id = ?',
        (course_id,), fetchone=True
    )
    
    if course:
        return jsonify({'success': True, 'course': course})
    else:
        return jsonify({'success': False, 'message': '課程不存在'})

# ========================================
# API: 新增課程 (管理者)
# ========================================
@app.route('/api/courses', methods=['POST'])
def add_course():
    """新增課程"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    data = request.json
    
    day_time = ''
    weekday = data.get('weekday', '')
    period = data.get('period', '')
    if weekday:
        day_map = {'1': '週一', '2': '週二', '3': '週三', '4': '週四', 
                   '5': '週五', '6': '週六', '7': '週日'}
        day_str = day_map.get(str(weekday), '')
        if day_str and period:
            day_time = f"{day_str} {period.replace(',', '-')}"
        elif day_str:
            day_time = day_str
    
    execute_query('''
        INSERT INTO courses (semester, department, grade, course_code, course_name, 
                           instructor, credits, course_type, classroom, day_time, 
                           weekday, period, capacity, class_group, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('semester', ''),
        data.get('department', ''),
        data.get('grade', ''),
        data.get('course_code', ''),
        data.get('course_name', ''),
        data.get('instructor', ''),
        data.get('credits', 0),
        data.get('course_type', ''),
        data.get('classroom', ''),
        day_time,
        weekday,
        period,
        data.get('capacity', 60),
        data.get('class_group', ''),
        data.get('remarks', '')
    ))
    
    return jsonify({'success': True, 'message': '新增成功'})

# ========================================
# API: 更新課程 (管理者)
# ========================================
@app.route('/api/courses/<int:course_id>', methods=['PUT'])
def update_course(course_id):
    """更新課程"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    data = request.json
    
    day_time = ''
    weekday = data.get('weekday', '')
    period = data.get('period', '')
    if weekday:
        day_map = {'1': '週一', '2': '週二', '3': '週三', '4': '週四', 
                   '5': '週五', '6': '週六', '7': '週日'}
        day_str = day_map.get(str(weekday), '')
        if day_str and period:
            day_time = f"{day_str} {period.replace(',', '-')}"
        elif day_str:
            day_time = day_str
    
    execute_query('''
        UPDATE courses SET 
            semester = ?, department = ?, grade = ?, course_code = ?, course_name = ?,
            instructor = ?, credits = ?, course_type = ?, classroom = ?, day_time = ?,
            weekday = ?, period = ?, capacity = ?, class_group = ?, remarks = ?
        WHERE id = ?
    ''', (
        data.get('semester', ''),
        data.get('department', ''),
        data.get('grade', ''),
        data.get('course_code', ''),
        data.get('course_name', ''),
        data.get('instructor', ''),
        data.get('credits', 0),
        data.get('course_type', ''),
        data.get('classroom', ''),
        day_time,
        weekday,
        period,
        data.get('capacity', 60),
        data.get('class_group', ''),
        data.get('remarks', ''),
        course_id
    ))
    
    return jsonify({'success': True, 'message': '更新成功'})

# ========================================
# API: 刪除課程 (管理者)
# ========================================
@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    """刪除課程"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    execute_query('DELETE FROM courses WHERE id = ?', (course_id,))
    execute_query('DELETE FROM enrollments WHERE course_id = ?', (course_id,))
    
    return jsonify({'success': True, 'message': '刪除成功'})

# ========================================
# API: 取得所有使用者 (管理者)
# ========================================
@app.route('/api/users', methods=['GET'])
def get_users():
    """取得所有使用者"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    users = execute_query(
        "SELECT id, username, role, name, student_id, department, class_name, phone, email, avatar FROM users",
        fetch=True
    )
    
    # 分成學生和管理員
    students = [u for u in users if u['role'] == 'student']
    admins = [u for u in users if u['role'] == 'admin']
    
    return jsonify({
        'success': True,
        'students': students,
        'admins': admins,
        'users': users
    })

# ========================================
# API: 新增使用者 (管理者)
# ========================================
@app.route('/api/users', methods=['POST'])
def create_user():
    """新增使用者"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    data = request.json
    username = data.get('username', '')  # ID/學號
    password = data.get('password', '')
    name = data.get('name', '')
    role = data.get('role', 'student')
    phone = data.get('phone', '')
    avatar = data.get('avatar', '🐱')
    
    if not username or not password:
        return jsonify({'success': False, 'message': '請填寫必要欄位'})
    
    # 檢查是否已存在
    existing = execute_query(
        'SELECT id FROM users WHERE username = ?',
        (username,), fetchone=True
    )
    
    if existing:
        return jsonify({'success': False, 'message': '此帳號已存在'})
    
    execute_query('''
        INSERT INTO users (username, password, name, role, student_id, phone, avatar)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, password, name, role, username, phone, avatar))
    
    return jsonify({'success': True, 'message': '新增成功'})

# ========================================
# API: 取得單一使用者 (管理者)
# ========================================
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """取得單一使用者"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    user = execute_query(
        "SELECT id, username, password, role, name, student_id, department, class_name, phone, email, avatar FROM users WHERE id = ?",
        (user_id,), fetchone=True
    )
    
    if user:
        return jsonify({'success': True, 'user': user})
    else:
        return jsonify({'success': False, 'message': '找不到使用者'})

# ========================================
# API: 更新使用者 (管理者)
# ========================================
@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """更新使用者資料"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    data = request.json
    
    execute_query('''
        UPDATE users SET 
            name = ?, student_id = ?, department = ?, class_name = ?, 
            username = ?, phone = ?, email = ?, avatar = ?
        WHERE id = ?
    ''', (
        data.get('name', ''),
        data.get('student_id', ''),
        data.get('department', ''),
        data.get('class_name', ''),
        data.get('username', ''),
        data.get('phone', ''),
        data.get('email', ''),
        data.get('avatar', '🐱'),
        user_id
    ))
    
    return jsonify({'success': True, 'message': '更新成功'})

# ========================================
# API: 刪除使用者 (管理者)
# ========================================
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """刪除使用者"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    execute_query('DELETE FROM enrollments WHERE user_id = ?', (user_id,))
    execute_query('DELETE FROM users WHERE id = ?', (user_id,))
    
    return jsonify({'success': True, 'message': '刪除成功'})

# ========================================
# API: 重設密碼為預設 (管理者)
# ========================================
@app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
def reset_user_password(user_id):
    """重設使用者密碼為預設值"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    default_password = 'pass123'
    
    execute_query(
        'UPDATE users SET password = ? WHERE id = ?',
        (default_password, user_id)
    )
    
    return jsonify({'success': True, 'message': f'密碼已重設為預設值: {default_password}'})

# ========================================
# API: 匯入課程 (管理者)
# ========================================
@app.route('/api/import-courses', methods=['POST'])
def import_courses():
    """匯入課程 Excel 檔案"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '沒有選擇檔案'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '沒有選擇檔案'})
    
    semester = request.form.get('semester', '')
    if not semester:
        return jsonify({'success': False, 'message': '請指定學期'})
    
    try:
        if file.filename.endswith('.xls'):
            df = pd.read_excel(file, header=3, engine='xlrd')
        else:
            df = pd.read_excel(file, header=3)
        
        imported_count = 0
        
        for idx, row in df.iterrows():
            if idx == 0:
                continue
            
            try:
                course_code = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ''
                if not course_code or course_code == 'nan':
                    continue
                
                dept_code = str(row.iloc[4]) if pd.notna(row.iloc[4]) else ''
                department = get_department_name(dept_code)
                
                grade = str(row.iloc[7]) if pd.notna(row.iloc[7]) else ''
                class_group = str(row.iloc[8]) if pd.notna(row.iloc[8]) else ''
                course_name = str(row.iloc[9]) if pd.notna(row.iloc[9]) else ''
                course_name_en = str(row.iloc[10]) if pd.notna(row.iloc[10]) else ''
                instructor = str(row.iloc[11]) if pd.notna(row.iloc[11]) else ''
                capacity = int(row.iloc[12]) if pd.notna(row.iloc[12]) else 0
                credits = float(row.iloc[15]) if pd.notna(row.iloc[15]) else 0
                course_type = str(row.iloc[19]) if pd.notna(row.iloc[19]) else ''
                classroom = str(row.iloc[20]) if pd.notna(row.iloc[20]) else ''
                weekday = str(row.iloc[21]) if pd.notna(row.iloc[21]) else ''
                period = str(row.iloc[22]) if pd.notna(row.iloc[22]) else ''
                remarks = str(row.iloc[23]) if pd.notna(row.iloc[23]) else ''
                course_summary = str(row.iloc[24]) if pd.notna(row.iloc[24]) else ''
                
                day_map = {'1': '週一', '2': '週二', '3': '週三', '4': '週四', 
                           '5': '週五', '6': '週六', '7': '週日'}
                day_time = ''
                if weekday:
                    day_str = day_map.get(str(int(float(weekday))), '')
                    if day_str:
                        day_time = f"{day_str} {period}"
                    weekday = str(int(float(weekday)))
                
                existing = execute_query(
                    'SELECT id FROM courses WHERE semester = ? AND course_code = ? AND class_group = ?',
                    (semester, course_code, class_group), fetchone=True
                )
                
                if existing:
                    execute_query('''
                        UPDATE courses SET 
                            department = ?, grade = ?, course_name = ?, course_name_en = ?,
                            instructor = ?, credits = ?, course_type = ?, classroom = ?,
                            day_time = ?, weekday = ?, period = ?, capacity = ?, 
                            remarks = ?, course_summary = ?
                        WHERE id = ?
                    ''', (
                        department, grade, course_name, course_name_en,
                        instructor, credits, course_type, classroom,
                        day_time, weekday, period, capacity,
                        remarks, course_summary, existing['id']
                    ))
                else:
                    execute_query('''
                        INSERT INTO courses (semester, department, grade, course_code, course_name,
                                           course_name_en, instructor, credits, course_type, classroom,
                                           day_time, weekday, period, capacity, class_group, 
                                           remarks, course_summary)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        semester, department, grade, course_code, course_name,
                        course_name_en, instructor, credits, course_type, classroom,
                        day_time, weekday, period, capacity, class_group,
                        remarks, course_summary
                    ))
                
                imported_count += 1
                
            except Exception as e:
                print(f"Row {idx} error: {e}")
                continue
        
        return jsonify({
            'success': True, 
            'message': f'成功匯入 {imported_count} 筆課程',
            'count': imported_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'匯入失敗: {str(e)}'})

def get_department_name(dept_code):
    """根據系所代碼取得系所名稱"""
    dept_map = {
        '11120': '嬰幼兒保育系',
        '11140': '嬰幼兒保育系',
        '11170': '護理系博士班',
        '21120': '高齡健康照護系',
        '21140': '高齡健康照護系',
        '24120': '長期照護系',
        '24140': '長期照護系',
        '24150': '學士後多元專長',
        '30860': '健康事業管理系',
        '31140': '健康事業管理系',
        '31180': '學士後學位學程',
        '33140': '護理系',
        '33160': '護理系碩士班',
        '43160': '人工智慧與健康大數據研究所',
        '51140': '語言治療與聽力學系',
        '51160': '語言治療與聽力學系碩士班',
        '90100': '通識教育中心',
        '90200': '體育室',
    }
    
    if dept_code in dept_map:
        return dept_map[dept_code]
    
    prefix4 = dept_code[:4] if len(dept_code) >= 4 else dept_code
    for key, value in dept_map.items():
        if key.startswith(prefix4):
            return value
    
    return dept_code

# ========================================
# 啟動應用程式
# ========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
