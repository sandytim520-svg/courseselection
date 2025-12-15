// ========================================
// 北護課程查詢系統 - 訪客模式 JavaScript
// ========================================

console.log('🚀 訪客模式已載入');

// ========================================
// 初始化
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ 訪客頁面初始化');
    loadDepartments();
});

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
            console.log(`✅ 載入 ${data.departments.length} 個系所`);
        }
    } catch (error) {
        console.error('❌ 載入系所失敗:', error);
    }
}

// ========================================
// 篩選狀態管理
// ========================================
let currentFilters = {
    weekday: [],
    period: [],
    degree: [],
    category: []
};

let currentPanel = null;

// ========================================
// 功能：搜尋課程
// ========================================
async function searchCourses() {
    const semester = document.getElementById('semesterSelect').value;
    const keyword = document.getElementById('keywordInput').value.trim();
    const department = document.getElementById('departmentSelect').value;
    const grade = document.getElementById('gradeSelect').value;
    const courseType = document.getElementById('typeSelect').value;
    
    // 驗證必填欄位
    if (!semester) {
        alert('請選擇學期');
        return;
    }
    
    // 建立查詢參數
    let params = new URLSearchParams();
    params.append('semester', semester);
    if (keyword) params.append('keyword', keyword);
    if (department) params.append('department', department);
    if (grade) params.append('grade', grade);
    if (courseType) params.append('type', courseType);
    
    // 加入篩選條件
    if (currentFilters.weekday.length > 0) {
        params.append('weekday', currentFilters.weekday.join(','));
    }
    if (currentFilters.period.length > 0) {
        params.append('period', currentFilters.period.join(','));
    }
    if (currentFilters.degree.length > 0) {
        params.append('degree', currentFilters.degree.join(','));
    }
    if (currentFilters.category.length > 0) {
        params.append('category', currentFilters.category.join(','));
    }
    
    try {
        console.log('🔍 搜尋課程:', params.toString());
        const response = await fetch(`/api/courses?${params.toString()}`);
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ 找到 ${data.count} 筆課程`);
            displaySearchResults(data.items);
        } else {
            alert('搜尋失敗: ' + data.message);
        }
    } catch (error) {
        console.error('❌ 搜尋失敗:', error);
        alert('搜尋失敗，請稍後再試');
    }
}

// ========================================
// 功能：顯示搜尋結果 (訪客版 - 無收藏/預選按鈕)
// ========================================
function displaySearchResults(courses) {
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
                <td><a href="#" class="classroom-link">${course.classroom || ''}</a></td>
                <td>${weekdayDisplay}</td>
                <td>${periodDisplay}</td>
                <td>
                    <button class="btn-icon btn-outline" onclick="showCourseInfo(${course.id})" title="課程資訊">•••</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    container.innerHTML = html;
}

// ========================================
// 功能：顯示課程資訊 (大綱)
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
// 功能：清除搜尋
// ========================================
function clearSearch() {
    document.getElementById('semesterSelect').value = '';
    document.getElementById('keywordInput').value = '';
    document.getElementById('departmentSelect').value = '';
    document.getElementById('gradeSelect').value = '';
    document.getElementById('typeSelect').value = '';
    
    // 清除篩選條件
    currentFilters = {
        weekday: [],
        period: [],
        degree: [],
        category: []
    };
    
    // 清除篩選面板
    document.getElementById('filterPanelContainer').innerHTML = '';
    currentPanel = null;
    
    // 清除結果
    document.getElementById('searchResults').innerHTML = '<p class="no-results">請輸入搜尋條件查詢課程</p>';
    
    console.log('✅ 已清除搜尋條件');
}

// ========================================
// 篩選面板功能
// ========================================
function toggleFilterPanel(panelType) {
    const container = document.getElementById('filterPanelContainer');
    
    if (currentPanel === panelType) {
        container.innerHTML = '';
        currentPanel = null;
        return;
    }
    
    let panelHTML = '';
    switch (panelType) {
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
        default:
            container.innerHTML = '';
            currentPanel = null;
            return;
    }
    
    container.innerHTML = panelHTML;
    currentPanel = panelType;
    
    // 恢復已選狀態
    restoreFilterState(panelType);
}

function restoreFilterState(panelType) {
    const values = currentFilters[panelType] || [];
    values.forEach(val => {
        const checkbox = document.getElementById(`${panelType}_${val}`);
        if (checkbox) checkbox.checked = true;
    });
}

function updateFilter(filterType, value, checked) {
    if (checked) {
        if (!currentFilters[filterType].includes(value)) {
            currentFilters[filterType].push(value);
        }
    } else {
        currentFilters[filterType] = currentFilters[filterType].filter(v => v !== value);
    }
    console.log(`篩選更新 - ${filterType}:`, currentFilters[filterType]);
}

// 建立星期篩選面板
function createWeekdayPanel() {
    const weekdays = [
        { value: '1', label: '星期一' },
        { value: '2', label: '星期二' },
        { value: '3', label: '星期三' },
        { value: '4', label: '星期四' },
        { value: '5', label: '星期五' },
        { value: '6', label: '星期六' },
        { value: '7', label: '星期日' }
    ];
    
    return `
        <div class="filter-panel">
            <div class="filter-panel-title">星期：</div>
            <div class="filter-panel-content">
                ${weekdays.map(w => `
                    <div class="filter-checkbox-group">
                        <input type="checkbox" id="weekday_${w.value}" value="${w.value}" 
                               onchange="updateFilter('weekday', '${w.value}', this.checked)">
                        <label for="weekday_${w.value}">${w.label}</label>
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
