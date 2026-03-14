// ==================== 全局状态 ====================
let selectedCollection = null;
let selectedArticles = new Set();
let allArticles = [];
let outputDir = './downloads';

// ==================== 工具函数 ====================
function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    const id = Date.now();

    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ'
    };

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.id = `notif-${id}`;
    notification.innerHTML = `
        <span class="notification-icon">${icons[type]}</span>
        <span class="notification-message">${message}</span>
    `;

    container.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function formatCount(count) {
    if (count >= 10000) {
        return (count / 10000).toFixed(1) + '万';
    }
    return count.toString();
}

function extractCollectionId(input) {
    const patterns = [
        /^(\d+)$/,
        /collection\/(\d+)/,
        /collections\/(\d+)/
    ];

    for (const pattern of patterns) {
        const match = input.match(pattern);
        if (match) {
            return match[1];
        }
    }
    return null;
}

// ==================== API 调用 ====================
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '请求失败');
        }

        return await response.json();
    } catch (error) {
        throw error;
    }
}

// ==================== 页面导航 ====================
function switchPage(pageId) {
    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageId) {
            item.classList.add('active');
        }
    });

    // 更新页面显示
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(`page-${pageId}`).classList.add('active');
}

// 绑定导航事件
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        switchPage(item.dataset.page);
    });
});

// ==================== Cookie 管理 ====================
async function checkCookie() {
    try {
        const result = await apiRequest('/api/cookies/check', { method: 'POST' });
        document.getElementById('cookieStatus').className = 'status-indicator valid';
        document.getElementById('cookieStatus').querySelector('.status-text').textContent = '已连接';
        showNotification('Cookie 验证成功', 'success');
        return true;
    } catch (error) {
        document.getElementById('cookieStatus').className = 'status-indicator invalid';
        document.getElementById('cookieStatus').querySelector('.status-text').textContent = '未连接';
        showNotification('Cookie 无效或已过期', 'error');
        return false;
    }
}

async function saveCookies() {
    const cookieInput = document.getElementById('cookieInput');
    const cookieText = cookieInput.value.trim();

    if (!cookieText) {
        showNotification('请输入 Cookie 内容', 'error');
        return;
    }

    try {
        const cookies = JSON.parse(cookieText);
        const result = await apiRequest('/api/cookies', {
            method: 'POST',
            body: JSON.stringify({ cookies })
        });

        showNotification('Cookie 保存成功', 'success');
        checkCookie();
    } catch (error) {
        showNotification(`保存失败：${error.message}`, 'error');
    }
}

async function loadCookies() {
    try {
        const result = await apiRequest('/api/cookies');
        document.getElementById('cookieInput').value = JSON.stringify(result.cookies, null, 2);
        showNotification('Cookie 加载成功', 'success');
    } catch (error) {
        showNotification(`加载失败：${error.message}`, 'error');
    }
}

async function clearCookies() {
    try {
        await apiRequest('/api/cookies', { method: 'DELETE' });
        document.getElementById('cookieInput').value = '';
        showNotification('Cookie 已清除', 'success');
        checkCookie();
    } catch (error) {
        showNotification(`清除失败：${error.message}`, 'error');
    }
}

// ==================== 收藏夹管理 ====================
async function loadCollections() {
    const list = document.getElementById('collectionsList');
    list.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>加载中...</p>
        </div>
    `;

    try {
        const result = await apiRequest('/api/collections');
        const collections = result.collections || [];

        if (collections.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <span class="empty-state-icon">📚</span>
                    <p>暂无收藏夹</p>
                    <p style="font-size: 13px; margin-top: 10px;">请在上方输入收藏夹 URL 或 ID 添加</p>
                </div>
            `;
        } else {
            list.innerHTML = collections.map(coll => `
                <div class="collection-item" data-id="${coll.id}" onclick="selectCollection('${coll.id}', '${coll.title?.replace(/'/g, "\\'") || '未命名'}', ${coll.count || 0})">
                    <div class="collection-info">
                        <div class="collection-avatar">📚</div>
                        <div class="collection-details">
                            <div class="collection-name">${coll.title || '未命名'}</div>
                            <div class="collection-meta">
                                <span>📄 ${formatCount(coll.count || 0)} 篇</span>
                                <span>👤 ${coll.creator?.name || '未知'}</span>
                            </div>
                        </div>
                    </div>
                    <div class="collection-actions">
                        <button class="icon-btn" onclick="event.stopPropagation(); viewCollectionArticles('${coll.id}')" title="查看文章">👁️</button>
                    </div>
                </div>
            `).join('');
        }

        showNotification(`加载了 ${collections.length} 个收藏夹`, 'success');
    } catch (error) {
        list.innerHTML = `
            <div class="empty-state">
                <span class="empty-state-icon">⚠️</span>
                <p>加载失败：${error.message}</p>
            </div>
        `;
        showNotification('获取收藏夹失败', 'error');
    }
}

async function addCollection() {
    const input = document.getElementById('collectionUrlInput');
    const inputValue = input.value.trim();

    if (!inputValue) {
        showNotification('请输入收藏夹 URL 或 ID', 'error');
        return;
    }

    const collectionId = extractCollectionId(inputValue);
    if (!collectionId) {
        showNotification('无法解析收藏夹 ID，请检查输入格式', 'error');
        return;
    }

    try {
        const result = await apiRequest(`/api/collections/${collectionId}/info`, { method: 'POST' });
        selectCollection(collectionId, result.title || `收藏夹 ${collectionId}`, result.count || 0);
        showNotification(`成功添加收藏夹：${result.title}`, 'success');
        input.value = '';
        loadCollections();
    } catch (error) {
        showNotification(`收藏夹不存在或无法访问：${error.message}`, 'error');
    }
}

function selectCollection(id, name, count) {
    selectedCollection = { id, name, count };

    // 更新选中状态
    document.querySelectorAll('.collection-item').forEach(item => {
        item.classList.remove('selected');
        if (item.dataset.id === id) {
            item.classList.add('selected');
        }
    });

    // 跳转到文章列表页面
    switchPage('articles');
    loadArticles(id, name, count);
}

function viewCollectionArticles(id) {
    const item = document.querySelector(`.collection-item[data-id="${id}"]`);
    if (item) {
        const name = item.querySelector('.collection-name')?.textContent || '未命名';
        selectCollection(id, name, 0);
    }
}

// ==================== 文章管理 ====================
async function loadArticles(collectionId, collectionName, count) {
    const list = document.getElementById('articlesList');
    const selectedInfo = document.getElementById('selectedInfo');

    selectedInfo.innerHTML = `当前：<strong>${collectionName}</strong>（${count} 篇）`;

    list.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>加载文章列表...</p>
        </div>
    `;

    selectedArticles.clear();
    allArticles = [];

    try {
        const result = await apiRequest(`/api/collections/${collectionId}/articles`);
        allArticles = result.articles || [];

        if (allArticles.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <span class="empty-state-icon">📭</span>
                    <p>收藏夹为空</p>
                </div>
            `;
        } else {
            list.innerHTML = allArticles.map((article, index) => `
                <div class="article-item" data-index="${index}">
                    <input type="checkbox" class="article-checkbox" onchange="toggleArticle(${index})">
                    <div class="article-content">
                        <div class="article-title">${article.title || '无标题'}</div>
                        <div class="article-meta">
                            <span class="article-badge ${article.type}">${article.type === 'answer' ? '回答' : '文章'}</span>
                            <span>👍 ${article.upvotes || 0}</span>
                            <span>💬 ${article.comments || 0}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        updateExportBar();
    } catch (error) {
        list.innerHTML = `
            <div class="empty-state">
                <span class="empty-state-icon">⚠️</span>
                <p>加载失败：${error.message}</p>
            </div>
        `;
        showNotification('获取文章列表失败', 'error');
    }
}

function toggleArticle(index) {
    if (selectedArticles.has(index)) {
        selectedArticles.delete(index);
    } else {
        selectedArticles.add(index);
    }
    updateExportBar();
}

function selectAllArticles() {
    allArticles.forEach((_, index) => selectedArticles.add(index));
    document.querySelectorAll('.article-checkbox').forEach((cb, index) => {
        cb.checked = true;
    });
    updateExportBar();
}

function selectNoneArticles() {
    selectedArticles.clear();
    document.querySelectorAll('.article-checkbox').forEach(cb => {
        cb.checked = false;
    });
    updateExportBar();
}

function selectInverseArticles() {
    allArticles.forEach((_, index) => {
        if (selectedArticles.has(index)) {
            selectedArticles.delete(index);
        } else {
            selectedArticles.add(index);
        }
    });
    document.querySelectorAll('.article-checkbox').forEach((cb, index) => {
        cb.checked = selectedArticles.has(index);
    });
    updateExportBar();
}

function updateExportBar() {
    document.getElementById('selectedCount').textContent = selectedArticles.size;
}

// ==================== 导出功能 ====================
async function startExport() {
    if (!selectedCollection) {
        showNotification('请先选择一个收藏夹', 'error');
        return;
    }

    if (selectedArticles.size === 0) {
        showNotification('请至少选择一篇文章', 'error');
        return;
    }

    // 获取选中的格式
    const formats = Array.from(document.querySelectorAll('input[name="format"]:checked'))
        .map(cb => cb.value);

    if (formats.length === 0) {
        showNotification('请至少选择一种导出格式', 'error');
        return;
    }

    // 获取选中的文章
    const selectedArticleList = Array.from(selectedArticles).map(i => allArticles[i]);

    try {
        const result = await apiRequest('/api/export', {
            method: 'POST',
            body: JSON.stringify({
                collection_id: selectedCollection.id,
                formats: formats,
                articles: selectedArticleList,
                output_dir: outputDir
            })
        });

        showNotification('导出任务已创建', 'success');

        // 跳转到任务页面
        switchPage('tasks');
        pollTaskStatus(result.task_id);
    } catch (error) {
        showNotification(`创建任务失败：${error.message}`, 'error');
    }
}

async function pollTaskStatus(taskId) {
    const poll = async () => {
        try {
            const task = await apiRequest(`/api/tasks/${taskId}`);
            updateTaskCard(task);

            if (task.status === 'pending' || task.status === 'running') {
                setTimeout(poll, 2000);
            }
        } catch (error) {
            console.error('获取任务状态失败:', error);
        }
    };

    poll();
}

function updateTaskCard(task) {
    const tasksList = document.getElementById('tasksList');

    let taskCard = tasksList.querySelector(`[data-task-id="${task.id}"]`);

    if (!taskCard) {
        taskCard = document.createElement('div');
        taskCard.className = 'task-card';
        taskCard.dataset.taskId = task.id;
        tasksList.insertBefore(taskCard, tasksList.firstChild);

        // 移除空状态
        const emptyState = tasksList.querySelector('.empty-state');
        if (emptyState) emptyState.remove();
    }

    const progress = task.total > 0 ? Math.round((task.progress / task.total) * 100) : 0;

    taskCard.innerHTML = `
        <div class="task-header">
            <span class="task-title">导出 ${task.collection_id}</span>
            <span class="task-status ${task.status}">${task.status}</span>
        </div>
        <div class="task-progress">
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
            <div class="progress-info">
                <span>进度：${task.progress} / ${task.total}</span>
                <span>${progress}%</span>
            </div>
        </div>
        <div class="task-stats" style="display: flex; gap: 20px; font-size: 13px;">
            <span style="color: var(--success-color);">✓ 成功：${task.success || 0}</span>
            <span style="color: var(--error-color);">✗ 失败：${task.failed || 0}</span>
        </div>
        ${task.error ? `<div style="color: var(--error-color); margin-top: 12px; font-size: 13px;">错误：${task.error}</div>` : ''}
    `;
}

// ==================== 输出目录 ====================
function updateOutputDir() {
    const input = document.getElementById('outputDirInput');
    outputDir = input.value.trim() || './downloads';
    showNotification(`输出目录已设置为：${outputDir}`, 'success');
}

// 绑定输入框变化事件
document.getElementById('outputDirInput')?.addEventListener('change', updateOutputDir);

// ==================== 页面初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    checkCookie();
    loadCollections();

    // 定时刷新状态
    setInterval(checkCookie, 30000);
});
