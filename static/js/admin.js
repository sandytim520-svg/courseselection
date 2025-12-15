/* ==========================================================
   北護課程查詢系統 - 管理者頁面JavaScript
   功能: 課程管理、匯入課程、帳號管理
   ========================================================== */

// ========================================
// 全域變數
// ========================================
let currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
let editingCourseId = null;

// 篩選面板變數
let adminCurrentFilterPanel = null;
let adminSelectedFilters = {
    weekday: [],
    period: [],
    degree: [],
    category: []
};

// ========================================
// 頁面載入時執行
// ========================================
window.onload = function() {
    console.log('✅ 管理者頁面載入完成');
    loadDepartments();
    loadAccounts();
    loadAdminProfile();
    
    // 設置表單提交事件
    document.getElementById('courseForm').addEventListener('submit', handleCourseSubmit);
    document.getElementById('accountForm').addEventListener('submit', handleAccountSubmit);
};

// ========================================
// 功能：載入管理者個人資料
// ========================================
async function loadAdminProfile() {
    try {
        const response = await fetch('/api/profile');
        const data = await response.json();
        
        if (data.success && data.profile) {
            const profile = data.profile;
            // 更新 sidebar 的頭貼和姓名
            document.getElementById('adminAvatar').textContent = profile.avatar || '🧑‍💼';
            document.getElementById('adminName').textContent = profile.name || '管理員';
            console.log('✅ 管理者資料載入成功');
        }
    } catch (error) {
        console.error('❌ 載入管理者資料失敗:', error);
    }
}

// ========================================
// 功能：載入系所列表
// ========================================
async function loadDepartments() {
    try {
        const response = await fetch('/api/departments');
        const data = await response.json();
        
        if (data.success && data.departments) {
            const select = document.getElementById('adminDepartmentSelect');
            data.departments.forEach(dept => {
                const option = document.createElement('option');
                option.value = dept;
                option.textContent = dept;
                select.appendChild(option);
            });
            console.log('✅ 系所列表載入成功');
        }
    } catch (error) {
        console.error('❌ 載入系所失敗:', error);
    }
}

// ========================================
// 功能：切換頁面Section
// ========================================
function showSection(section) {
    // 隱藏所有section
    document.querySelectorAll('.content-section').forEach(s => {
        s.classList.remove('active');
    });
    
    // 移除所有nav-item的active
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 顯示選中的section
    const sectionMap = {
        'courses': 'coursesSection',
        'import': 'importSection',
        'accounts': 'accountsSection'
    };
    
    const targetSection = document.getElementById(sectionMap[section]);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // 標記選中的nav-item
    if (event && event.target) {
        const navItem = event.target.closest('.nav-item');
        if (navItem) {
            navItem.classList.add('active');
        }
    }
    
    // 載入對應資料
    if (section === 'accounts') loadAccounts();
    
    console.log('📄 切換到:', section);
}

// ========================================
// 功能：搜尋課程
// ========================================
async function adminSearchCourses() {
    const keyword = document.getElementById('adminKeywordInput').value.trim();
    const semester = document.getElementById('adminSemesterSelect').value;
    const department = document.getElementById('adminDepartmentSelect').value;
    const grade = document.getElementById('adminGradeSelect').value;
    const type = document.getElementById('adminTypeSelect').value;
    
    // 建立查詢參數
    let params = new URLSearchParams();
    if (keyword) params.append('keyword', keyword);
    if (semester) params.append('semester', semester);
    if (department) params.append('department', department);
    if (grade) params.append('grade', grade);
    if (type) params.append('type', type);
    
    // 添加篩選面板的參數
    if (adminSelectedFilters.weekday.length > 0) {
        params.append('weekday', adminSelectedFilters.weekday.join(','));
    }
    if (adminSelectedFilters.period.length > 0) {
        params.append('period', adminSelectedFilters.period.join(','));
    }
    if (adminSelectedFilters.degree.length > 0) {
        params.append('degree', adminSelectedFilters.degree.join(','));
    }
    if (adminSelectedFilters.category.length > 0) {
        params.append('category', adminSelectedFilters.category.join(','));
    }
    
    console.log('🔍 管理者搜尋參數:', Object.fromEntries(params));
    
    try {
        const response = await fetch(`/api/courses?${params}`);
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ 找到 ${data.count} 筆課程`);
            displayAdminResults(data.items);
        } else {
            displayAdminResults([]);
        }
    } catch (error) {
        console.error('❌ 搜尋失敗:', error);
        alert('搜尋失敗，請稍後再試');
    }
}

// ========================================
// 功能：顯示課程列表（管理者）
// ========================================
function displayAdminResults(courses) {
    const container = document.getElementById('adminCoursesResults');
    
    if (!courses || courses.length === 0) {
        container.innerHTML = '<p class="no-results">沒有找到符合的課程</p>';
        return;
    }
    
    let html = `
        <table class="results-table">
            <thead>
                <tr>
                    <th>學期</th>
                    <th>系所</th>
                    <th>年級</th>          
                    <th>課程名稱</th>
                    <th>授課教師</th>
                    <th>學分</th>
                    <th>課別</th>
                    <th>教室</th>
                    <th>星期</th>
                    <th>節次</th>
                    <th>大綱</th>
                    <th>編輯</th>
                    <th>刪除</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    courses.forEach(course => {
        // 解析星期
        const dayMap = {'1': '一', '2': '二', '3': '三', '4': '四', 
                       '5': '五', '6': '六', '7': '日'};
        let weekdayDisplay = '';
        if (course.weekday) {
            weekdayDisplay = dayMap[course.weekday] || '';
        } else if (course.day_time) {
            const match = course.day_time.match(/週([一二三四五六日])/);
            if (match) weekdayDisplay = match[1];
        }
        
        // 解析節次
        let periodDisplay = course.period || '';
        if (!periodDisplay && course.day_time) {
            const match = course.day_time.match(/(\d+[-,\d]*)/);
            if (match) periodDisplay = match[1];
        }
        
        html += `
            <tr>
                <td>${course.semester || ''}</td>
                <td>${course.department || ''}</td>
                <td>${course.grade || ''}</td>           
                <td>${course.course_name || ''}</td>
                <td>${course.instructor || ''}</td>
                <td>${course.credits || ''}</td>
                <td>${course.course_type || ''}</td>
                <td>${course.classroom || ''}</td>
                <td>${weekdayDisplay}</td>
                <td>${periodDisplay}</td>
                <td>
                    <button class="btn-icon btn-outline" onclick="showCourseInfo(${course.id})" title="課程資訊">•••</button>
                </td>
                <td>
                    <button class="btn-icon btn-edit" onclick="editCourse(${course.id})" title="編輯">✎</button>
                </td>
                <td>
                    <button class="btn-icon btn-trash" onclick="deleteCourse(${course.id})" title="刪除">🗑</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// ========================================
// 功能：顯示課程資訊 (大綱) - 管理者版
// ========================================
async function showCourseInfo(courseId) {
    try {
        const response = await fetch(`/api/courses/${courseId}`);
        const data = await response.json();
        
        if (data.success && data.course) {
            const course = data.course;
            
            // 格式化時間顯示
            let timeDisplay = '';
            if (course.weekday) {
                const dayMap = {'1': '週一', '2': '週二', '3': '週三', '4': '週四', 
                               '5': '週五', '6': '週六', '7': '週日'};
                timeDisplay = dayMap[course.weekday] || '';
                if (course.period) {
                    const periodTimes = {
                        '1': '08:10~09:00', '2': '09:10~10:00', '3': '10:10~11:00', '4': '11:10~12:00',
                        '5': '12:40~13:30', '6': '13:40~14:30', '7': '14:40~15:30', '8': '15:40~16:30',
                        '9': '16:40~17:30', '10': '17:40~18:30', '11': '18:35~19:25', '12': '19:30~20:20',
                        '13': '20:25~21:15', '14': '21:20~22:10'
                    };
                    const periods = course.period.split(',');
                    if (periods.length > 0) {
                        const startTime = periodTimes[periods[0].trim()] ? periodTimes[periods[0].trim()].split('~')[0] : '';
                        const endTime = periodTimes[periods[periods.length-1].trim()] ? periodTimes[periods[periods.length-1].trim()].split('~')[1] : '';
                        timeDisplay += `，${course.period}節(${startTime}~${endTime})`;
                    }
                }
            } else if (course.day_time) {
                timeDisplay = course.day_time;
            }
            if (course.classroom) {
                timeDisplay += `，${course.classroom}`;
            }
            
            const modalHTML = `
                <div id="courseInfoModal" class="course-info-overlay" onclick="closeCourseInfoModal(event)">
                    <div class="course-info-modal admin-modal" onclick="event.stopPropagation()">
                        <div class="course-info-header admin-header-pink">
                            <h3>課程資訊</h3>
                            <button class="close-btn-x" onclick="closeCourseInfoModal()">✕</button>
                        </div>
                        <div class="course-info-body">
                            <div class="info-grid">
                                <div class="info-cell">
                                    <span class="info-label">學年期</span>
                                    <span class="info-value admin-value">${course.semester || ''}</span>
                                </div>
                                <div class="info-cell">
                                    <span class="info-label">課程代碼</span>
                                    <span class="info-value admin-value">${course.course_code || ''}</span>
                                </div>
                            </div>
                            <div class="info-grid">
                                <div class="info-cell">
                                    <span class="info-label">課程名稱</span>
                                    <span class="info-value admin-value">${course.course_name || ''}</span>
                                </div>
                                <div class="info-cell">
                                    <span class="info-label">授課老師</span>
                                    <span class="info-value admin-value">${course.instructor || ''}</span>
                                </div>
                            </div>
                            <div class="info-grid">
                                <div class="info-cell">
                                    <span class="info-label">學分數</span>
                                    <span class="info-value admin-value">${course.credits || ''}</span>
                                </div>
                                <div class="info-cell">
                                    <span class="info-label">課別名稱</span>
                                    <span class="info-value admin-value">${course.course_type || ''}</span>
                                </div>
                            </div>
                            <div class="info-grid">
                                <div class="info-cell">
                                    <span class="info-label">上課人數</span>
                                    <span class="info-value admin-value">${course.capacity !== null && course.capacity !== undefined ? course.capacity : ''}</span>
                                </div>
                                <div class="info-cell">
                                    <span class="info-label">班組名稱</span>
                                    <span class="info-value admin-value">${course.class_group || ''}</span>
                                </div>
                            </div>
                            <div class="info-grid single">
                                <div class="info-cell full">
                                    <span class="info-label">時間及教室</span>
                                    <span class="info-value admin-value">${timeDisplay || '無'}</span>
                                </div>
                            </div>
                            <div class="info-remarks">
                                <span class="info-label">課程備註</span>
                                <div class="remarks-text admin-remarks">${course.remarks || '無'}</div>
                            </div>
                        </div>
                        <div class="course-info-footer">
                            <button class="btn-close-pink" onclick="closeCourseInfoModal()">關閉</button>
                        </div>
                    </div>
                </div>
            `;
            
            // 移除舊的Modal
            const oldModal = document.getElementById('courseInfoModal');
            if (oldModal) oldModal.remove();
            
            // 添加新Modal
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }
    } catch (error) {
        console.error('❌ 載入課程資訊失敗:', error);
        alert('載入課程資訊失敗');
    }
}

// 關閉課程資訊Modal
function closeCourseInfoModal(event) {
    if (event && event.target.id !== 'courseInfoModal') return;
    const modal = document.getElementById('courseInfoModal');
    if (modal) modal.remove();
}

// ========================================
// 功能：清除搜尋
// ========================================
function adminClearSearch() {
    document.getElementById('adminKeywordInput').value = '';
    document.getElementById('adminSemesterSelect').value = '';
    document.getElementById('adminDepartmentSelect').value = '';
    document.getElementById('adminGradeSelect').value = '';
    document.getElementById('adminTypeSelect').value = '';
    document.getElementById('adminCoursesResults').innerHTML = 
        '<p class="no-results">請輸入搜尋條件查詢課程</p>';
    console.log('🧹 清除搜尋條件');
}

// ========================================
// 功能：開啟新增課程Modal
// ========================================
function openAddCourseModal() {
    editingCourseId = null;
    document.getElementById('courseModalTitle').textContent = '新增課程';
    document.getElementById('courseForm').reset();
    document.getElementById('courseId').value = '';
    document.getElementById('courseModal').classList.add('active');
    console.log('➕ 開啟新增課程視窗');
}

// ========================================
// 功能：關閉課程Modal
// ========================================
function closeCourseModal() {
    document.getElementById('courseModal').classList.remove('active');
    document.getElementById('courseForm').reset();
    editingCourseId = null;
    console.log('✖ 關閉課程視窗');
}

// ========================================
// 功能：編輯課程
// ========================================
async function editCourse(courseId) {
    try {
        const response = await fetch(`/api/courses/${courseId}`);
        const data = await response.json();
        
        if (data.success && data.course) {
            const course = data.course;
            editingCourseId = courseId;
            
            document.getElementById('courseModalTitle').textContent = '編輯課程';
            document.getElementById('courseId').value = courseId;
            document.getElementById('courseSemester').value = course.semester || '';
            document.getElementById('courseCode').value = course.course_code || '';
            document.getElementById('courseCredits').value = course.credits || '';
            document.getElementById('courseName').value = course.course_name || '';
            document.getElementById('courseInstructor').value = course.instructor || '';
            document.getElementById('courseDepartment').value = course.department || '';
            document.getElementById('courseWeekday').value = course.weekday || '';
            document.getElementById('coursePeriod').value = course.period || '';
            document.getElementById('courseLocation').value = course.classroom || '';
            document.getElementById('courseClassGroup').value = course.class_group || '';
            document.getElementById('courseGrade').value = course.grade || '';
            document.getElementById('courseType').value = course.course_type || '';  // 課別
            document.getElementById('courseCapacity').value = course.capacity || 60;
            document.getElementById('courseRemarks').value = course.remarks || '';
            
            document.getElementById('courseModal').classList.add('active');
            console.log('✏️ 載入課程資料:', courseId);
        } else {
            alert('載入課程資料失敗');
        }
    } catch (error) {
        console.error('❌ 載入課程失敗:', error);
        alert('載入課程資料失敗');
    }
}

// ========================================
// 功能：處理課程表單提交
// ========================================
async function handleCourseSubmit(e) {
    e.preventDefault();
    
    const courseData = {
        semester: document.getElementById('courseSemester').value,
        course_code: document.getElementById('courseCode').value,
        credits: document.getElementById('courseCredits').value,
        course_name: document.getElementById('courseName').value,
        instructor: document.getElementById('courseInstructor').value,
        department: document.getElementById('courseDepartment').value,
        weekday: document.getElementById('courseWeekday').value,
        period: document.getElementById('coursePeriod').value,
        classroom: document.getElementById('courseLocation').value,
        class_group: document.getElementById('courseClassGroup').value,
        grade: document.getElementById('courseGrade').value,
        course_type: document.getElementById('courseType').value,  // 課別
        capacity: document.getElementById('courseCapacity').value,
        remarks: document.getElementById('courseRemarks').value
    };
    
    try {
        const url = editingCourseId 
            ? `/api/courses/${editingCourseId}` 
            : '/api/courses';
        const method = editingCourseId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(courseData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✓ ' + result.message);
            closeCourseModal();
            adminSearchCourses(); // 重新搜尋以更新列表
            console.log('✅ 課程儲存成功');
        } else {
            alert('✗ ' + result.message);
        }
    } catch (error) {
        console.error('❌ 儲存課程失敗:', error);
        alert('操作失敗: ' + error.message);
    }
}

// ========================================
// 功能：刪除課程
// ========================================
async function deleteCourse(courseId) {
    if (!confirm('確定要刪除這門課程嗎？')) return;
    
    try {
        const response = await fetch(`/api/courses/${courseId}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            alert('✓ ' + result.message);
            adminSearchCourses(); // 重新搜尋以更新列表
            console.log('✅ 課程刪除成功');
        } else {
            alert('✗ ' + result.message);
        }
    } catch (error) {
        console.error('❌ 刪除課程失敗:', error);
        alert('操作失敗，請稍後再試');
    }
}

// ========================================
// 功能：檔案拖放處理
// ========================================
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('dropZone').classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('dropZone').classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('dropZone').classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
}

// ========================================
// 功能：檔案上傳處理
// ========================================
async function handleFileUpload(file) {
    const statusDiv = document.getElementById('uploadStatus');
    const semesterInput = document.getElementById('importSemester');
    const semester = semesterInput ? semesterInput.value.trim() : '';
    
    // 檢查學期
    if (!semester) {
        statusDiv.className = 'upload-status error';
        statusDiv.textContent = '✗ 請先輸入學期！';
        return;
    }
    
    // 檢查檔案類型
    const validTypes = ['.csv', '.xlsx', '.xls'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!validTypes.includes(fileExt)) {
        statusDiv.className = 'upload-status error';
        statusDiv.textContent = '✗ 檔案格式錯誤！請上傳 CSV 或 Excel 檔案';
        return;
    }
    
    // 檢查檔案大小 (300MB)
    if (file.size > 300 * 1024 * 1024) {
        statusDiv.className = 'upload-status error';
        statusDiv.textContent = '✗ 檔案太大！請上傳小於 300 MB 的檔案';
        return;
    }
    
    // 顯示上傳中
    statusDiv.className = 'upload-status';
    statusDiv.textContent = '⏳ 正在匯入課程資料...';
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('semester', semester);
    
    try {
        const response = await fetch('/api/import-courses', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            statusDiv.className = 'upload-status success';
            statusDiv.textContent = `✓ 成功匯入 ${result.count || 0} 筆課程資料！`;
            console.log('✅ 檔案上傳成功');
            
            // 重新載入學期列表（如果有動態學期選單的話）
            loadSemesters();
        } else {
            statusDiv.className = 'upload-status error';
            statusDiv.textContent = '✗ ' + result.message;
        }
    } catch (error) {
        console.error('❌ 上傳失敗:', error);
        statusDiv.className = 'upload-status error';
        statusDiv.textContent = '✗ 上傳失敗，請稍後再試';
    }
}

// ========================================
// 功能：載入學期列表
// ========================================
async function loadSemesters() {
    try {
        const response = await fetch('/api/semesters');
        const data = await response.json();
        
        if (data.success && data.semesters) {
            const select = document.getElementById('adminSemesterSelect');
            if (select) {
                // 保存當前選擇
                const currentValue = select.value;
                
                // 清空並重新填充
                select.innerHTML = '<option value="">請選擇學期</option>';
                data.semesters.forEach(s => {
                    const option = document.createElement('option');
                    option.value = s;
                    option.textContent = s;
                    select.appendChild(option);
                });
                
                // 恢復選擇
                if (currentValue) select.value = currentValue;
            }
            console.log(`✅ 載入 ${data.semesters.length} 個學期`);
        }
    } catch (error) {
        console.error('❌ 載入學期失敗:', error);
    }
}

// ========================================
// 功能：載入帳號列表
// ========================================
async function loadAccounts() {
    try {
        const response = await fetch('/api/users');
        const data = await response.json();
        
        if (data.success) {
            displayStudents(data.students || []);
            displayAdmins(data.admins || []);
            console.log(`✅ 載入 ${(data.students || []).length} 個學生, ${(data.admins || []).length} 個管理員`);
        }
    } catch (error) {
        console.error('❌ 載入帳號失敗:', error);
    }
}

// ========================================
// 功能：顯示學生帳號卡片
// ========================================
function displayStudents(students) {
    const container = document.getElementById('studentsGrid');
    
    if (!students || students.length === 0) {
        container.innerHTML = '<p class="no-results">尚無學生帳號</p>';
        return;
    }
    
    let html = '';
    students.forEach((user) => {
        const avatar = user.avatar || '🐱';
        html += `
            <div class="account-card" onclick="editAccount(${user.id})" style="cursor: pointer;">
                <button class="delete-account-btn" onclick="event.stopPropagation(); deleteAccount(${user.id}, '${user.username}')" title="刪除帳號">✖</button>
                <div class="account-avatar-emoji">${avatar}</div>
                <div class="account-name">${user.name || user.username}</div>
                <div class="account-id">ID : ${user.student_id || user.username}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ========================================
// 功能：顯示管理員帳號卡片
// ========================================
function displayAdmins(admins) {
    const container = document.getElementById('adminsGrid');
    
    if (!admins || admins.length === 0) {
        container.innerHTML = '<p class="no-results">尚無管理員帳號</p>';
        return;
    }
    
    let html = '';
    admins.forEach((user) => {
        const avatar = user.avatar || '🧑‍💼';
        html += `
            <div class="account-card" onclick="editAccount(${user.id})" style="cursor: pointer;">
                <button class="delete-account-btn" onclick="event.stopPropagation(); deleteAccount(${user.id}, '${user.username}')" title="刪除帳號">✖</button>
                <div class="account-avatar-emoji">${avatar}</div>
                <div class="account-name">${user.name || user.username}</div>
                <div class="account-id">ID : ${user.username}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ========================================
// 功能：顯示帳號卡片 (保留向後兼容)
// ========================================
function displayAccounts(users) {
    // 分開學生和管理員
    const students = users.filter(u => u.role === 'student');
    const admins = users.filter(u => u.role === 'admin');
    displayStudents(students);
    displayAdmins(admins);
}

// ========================================
// 功能：開啟新增帳號Modal
// ========================================
function openAddAccountModal() {
    document.getElementById('accountForm').reset();
    document.getElementById('accountModal').classList.add('active');
    console.log('➕ 開啟新增帳號視窗');
}

// ========================================
// 功能：關閉帳號Modal
// ========================================
function closeAccountModal() {
    document.getElementById('accountModal').classList.remove('active');
    document.getElementById('accountForm').reset();
    console.log('✖ 關閉帳號視窗');
}

// ========================================
// 功能：處理帳號表單提交
// ========================================
async function handleAccountSubmit(e) {
    e.preventDefault();
    
    const accountData = {
        username: document.getElementById('accountUsername').value,
        password: document.getElementById('accountPassword').value,
        name: document.getElementById('accountName').value,
        role: document.getElementById('accountRole').value,
        phone: document.getElementById('accountPhone').value,
        avatar: document.getElementById('accountAvatar').value || '🐱'
    };
    
    try {
        const response = await fetch('/api/users', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(accountData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✓ ' + result.message);
            closeAccountModal();
            loadAccounts(); // 重新載入帳號列表
            console.log('✅ 帳號新增成功');
        } else {
            alert('✗ ' + result.message);
        }
    } catch (error) {
        console.error('❌ 新增帳號失敗:', error);
        alert('操作失敗，請稍後再試');
    }
}

// ========================================
// 功能：選擇頭貼
// ========================================
function selectAvatar(element) {
    // 移除其他選中狀態
    document.querySelectorAll('.avatar-option-sm').forEach(el => {
        el.classList.remove('selected');
    });
    document.querySelectorAll('.avatar-option').forEach(el => {
        el.classList.remove('selected');
    });
    // 添加選中狀態
    element.classList.add('selected');
    // 更新隱藏欄位
    document.getElementById('accountAvatar').value = element.dataset.avatar;
    // 更新大頭貼顯示
    const avatarDisplay = document.getElementById('accountAvatarDisplay');
    if (avatarDisplay) {
        avatarDisplay.textContent = element.dataset.avatar;
    }
}

// ========================================
// 功能：刪除帳號
// ========================================
async function deleteAccount(username) {
    if (!confirm(`確定要刪除帳號 ${username} 嗎？`)) return;
    
    try {
        const response = await fetch(`/api/users/${username}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            alert('✓ ' + result.message);
            loadAccounts(); // 重新載入帳號列表
            console.log('✅ 帳號刪除成功');
        } else {
            alert('✗ ' + result.message);
        }
    } catch (error) {
        console.error('❌ 刪除帳號失敗:', error);
        alert('操作失敗，請稍後再試');
    }
}

// ========================================
// 功能：登出
// ========================================
async function logout() {
    if (!confirm('確定要登出嗎？')) return;
    
    try {
        await fetch('/api/logout', {method: 'POST'});
        localStorage.removeItem('currentUser');
        console.log('✅ 登出成功');
        window.location.href = '/';
    } catch (error) {
        console.error('❌ 登出失敗:', error);
        window.location.href = '/';
    }
}

// ========================================
// Enter鍵快速搜尋
// ========================================
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        const activeElement = document.activeElement;
        if (activeElement.id === 'adminKeywordInput') {
            adminSearchCourses();
        }
    }
});

// ========================================
// Modal背景點擊關閉
// ========================================
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        if (e.target.id === 'courseModal') closeCourseModal();
        if (e.target.id === 'accountModal') closeAccountModal();
    }
});

// ========================================
// 篩選面板功能
// ========================================

// 切換篩選面板
function toggleFilterPanel(type) {
    const container = document.getElementById('adminFilterPanelContainer');
    
    if (adminCurrentFilterPanel === type) {
        container.innerHTML = '';
        adminCurrentFilterPanel = null;
        return;
    }
    
    adminCurrentFilterPanel = type;
    let panelHTML = '';
    
    switch(type) {
        case 'weekday':
            panelHTML = createAdminWeekdayPanel();
            break;
        case 'period':
            panelHTML = createAdminPeriodPanel();
            break;
        case 'degree':
            panelHTML = createAdminDegreePanel();
            break;
        case 'category':
            panelHTML = createAdminCategoryPanel();
            break;
        case 'dept':
            container.innerHTML = '';
            adminCurrentFilterPanel = null;
            return;
    }
    
    container.innerHTML = panelHTML;
    restoreAdminFilterSelections(type);
}

// 建立星期篩選面板
function createAdminWeekdayPanel() {
    const weekdays = [
        { value: '1', label: '週一' },
        { value: '2', label: '週二' },
        { value: '3', label: '週三' },
        { value: '4', label: '週四' },
        { value: '5', label: '週五' },
        { value: '6', label: '週六' },
        { value: '7', label: '週日' }
    ];
    
    return `
        <div class="filter-panel">
            <div class="filter-panel-title">星期：</div>
            <div class="filter-panel-content">
                ${weekdays.map(day => `
                    <div class="filter-checkbox-group">
                        <input type="checkbox" id="admin_weekday_${day.value}" value="${day.value}" 
                               onchange="updateAdminFilter('weekday', '${day.value}', this.checked)">
                        <label for="admin_weekday_${day.value}">${day.label}</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// 建立節次篩選面板
function createAdminPeriodPanel() {
    const periods = [
        { value: '1', label: '第1節 (08:10~09:00)' },
        { value: '2', label: '第2節 (09:10~10:00)' },
        { value: '3', label: '第3節 (10:10~11:00)' },
        { value: '4', label: '第4節 (11:10~12:00)' },
        { value: '5', label: '第5節 (12:40~13:30)' },
        { value: '6', label: '第6節 (13:40~14:30)' },
        { value: '7', label: '第7節 (14:40~15:30)' },
        { value: '8', label: '第8節 (15:40~16:30)' },
        { value: '9', label: '第9節 (16:40~17:30)' },
        { value: '10', label: '第10節 (17:40~18:30)' },
        { value: '11', label: '第11節 (18:35~19:25)' },
        { value: '12', label: '第12節 (19:30~20:20)' },
        { value: '13', label: '第13節 (20:25~21:15)' },
        { value: '14', label: '第14節 (21:20~22:10)' }
    ];
    
    return `
        <div class="filter-panel">
            <div class="filter-panel-title">節次：</div>
            <div class="filter-panel-content">
                ${periods.map(p => `
                    <div class="filter-checkbox-group">
                        <input type="checkbox" id="admin_period_${p.value}" value="${p.value}" 
                               onchange="updateAdminFilter('period', '${p.value}', this.checked)">
                        <label for="admin_period_${p.value}">${p.label}</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// 建立學制篩選面板
function createAdminDegreePanel() {
    const degrees = [
        { value: '四技', label: '四技' },
        { value: '二技', label: '二技' },
        { value: '二技(三年)', label: '二技(三年)' },
        { value: '碩士班', label: '碩士班' },
        { value: '博士班', label: '博士班' },
        { value: '學士後系', label: '學士後系' },
        { value: '學士後多元專長', label: '學士後多元專長' },
        { value: '學士後學位學程', label: '學士後學位學程' }
    ];
    
    return `
        <div class="filter-panel">
            <div class="filter-panel-title">學制：</div>
            <div class="filter-panel-content">
                ${degrees.map(d => `
                    <div class="filter-checkbox-group">
                        <input type="checkbox" id="admin_degree_${d.value}" value="${d.value}" 
                               onchange="updateAdminFilter('degree', '${d.value}', this.checked)">
                        <label for="admin_degree_${d.value}">${d.label}</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// 建立課程內容分類篩選面板
function createAdminCategoryPanel() {
    const categories = [
        { value: '跨校', label: '跨校' },
        { value: '跨域課程', label: '跨域課程' },
        { value: '全英語授課', label: '全英語授課' },
        { value: 'EMI全英語授課', label: 'EMI全英語授課' },
        { value: '同步遠距教學', label: '同步遠距教學' },
        { value: '非同步遠距教學', label: '非同步遠距教學' },
        { value: '混合式遠距教學', label: '混合式遠距教學' },
        { value: '遠距教學課程', label: '遠距教學課程' },
        { value: '遠距輔助課程', label: '遠距輔助課程' }
    ];
    
    return `
        <div class="filter-panel">
            <div class="filter-panel-title">課程內容分類：</div>
            <div class="filter-panel-content">
                ${categories.map(c => `
                    <div class="filter-checkbox-group">
                        <input type="checkbox" id="admin_category_${c.value.replace(/\s/g, '_')}" value="${c.value}" 
                               onchange="updateAdminFilter('category', '${c.value}', this.checked)">
                        <label for="admin_category_${c.value.replace(/\s/g, '_')}">${c.label}</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// 更新篩選條件
function updateAdminFilter(type, value, checked) {
    if (checked) {
        if (!adminSelectedFilters[type].includes(value)) {
            adminSelectedFilters[type].push(value);
        }
    } else {
        adminSelectedFilters[type] = adminSelectedFilters[type].filter(v => v !== value);
    }
    console.log('管理員篩選條件已更新:', adminSelectedFilters);
}

// 恢復篩選選擇狀態
function restoreAdminFilterSelections(type) {
    if (adminSelectedFilters[type] && adminSelectedFilters[type].length > 0) {
        adminSelectedFilters[type].forEach(value => {
            const safeValue = value.replace(/\s/g, '_');
            const checkbox = document.getElementById(`admin_${type}_${value}`) || 
                           document.getElementById(`admin_${type}_${safeValue}`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
    }
}

// ========================================
// 變更密碼功能
// ========================================
function showChangePasswordModal() {
    document.getElementById('changePasswordModal').style.display = 'flex';
    document.getElementById('oldPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
}

function closeChangePasswordModal() {
    document.getElementById('changePasswordModal').style.display = 'none';
}

async function submitChangePassword(event) {
    event.preventDefault();
    
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (newPassword !== confirmPassword) {
        alert('新密碼與確認密碼不一致！');
        return;
    }
    
    try {
        const response = await fetch('/api/change-password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('密碼變更成功！');
            closeChangePasswordModal();
        } else {
            alert('密碼變更失敗：' + result.message);
        }
    } catch (error) {
        console.error('變更密碼錯誤:', error);
        alert('變更密碼失敗，請稍後再試');
    }
}

// ========================================
// 帳號編輯功能
// ========================================
let editingUserId = null;

async function editAccount(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        
        if (data.success && data.user) {
            editingUserId = userId;
            const user = data.user;
            
            document.getElementById('editAccountId').value = user.id;
            document.getElementById('editAccountName').value = user.name || '';
            document.getElementById('editAccountStudentId').value = user.student_id || '';
            document.getElementById('editAccountDepartment').value = user.department || '';
            document.getElementById('editAccountClass').value = user.class_name || '';
            document.getElementById('editAccountUsername').value = user.username || '';
            document.getElementById('editAccountAvatarDisplay').textContent = user.avatar || '🐱';
            document.getElementById('editAccountAvatar').value = user.avatar || '🐱';
            
            document.getElementById('editAccountModal').style.display = 'flex';
        }
    } catch (error) {
        console.error('載入帳號資料失敗:', error);
        alert('載入帳號資料失敗');
    }
}

// 編輯帳號時選擇頭貼
function selectEditAvatar(element) {
    const avatar = element.dataset.avatar;
    document.getElementById('editAccountAvatarDisplay').textContent = avatar;
    document.getElementById('editAccountAvatar').value = avatar;
}

function closeEditAccountModal() {
    document.getElementById('editAccountModal').style.display = 'none';
    editingUserId = null;
}

async function submitEditAccount(event) {
    event.preventDefault();
    
    if (!editingUserId) return;
    
    const data = {
        name: document.getElementById('editAccountName').value,
        student_id: document.getElementById('editAccountStudentId').value,
        department: document.getElementById('editAccountDepartment').value,
        class_name: document.getElementById('editAccountClass').value,
        username: document.getElementById('editAccountUsername').value,
        avatar: document.getElementById('editAccountAvatar').value || '🐱'
    };
    
    try {
        const response = await fetch(`/api/users/${editingUserId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('帳號資料更新成功！');
            closeEditAccountModal();
            loadAccounts();
        } else {
            alert('更新失敗：' + result.message);
        }
    } catch (error) {
        console.error('更新帳號失敗:', error);
        alert('更新帳號失敗，請稍後再試');
    }
}

async function resetAccountPassword() {
    if (!editingUserId) return;
    
    if (!confirm('確定要將此帳號的密碼重設為預設值 (pass123) 嗎？')) return;
    
    try {
        const response = await fetch(`/api/users/${editingUserId}/reset-password`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(result.message);
        } else {
            alert('重設密碼失敗：' + result.message);
        }
    } catch (error) {
        console.error('重設密碼失敗:', error);
        alert('重設密碼失敗，請稍後再試');
    }
}

console.log('✅ 管理員篩選面板功能已載入');
console.log('🎉 admin.js 載入完成');
