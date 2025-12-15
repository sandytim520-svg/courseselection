/* ==========================================================
   北護課程查詢系統 - 學生頁面JavaScript
   功能: 課程搜尋、收藏、選課管理
   ========================================================== */

// ========================================
// 全域變數
// ========================================
let currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');

// ========================================
// 頁面載入時執行
// ========================================
window.onload = function() {
    console.log('✅ 學生頁面載入完成');
    loadDepartments();
    loadMyCourses();
};

// ========================================
// 功能：載入系所列表
// ========================================
async function loadDepartments() {
    try {
        const response = await fetch('/api/departments');
        const data = await response.json();
        
        if (data.success && data.departments) {
            const select = document.getElementById('departmentSelect');
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
        'home': 'homeSection',
        'favorites': 'favoritesSection',
        'preselect': 'preselectSection',
        'mycourses': 'mycoursesSection'
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
    if (section === 'mycourses') loadMyCourses();
    if (section === 'favorites') loadFavorites();
    if (section === 'preselect') loadPreselect();
    
    console.log('📄 切換到:', section);
}

// ========================================
// 功能:搜尋課程
// ========================================
async function searchCourses() {
    const keyword = document.getElementById('keywordInput').value.trim();
    const semester = document.getElementById('semesterSelect').value;
    const department = document.getElementById('departmentSelect').value;
    const grade = document.getElementById('gradeSelect').value;
    const courseType = document.getElementById('typeSelect').value;
    
    // 建立查詢參數
    let params = new URLSearchParams();
    if (keyword) params.append('keyword', keyword);
    if (semester) params.append('semester', semester);
    if (department) params.append('department', department);
    if (grade) params.append('grade', grade);
    if (courseType) params.append('type', courseType);
    
    // 添加新的篩選條件
    if (selectedFilters.weekday && selectedFilters.weekday.length > 0) {
        params.append('weekday', selectedFilters.weekday.join(','));
    }
    if (selectedFilters.period && selectedFilters.period.length > 0) {
        params.append('period', selectedFilters.period.join(','));
    }
    if (selectedFilters.degree && selectedFilters.degree.length > 0) {
        params.append('degree', selectedFilters.degree.join(','));
    }
    if (selectedFilters.category && selectedFilters.category.length > 0) {
        params.append('category', selectedFilters.category.join(','));
    }
    
    console.log('🔍 搜尋參數:', Object.fromEntries(params));
    
    try {
        const response = await fetch(`/api/courses?${params}`);
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ 找到 ${data.count} 筆課程`);
            displayResults(data.items);
        } else {
            displayResults([]);
        }
    } catch (error) {
        console.error('❌ 搜尋失敗:', error);
        alert('搜尋失敗,請稍後再試');
    }
}

// ========================================
// 功能：顯示搜尋結果
// ========================================
function displayResults(courses) {
    const container = document.getElementById('searchResults');
    
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
                    <th>收藏</th>
                    <th>預選</th>
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
            // 從day_time提取星期
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
                <td><a href="#" class="classroom-link">${course.classroom || ''}</a></td>
                <td>${weekdayDisplay}</td>
                <td>${periodDisplay}</td>
                <td>
                    <button class="btn-icon btn-outline" onclick="showCourseInfo(${course.id})" title="課程資訊">•••</button>
                </td>
                <td>
                    <button class="btn-icon btn-heart" onclick="addToFavorite(${course.id})" title="收藏">♡</button>
                </td>
                <td>
                    <button class="btn-icon btn-add" onclick="addToPreselect(${course.id})" title="加入預選">⊕</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// ========================================
// 功能：顯示課程資訊 (大綱) - 學生版
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
                    <div class="course-info-modal student-modal" onclick="event.stopPropagation()">
                        <div class="course-info-header student-header">
                            <h3>課程資訊</h3>
                            <button class="close-btn-x" onclick="closeCourseInfoModal()">✕</button>
                        </div>
                        <div class="course-info-body">
                            <div class="info-grid">
                                <div class="info-cell">
                                    <span class="info-label">學年期</span>
                                    <span class="info-value">${course.semester || ''}</span>
                                </div>
                                <div class="info-cell">
                                    <span class="info-label">課程代碼</span>
                                    <span class="info-value">${course.course_code || ''}</span>
                                </div>
                            </div>
                            <div class="info-grid">
                                <div class="info-cell">
                                    <span class="info-label">課程名稱</span>
                                    <span class="info-value">${course.course_name || ''}</span>
                                </div>
                                <div class="info-cell">
                                    <span class="info-label">授課老師</span>
                                    <span class="info-value">${course.instructor || ''}</span>
                                </div>
                            </div>
                            <div class="info-grid">
                                <div class="info-cell">
                                    <span class="info-label">學分數</span>
                                    <span class="info-value">${course.credits || ''}</span>
                                </div>
                                <div class="info-cell">
                                    <span class="info-label">課別名稱</span>
                                    <span class="info-value">${course.course_type || ''}</span>
                                </div>
                            </div>
                            <div class="info-grid">
                                <div class="info-cell">
                                    <span class="info-label">上課人數</span>
                                    <span class="info-value">${course.capacity !== null && course.capacity !== undefined ? course.capacity : ''}</span>
                                </div>
                                <div class="info-cell">
                                    <span class="info-label">班組名稱</span>
                                    <span class="info-value">${course.class_group || ''}</span>
                                </div>
                            </div>
                            <div class="info-grid single">
                                <div class="info-cell full">
                                    <span class="info-label">時間及教室</span>
                                    <span class="info-value">${timeDisplay || '無'}</span>
                                </div>
                            </div>
                            <div class="info-remarks">
                                <span class="info-label">課程備註</span>
                                <div class="remarks-text">${course.remarks || '無'}</div>
                            </div>
                        </div>
                        <div class="course-info-footer">
                            <button class="btn-close-green" onclick="closeCourseInfoModal()">關閉</button>
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
// 功能：加入收藏
// ========================================
async function addToFavorite(courseId) {
    try {
        const response = await fetch('/api/enroll', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({course_id: courseId, status: 'favorite'})
        });
        const result = await response.json();
        
        if (result.success) {
            alert('✓ ' + result.message);
            console.log('✅ 加入收藏成功');
        } else {
            alert('✗ ' + result.message);
        }
    } catch (error) {
        console.error('❌ 加入收藏失敗:', error);
        alert('操作失敗，請稍後再試');
    }
}

// ========================================
// 功能：加入預選
// ========================================
async function addToPreselect(courseId) {
    try {
        const response = await fetch('/api/enroll', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({course_id: courseId, status: 'enrolled'})
        });
        const result = await response.json();
        
        if (result.success) {
            alert('✓ ' + result.message);
            console.log('✅ 加入預選成功');
        } else {
            alert('✗ ' + result.message);
        }
    } catch (error) {
        console.error('❌ 加入預選失敗:', error);
        alert('操作失敗，請稍後再試');
    }
}

// ========================================
// 功能：載入我的課表
// ========================================
async function loadMyCourses() {
    try {
        const response = await fetch('/api/my-courses?status=enrolled');
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ 載入課表成功: ${data.count} 筆`);
            displayCourseList(data.items, 'myCoursesList');
        }
    } catch (error) {
        console.error('❌ 載入課表失敗:', error);
    }
}

// ========================================
// 功能：載入收藏清單
// ========================================
async function loadFavorites() {
    try {
        const response = await fetch('/api/my-courses?status=favorite');
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ 載入收藏成功: ${data.count} 筆`);
            displayFavoritesList(data.items);
        }
    } catch (error) {
        console.error('❌ 載入收藏失敗:', error);
    }
}

// ========================================
// 功能：顯示收藏清單 (卡片式設計)
// ========================================
function displayFavoritesList(courses) {
    const container = document.getElementById('favoritesList');
    
    if (!courses || courses.length === 0) {
        container.innerHTML = '<p class="no-results">尚無收藏課程</p>';
        return;
    }
    
    let html = '<div class="favorites-cards">';
    
    courses.forEach(course => {
        html += `
            <div class="favorite-card">
                <div class="favorite-info">
                    <span class="favorite-semester">${course.semester || ''}</span>
                    <span class="favorite-dept">${course.department || ''}</span>
                    <span class="favorite-type">${course.course_type || ''}</span>
                    <span class="favorite-name">${course.course_name || ''}</span>
                    <span class="favorite-instructor">${course.instructor || ''}</span>
                </div>
                <div class="favorite-actions">
                    <button class="btn-add-preselect" onclick="addFavoriteToPreselect(${course.id}, ${course.enrollment_id})" title="加入預選">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="12" y1="8" x2="12" y2="16"/>
                            <line x1="8" y1="12" x2="16" y2="12"/>
                        </svg>
                    </button>
                    <button class="btn-remove-favorite" onclick="removeCourse(${course.enrollment_id})" title="移除收藏">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// ========================================
// 功能：從收藏加入預選課表
// ========================================
async function addFavoriteToPreselect(courseId, enrollmentId) {
    try {
        // 直接將收藏狀態改為預選
        const response = await fetch('/api/enroll', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({course_id: courseId, status: 'enrolled'})
        });
        const result = await response.json();
        
        if (result.success) {
            alert('✓ 已加入預選課表');
            console.log('✅ 加入預選成功');
            loadFavorites();
            loadPreselect();
        } else {
            alert('✗ ' + result.message);
        }
    } catch (error) {
        console.error('❌ 加入預選失敗:', error);
        alert('操作失敗，請稍後再試');
    }
}

// ========================================
// 功能：載入預選課表
// ========================================
async function loadPreselect() {
    try {
        const response = await fetch('/api/my-courses?status=enrolled');
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ 載入預選成功: ${data.count} 筆`);
            renderScheduleTable(data.items || []);
        } else {
            // 即使API失敗也顯示空白課表
            renderScheduleTable([]);
        }
    } catch (error) {
        console.error('❌ 載入預選失敗:', error);
        // 發生錯誤時也顯示空白課表
        renderScheduleTable([]);
    }
}

// ========================================
// 功能：渲染課表視覺化
// ========================================
function renderScheduleTable(courses) {
    const scheduleBody = document.getElementById('scheduleBody');
    
    // 時間表定義
    const periodTimes = [
        { period: 1, time: '08:10-09:00' },
        { period: 2, time: '09:10-10:00' },
        { period: 3, time: '10:10-11:00' },
        { period: 4, time: '11:10-12:00' },
        { period: 5, time: '12:40-13:30' },
        { period: 6, time: '13:40-14:30' },
        { period: 7, time: '14:40-15:30' },
        { period: 8, time: '15:40-16:30' },
        { period: 9, time: '16:40-17:30' },
        { period: 10, time: '17:40-18:30' },
        { period: 11, time: '18:35-19:25' },
        { period: 12, time: '19:30-20:20' },
        { period: 13, time: '20:25-21:15' },
        { period: 14, time: '21:20-22:10' }
    ];
    
    // 建立課表資料結構 (週一到週日)
    const schedule = {};
    for (let i = 1; i <= 14; i++) {
        schedule[i] = { 1: null, 2: null, 3: null, 4: null, 5: null, 6: null, 7: null };
    }
    
    // 填入課程
    let totalCredits = 0;
    courses.forEach(course => {
        let weekday = course.weekday;
        let periods = course.period;
        
        // 如果沒有weekday，從day_time解析
        if (!weekday && course.day_time) {
            const dayMatch = course.day_time.match(/週([一二三四五六日])/);
            if (dayMatch) {
                const dayMap = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7};
                weekday = dayMap[dayMatch[1]];
            }
        }
        
        // 如果沒有period，從day_time解析
        if (!periods && course.day_time) {
            const periodMatch = course.day_time.match(/(\d+[-,\d]*)/);
            if (periodMatch) {
                periods = periodMatch[1];
            }
        }
        
        if (weekday && periods && weekday <= 7) {
            // 解析節次 (可能是 "2,3,4" 或 "2-4")
            let periodList = [];
            if (periods.includes('-')) {
                const range = periods.split('-');
                for (let p = parseInt(range[0]); p <= parseInt(range[range.length-1]); p++) {
                    periodList.push(p);
                }
            } else if (periods.includes(',')) {
                periodList = periods.split(',').map(p => parseInt(p.trim()));
            } else {
                periodList = [parseInt(periods)];
            }
            
            // 設定每個節次
            periodList.forEach(p => {
                if (p >= 1 && p <= 14) {
                    schedule[p][weekday] = {
                        name: course.course_name,
                        classroom: course.classroom || '',
                        id: course.id,
                        enrollment_id: course.enrollment_id
                    };
                }
            });
        }
        
        totalCredits += parseFloat(course.credits) || 0;
    });
    
    // 生成HTML (週一到週日)
    let html = '';
    periodTimes.forEach(pt => {
        html += `<tr>
            <td class="schedule-period">${pt.period}</td>
            <td class="schedule-time">${pt.time}</td>`;
        
        for (let day = 1; day <= 7; day++) {
            const cell = schedule[pt.period][day];
            if (cell) {
                html += `<td class="schedule-cell has-course">
                    <div class="course-block">
                        <div class="course-name">${cell.name}</div>
                        <div class="course-room">${cell.classroom}</div>
                        <button class="btn-delete-course" onclick="removeCourseFromSchedule(${cell.enrollment_id}); event.stopPropagation();">刪除</button>
                    </div>
                </td>`;
            } else {
                html += `<td class="schedule-cell"></td>`;
            }
        }
        
        html += '</tr>';
    });
    
    scheduleBody.innerHTML = html;
    document.getElementById('totalCredits').textContent = totalCredits;
}

// 從課表移除課程
async function removeCourseFromSchedule(enrollmentId) {
    if (!confirm('確定要從課表移除此課程嗎？')) return;
    
    try {
        const response = await fetch(`/api/enroll/${enrollmentId}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            loadPreselect(); // 重新載入課表
        }
    } catch (error) {
        console.error('❌ 移除失敗:', error);
    }
}

// 匯出課表
function exportSchedule() {
    alert('匯出功能開發中...');
}

// ========================================
// 功能：顯示課程列表
// ========================================
function displayCourseList(courses, containerId) {
    const container = document.getElementById(containerId);
    
    if (!courses || courses.length === 0) {
        container.innerHTML = '<p class="no-results">尚無課程</p>';
        return;
    }
    
    let html = `
        <table class="results-table">
            <thead>
                <tr>
                    <th>課程代碼</th>
                    <th>課程名稱</th>
                    <th>教師</th>
                    <th>時間</th>
                    <th>學分</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    courses.forEach(course => {
        html += `
            <tr>
                <td>${course.course_code}</td>
                <td>${course.course_name}</td>
                <td>${course.instructor}</td>
                <td>${course.day_time}</td>
                <td>${course.credits}</td>
                <td>
                    <button class="btn-icon" onclick="removeCourse(${course.enrollment_id})" title="移除">🗑️</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// ========================================
// 功能：移除課程
// ========================================
async function removeCourse(enrollmentId) {
    if (!confirm('確定要移除嗎？')) return;
    
    try {
        const response = await fetch(`/api/enroll/${enrollmentId}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            alert('✓ ' + result.message);
            console.log('✅ 移除成功');
            // 重新載入列表
            loadMyCourses();
            loadFavorites();
        } else {
            alert('✗ ' + result.message);
        }
    } catch (error) {
        console.error('❌ 移除失敗:', error);
        alert('操作失敗，請稍後再試');
    }
}

// ========================================
// 功能：清除搜尋
// ========================================
function clearSearch() {
    document.getElementById('keywordInput').value = '';
    document.getElementById('semesterSelect').value = '';
    document.getElementById('departmentSelect').value = '';
    document.getElementById('gradeSelect').value = '';
    document.getElementById('typeSelect').value = '';
    
    // 清除新的篩選條件
    selectedFilters = {
        weekday: [],
        period: [],
        degree: [],
        category: []
    };
    
    // 關閉篩選面板
    const container = document.getElementById('filterPanelContainer');
    if (container) container.innerHTML = '';
    currentFilterPanel = null;
    
    document.getElementById('searchResults').innerHTML = 
        '<p class="no-results">請輸入搜尋條件查詢課程</p>';
    console.log('🧹 清除搜尋條件');
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
        if (activeElement.id === 'keywordInput') {
            searchCourses();
        }
    }
});

console.log('🎉 student.js 載入完成');

// ========================================
// 篩選面板管理
// ========================================
let currentFilterPanel = null;
let selectedFilters = {
    weekday: [],
    period: [],
    degree: [],
    category: []
};

// 切換篩選面板
function toggleFilterPanel(type) {
    const container = document.getElementById('filterPanelContainer');
    
    // 如果點擊相同的面板,則關閉
    if (currentFilterPanel === type) {
        container.innerHTML = '';
        currentFilterPanel = null;
        return;
    }
    
    // 切換到新面板
    currentFilterPanel = type;
    
    // 根據類型生成對應面板
    let panelHTML = '';
    
    switch(type) {
        case 'weekday':
            panelHTML = createWeekdayPanel();
            break;
        case 'period':
            panelHTML = createPeriodPanel();
            break;
        case 'degree':
            panelHTML = createDegreePanel();
            break;
        case 'category':
            panelHTML = createCategoryPanel();
            break;
        case 'dept':
            // 系所/年級/課別已經有下拉選單,不需要額外面板
            container.innerHTML = '';
            currentFilterPanel = null;
            return;
    }
    
    container.innerHTML = panelHTML;
    
    // 恢復之前的選擇狀態
    restoreFilterSelections(type);
}

// 建立星期篩選面板
function createWeekdayPanel() {
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
                        <input type="checkbox" id="weekday_${day.value}" value="${day.value}" 
                               onchange="updateFilter('weekday', '${day.value}', this.checked)">
                        <label for="weekday_${day.value}">${day.label}</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// 建立節次篩選面板
function createPeriodPanel() {
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
                        <input type="checkbox" id="period_${p.value}" value="${p.value}" 
                               onchange="updateFilter('period', '${p.value}', this.checked)">
                        <label for="period_${p.value}">${p.label}</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// 建立學制篩選面板
function createDegreePanel() {
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
                        <input type="checkbox" id="degree_${d.value}" value="${d.value}" 
                               onchange="updateFilter('degree', '${d.value}', this.checked)">
                        <label for="degree_${d.value}">${d.label}</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// 建立課程內容分類篩選面板
function createCategoryPanel() {
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
                        <input type="checkbox" id="category_${c.value.replace(/\s/g, '_')}" value="${c.value}" 
                               onchange="updateFilter('category', '${c.value}', this.checked)">
                        <label for="category_${c.value.replace(/\s/g, '_')}">${c.label}</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// 更新篩選條件
function updateFilter(type, value, checked) {
    if (checked) {
        if (!selectedFilters[type].includes(value)) {
            selectedFilters[type].push(value);
        }
    } else {
        selectedFilters[type] = selectedFilters[type].filter(v => v !== value);
    }
    console.log('篩選條件已更新:', selectedFilters);
}

// 恢復篩選選擇狀態
function restoreFilterSelections(type) {
    if (selectedFilters[type] && selectedFilters[type].length > 0) {
        selectedFilters[type].forEach(value => {
            const safeValue = value.replace(/\s/g, '_');
            const checkbox = document.getElementById(`${type}_${value}`) || 
                           document.getElementById(`${type}_${safeValue}`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
    }
}

// 顯示節次時間表浮動視窗
function showScheduleModal() {
    const schedules = [
        { period: '節01', time: '08:10~09:00' },
        { period: '節02', time: '09:10~10:00' },
        { period: '節03', time: '10:10~11:00' },
        { period: '節04', time: '11:10~12:00' },
        { period: '節05', time: '12:40~13:30' },
        { period: '節06', time: '13:40~14:30' },
        { period: '節07', time: '14:40~15:30' },
        { period: '節08', time: '15:40~16:30' },
        { period: '節09', time: '16:40~17:30' },
        { period: '節10', time: '17:40~18:30' },
        { period: '節11', time: '18:35~19:25' },
        { period: '節12', time: '19:30~20:20' },
        { period: '節13', time: '20:25~21:15' },
        { period: '節14', time: '21:20~22:10' }
    ];
    
    const modalHTML = `
        <div id="scheduleModal" class="schedule-modal show" onclick="closeScheduleModal(event)">
            <div class="schedule-modal-content" onclick="event.stopPropagation()">
                <div class="schedule-modal-header">
                    <div class="schedule-modal-title">節次時間表</div>
                    <button class="schedule-close-btn" onclick="closeScheduleModal()">&times;</button>
                </div>
                <div class="schedule-list">
                    ${schedules.map(s => `
                        <div class="schedule-item">${s.period} (${s.time})</div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    // 移除舊的modal
    const oldModal = document.getElementById('scheduleModal');
    if (oldModal) oldModal.remove();
    
    // 添加新modal
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// 關閉節次時間表浮動視窗
function closeScheduleModal(event) {
    const modal = document.getElementById('scheduleModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

// ========================================
// 個人檔案功能
// ========================================
let userProfile = null;

// 顯示個人檔案主選單
async function showProfileModal() {
    // 先載入個人資料
    try {
        const response = await fetch('/api/profile');
        const data = await response.json();
        
        if (data.success) {
            userProfile = data.profile;
            document.getElementById('profileDisplayName').textContent = userProfile.name || '粥預選';
            document.getElementById('profileDisplayId').textContent = `ID：${userProfile.student_id || userProfile.username}`;
        }
    } catch (error) {
        console.error('載入個人資料失敗:', error);
    }
    
    document.getElementById('profileModal').style.display = 'flex';
}

function closeProfileModal() {
    document.getElementById('profileModal').style.display = 'none';
}

// 顯示修改檔案 modal
async function showEditProfileModal() {
    closeProfileModal();
    
    // 載入最新資料
    try {
        const response = await fetch('/api/profile');
        const data = await response.json();
        
        if (data.success) {
            userProfile = data.profile;
            document.getElementById('editProfileName').textContent = userProfile.name || '-';
            document.getElementById('editProfileStudentId').textContent = userProfile.student_id || '-';
            document.getElementById('editProfileDepartment').textContent = userProfile.department || '-';
            document.getElementById('editProfileClass').textContent = userProfile.class_name || '-';
            document.getElementById('editProfilePhone').value = userProfile.phone || '';
            document.getElementById('editProfileEmail').value = userProfile.email || '';
        }
    } catch (error) {
        console.error('載入個人資料失敗:', error);
    }
    
    document.getElementById('editProfileModal').style.display = 'flex';
}

function closeEditProfileModal() {
    document.getElementById('editProfileModal').style.display = 'none';
}

async function submitEditProfile(event) {
    event.preventDefault();
    
    const data = {
        phone: document.getElementById('editProfilePhone').value,
        email: document.getElementById('editProfileEmail').value
    };
    
    try {
        const response = await fetch('/api/profile', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('個人資料更新成功！');
            closeEditProfileModal();
        } else {
            alert('更新失敗：' + result.message);
        }
    } catch (error) {
        console.error('更新個人資料失敗:', error);
        alert('更新失敗，請稍後再試');
    }
}

// 顯示變更密碼 modal
function showChangePasswordModal() {
    closeProfileModal();
    document.getElementById('changePasswordModal').style.display = 'flex';
    document.getElementById('oldPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
}

function closeChangePasswordModal() {
    document.getElementById('changePasswordModal').style.display = 'none';
}

// 返回個人檔案主選單
function backToProfileModal() {
    closeEditProfileModal();
    closeChangePasswordModal();
    showProfileModal();
}

async function submitChangePassword(event) {
    event.preventDefault();
    
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const messageEl = document.getElementById('passwordMessage');
    
    // 清除之前的訊息
    if (messageEl) {
        messageEl.textContent = '';
        messageEl.className = 'message';
    }
    
    if (!newPassword || !confirmPassword) {
        if (messageEl) {
            messageEl.textContent = '請輸入新密碼';
            messageEl.className = 'message error';
        } else {
            alert('請輸入新密碼');
        }
        return;
    }
    
    if (newPassword !== confirmPassword) {
        if (messageEl) {
            messageEl.textContent = '新密碼與確認密碼不一致';
            messageEl.className = 'message error';
        } else {
            alert('新密碼與確認密碼不一致！');
        }
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
            if (messageEl) {
                messageEl.textContent = '密碼變更成功！';
                messageEl.className = 'message success';
                setTimeout(() => {
                    closeChangePasswordModal();
                }, 1000);
            } else {
                alert('密碼變更成功！');
                closeChangePasswordModal();
            }
        } else {
            if (messageEl) {
                messageEl.textContent = result.message || '密碼變更失敗';
                messageEl.className = 'message error';
            } else {
                alert('密碼變更失敗：' + result.message);
            }
        }
    } catch (error) {
        console.error('變更密碼錯誤:', error);
        if (messageEl) {
            messageEl.textContent = '變更密碼失敗，請稍後再試';
            messageEl.className = 'message error';
        } else {
            alert('變更密碼失敗，請稍後再試');
        }
    }
}

console.log('✅ 篩選面板功能已載入');
console.log('✅ 個人檔案功能已載入');
