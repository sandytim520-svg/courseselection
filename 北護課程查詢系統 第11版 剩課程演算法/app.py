# ==========================================================
# 北護課程查詢系統 - Flask後端程式 (完整版)
# 支援從Excel匯入的真實課程資料
# ==========================================================

from flask import Flask, request, jsonify, session, render_template, redirect
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'ntunhs_course_system_2024_secret_key'

# 資料庫檔案路徑
DATABASE = 'database.db'

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
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                       (username, password)).fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        return jsonify({
            'success': True,
            'message': '登入成功',
            'role': user['role'],
            'user_id': user['id'],
            'username': user['username']
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
# API: 取得系所列表
# ========================================
@app.route('/api/departments', methods=['GET'])
def get_departments():
    """取得所有系所"""
    conn = get_db()
    departments = conn.execute('SELECT DISTINCT department FROM courses WHERE department IS NOT NULL ORDER BY department').fetchall()
    conn.close()
    
    dept_list = [d['department'] for d in departments]
    return jsonify({'success': True, 'departments': dept_list})

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
    
    # 新增:星期篩選 - 使用 weekday 欄位
    if weekday:
        weekdays = weekday.split(',')
        weekday_conditions = ' OR '.join(['weekday = ?' for _ in weekdays])
        query += f' AND ({weekday_conditions})'
        params.extend(weekdays)
    
    # 新增:節次篩選 - 精確匹配 period 欄位中的節次
    if period:
        periods = period.split(',')
        period_conditions = []
        for p in periods:
            # 匹配節次：可能是 "3" 或 "3,4" 或 "2,3,4" 等格式
            # 需要精確匹配數字，避免 "13" 匹配到 "1"
            period_conditions.append("(',' || period || ',' LIKE ?)")
            params.append(f'%,{p},%')
        query += f' AND ({" OR ".join(period_conditions)})'
    
    # 新增:學制篩選 - 根據 course_code 第3-4碼判斷
    # 14=四技, 12=二技, 33/23=二技(三年), 16/46/86=碩士班, 17/87=博士班
    # 19=學士後系, 15=學士後多元專長, 18=學士後學位學程
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
    
    # 新增:課程內容分類篩選 - 根據 remarks 欄位判斷
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
    
    conn = get_db()
    courses = conn.execute(query, params).fetchall()
    conn.close()
    
    courses_list = [dict(course) for course in courses]
    
    return jsonify({
        'success': True,
        'items': courses_list,
        'count': len(courses_list)
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
    status = data.get('status', 'enrolled')  # 'favorite' 或 'enrolled'
    
    if not course_id:
        return jsonify({'success': False, 'message': '缺少課程ID'})
    
    conn = get_db()
    c = conn.cursor()
    
    # 檢查是否已存在
    existing = c.execute('SELECT * FROM enrollments WHERE user_id = ? AND course_id = ?',
                        (session['user_id'], course_id)).fetchone()
    
    if existing:
        # 更新狀態
        c.execute('UPDATE enrollments SET status = ? WHERE user_id = ? AND course_id = ?',
                 (status, session['user_id'], course_id))
        message = '更新成功'
    else:
        # 新增記錄
        c.execute('INSERT INTO enrollments (user_id, course_id, status) VALUES (?, ?, ?)',
                 (session['user_id'], course_id, status))
        message = '加入成功'
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': message})

# ========================================
# API: 移除課程
# ========================================
@app.route('/api/enroll/<int:enrollment_id>', methods=['DELETE'])
def remove_enrollment(enrollment_id):
    """移除收藏或選課"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '請先登入'})
    
    conn = get_db()
    c = conn.cursor()
    
    # 確認是本人的記錄
    enrollment = c.execute('SELECT * FROM enrollments WHERE id = ? AND user_id = ?',
                          (enrollment_id, session['user_id'])).fetchone()
    
    if not enrollment:
        conn.close()
        return jsonify({'success': False, 'message': '找不到此記錄'})
    
    # 刪除記錄
    c.execute('DELETE FROM enrollments WHERE id = ?', (enrollment_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '移除成功'})

# ========================================
# API: 取得我的收藏/預選課程
# ========================================
@app.route('/api/my-courses', methods=['GET'])
def get_my_courses():
    """取得使用者的課程列表"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '請先登入'})
    
    status = request.args.get('status', 'favorite')
    
    conn = get_db()
    courses = conn.execute('''
        SELECT e.id as enrollment_id, c.*, e.status, e.enrolled_at
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.user_id = ? AND e.status = ?
        ORDER BY e.enrolled_at DESC
    ''', (session['user_id'], status)).fetchall()
    conn.close()
    
    courses_list = [dict(course) for course in courses]
    
    return jsonify({
        'success': True,
        'items': courses_list,
        'count': len(courses_list)
    })

# ========================================
# API: 取得所有課程 (管理者)
# ========================================
@app.route('/api/all-courses', methods=['GET'])
def get_all_courses():
    """取得所有課程 (管理者)"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    semester = request.args.get('semester', '')
    department = request.args.get('department', '')
    
    query = 'SELECT * FROM courses WHERE 1=1'
    params = []
    
    if semester:
        query += ' AND semester = ?'
        params.append(semester)
    
    if department:
        query += ' AND department = ?'
        params.append(department)
    
    query += ' ORDER BY semester DESC, department, course_code'
    
    conn = get_db()
    courses = conn.execute(query, params).fetchall()
    conn.close()
    
    courses_list = [dict(course) for course in courses]
    
    return jsonify({
        'success': True,
        'courses': courses_list,
        'count': len(courses_list)
    })

# ========================================
# API: 取得使用者列表 (管理者)
# ========================================
@app.route('/api/users', methods=['GET'])
def get_users():
    """取得所有使用者"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    conn = get_db()
    users = conn.execute('SELECT id, username, role, created_at FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    
    users_list = [dict(user) for user in users]
    
    return jsonify({'success': True, 'users': users_list})

# ========================================
# API: 新增使用者 (管理者)
# ========================================
@app.route('/api/users', methods=['POST'])
def add_user():
    """新增使用者"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    data = request.json
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                  (data.get('username'), data.get('password'), 
                   data.get('role', 'student')))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '帳號新增成功'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'message': '帳號已存在'})

# ========================================
# API: 刪除使用者 (管理者)
# ========================================
@app.route('/api/users/<username>', methods=['DELETE'])
def delete_user(username):
    """刪除使用者"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    # 不能刪除自己
    if username == session.get('username'):
        return jsonify({'success': False, 'message': '不能刪除自己的帳號'})
    
    conn = get_db()
    c = conn.cursor()
    
    # 取得使用者ID
    user = c.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': '使用者不存在'})
    
    # 刪除選課記錄
    c.execute('DELETE FROM enrollments WHERE user_id = ?', (user['id'],))
    # 刪除使用者
    c.execute('DELETE FROM users WHERE username = ?', (username,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '帳號刪除成功'})

# ========================================
# API: 取得學期列表
# ========================================
@app.route('/api/semesters', methods=['GET'])
def get_semesters():
    """取得所有學期"""
    conn = get_db()
    semesters = conn.execute('SELECT DISTINCT semester FROM courses WHERE semester IS NOT NULL ORDER BY semester DESC').fetchall()
    conn.close()
    
    semester_list = [s['semester'] for s in semesters]
    return jsonify({'success': True, 'semesters': semester_list})

# ========================================
# API: 取得統計資料 (管理者)
# ========================================
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """取得系統統計資料"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    conn = get_db()
    
    # 總課程數
    total_courses = conn.execute('SELECT COUNT(*) as count FROM courses').fetchone()['count']
    
    # 總使用者數
    total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    
    # 各學期課程數
    semester_stats = conn.execute('''
        SELECT semester, COUNT(*) as count 
        FROM courses 
        GROUP BY semester 
        ORDER BY semester DESC
    ''').fetchall()
    
    # 各系所課程數
    dept_stats = conn.execute('''
        SELECT department, COUNT(*) as count 
        FROM courses 
        GROUP BY department 
        ORDER BY count DESC 
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'success': True,
        'total_courses': total_courses,
        'total_users': total_users,
        'semester_stats': [dict(s) for s in semester_stats],
        'dept_stats': [dict(d) for d in dept_stats]
    })

# ========================================
# API: 新增課程 (管理者)
# ========================================
@app.route('/api/courses', methods=['POST'])
def add_course():
    """新增課程"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    data = request.json
    
    # 驗證必填欄位
    if not data.get('course_name') or not data.get('semester'):
        return jsonify({'success': False, 'message': '請填寫必填欄位'})
    
    # 組合時間資訊
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
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO courses (
                semester, department, grade, course_code, course_name,
                instructor, credits, course_type, classroom, day_time,
                weekday, period, capacity, class_group, remarks
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('semester', ''),
            data.get('department', ''),
            data.get('grade', ''),
            data.get('course_code', ''),
            data.get('course_name', ''),
            data.get('instructor', ''),
            float(data.get('credits', 0)),
            data.get('course_type', ''),
            data.get('classroom', ''),
            day_time,
            weekday,
            period,
            int(data.get('capacity', 60)),
            data.get('class_group', ''),
            data.get('remarks', '')
        ))
        conn.commit()
        course_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'message': '課程新增成功', 'id': course_id})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'新增失敗: {str(e)}'})

# ========================================
# API: 取得單一課程 (用於編輯)
# ========================================
@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """取得單一課程資料"""
    conn = get_db()
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    conn.close()
    
    if course:
        return jsonify({'success': True, 'course': dict(course)})
    else:
        return jsonify({'success': False, 'message': '課程不存在'})

# ========================================
# API: 更新課程 (管理者)
# ========================================
@app.route('/api/courses/<int:course_id>', methods=['PUT'])
def update_course(course_id):
    """更新課程"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    data = request.json
    
    # 組合時間資訊
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
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''
            UPDATE courses SET
                semester = ?, department = ?, grade = ?, course_code = ?,
                course_name = ?, instructor = ?, credits = ?, course_type = ?,
                classroom = ?, day_time = ?, weekday = ?, period = ?,
                capacity = ?, class_group = ?, remarks = ?
            WHERE id = ?
        ''', (
            data.get('semester', ''),
            data.get('department', ''),
            data.get('grade', ''),
            data.get('course_code', ''),
            data.get('course_name', ''),
            data.get('instructor', ''),
            float(data.get('credits', 0)),
            data.get('course_type', ''),
            data.get('classroom', ''),
            day_time,
            weekday,
            period,
            int(data.get('capacity', 60)),
            data.get('class_group', ''),
            data.get('remarks', ''),
            course_id
        ))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '課程更新成功'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'更新失敗: {str(e)}'})

# ========================================
# API: 刪除課程 (管理者)
# ========================================
@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    """刪除課程"""
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': '權限不足'})
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        # 先刪除相關的選課記錄
        c.execute('DELETE FROM enrollments WHERE course_id = ?', (course_id,))
        # 刪除課程
        c.execute('DELETE FROM courses WHERE id = ?', (course_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '課程刪除成功'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'刪除失敗: {str(e)}'})

# ========================================
# 主程式入口
# ========================================
if __name__ == '__main__':
    print('=' * 60)
    print('🚀 北護課程查詢系統啟動中...')
    print('=' * 60)
    
    # 檢查資料庫是否存在
    if not os.path.exists(DATABASE):
        print('❌ 資料庫不存在！請先執行 create_database.py')
        exit(1)
    
    # 顯示資料庫統計
    conn = get_db()
    course_count = conn.execute('SELECT COUNT(*) as count FROM courses').fetchone()['count']
    user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    conn.close()
    
    print(f'📊 資料庫統計:')
    print(f'   課程數: {course_count} 筆')
    print(f'   使用者: {user_count} 人')
    print('📍 本地網址: http://127.0.0.1:5000')
    print('📝 測試帳號:')
    print('   學生 - student1 / pass123')
    print('   管理員 - admin / admin123')
    print('=' * 60)
    print()
    
    # 啟動Flask應用
    app.run(host='0.0.0.0', port=5000, debug=True)