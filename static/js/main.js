document.addEventListener('DOMContentLoaded', () => {
    const isbnInput = document.getElementById('isbn-input');
    const submitBtn = document.getElementById('submit-isbn-btn');
    const messageArea = document.getElementById('message-area');
    const bookInfoArea = document.getElementById('book-info-area');

    const configBtn = document.getElementById('config-btn');
    const configDrawer = document.getElementById('config-drawer');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const saveConfigBtn = document.getElementById('save-config-btn');
    const fetchFieldsBtn = document.getElementById('fetch-fields-btn');
    const fieldsMappingArea = document.getElementById('fields-mapping-area');

    const appIdInput = document.getElementById('app-id');
    const appSecretInput = document.getElementById('app-secret');
    const appTokenInput = document.getElementById('app-token');
    const tableIdInput = document.getElementById('table-id');

    // 加载已保存的配置
    loadConfig();

    // 处理ISBN提交
    submitBtn.addEventListener('click', async () => {
        const isbn = isbnInput.value.trim();
        if (!isbn) {
            showMessage('请输入 ISBN', 'error');
            return;
        }
        showMessage('正在获取书籍信息...', 'info');
        bookInfoArea.innerHTML = '';

        try {
            const response = await fetch(`/get_book_info?isbn=${encodeURIComponent(isbn)}`);
            const data = await response.json();

            if (response.ok) {
                showMessage(data.message, 'success');
                if (data.book_info) {
                    displayBookInfo(data.book_info);
                    // 隐藏 ISBN 输入框和按钮
                    isbnInput.style.display = 'none';
                    submitBtn.style.display = 'none';
                }
            } else {
                showMessage(data.message || '获取书籍信息失败', 'error');
            }
        } catch (error) {
            console.error('获取书籍信息失败:', error);
            showMessage('获取书籍信息失败，请检查网络连接或服务器状态。', 'error');
        }
    });

    // 打开配置抽屉
    configBtn.addEventListener('click', () => {
        configDrawer.classList.add('open');
    });

    // 关闭配置抽屉
    closeDrawerBtn.addEventListener('click', () => {
        configDrawer.classList.remove('open');
    });

    // 点击抽屉外部关闭 (可选)
    document.addEventListener('click', (event) => {
        if (configDrawer.classList.contains('open') && !configDrawer.contains(event.target) && event.target !== configBtn) {
            // configDrawer.classList.remove('open'); // 如果希望点击外部关闭，取消此行注释
        }
    });

    // 保存配置
    saveConfigBtn.addEventListener('click', async () => {
        const config = {
            app_id: appIdInput.value.trim(),
            app_secret: appSecretInput.value.trim(),
            app_token: appTokenInput.value.trim(),
            table_id: tableIdInput.value.trim(),
        };

        try {
            const response = await fetch('/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config),
            });
            const data = await response.json();
            if (response.ok) {
                showMessage('配置已保存', 'success');
                localStorage.setItem('feishuConfig', JSON.stringify(config)); // 同时保存到localStorage
            } else {
                showMessage(data.message || '保存配置失败', 'error');
            }
        } catch (error) {
            console.error('保存配置失败:', error);
            showMessage('保存配置失败，请检查网络连接或服务器状态。', 'error');
        }
    });

    // 获取飞书表头字段
    fetchFieldsBtn.addEventListener('click', async () => {
        showMessage('正在获取表头字段...', 'info');
        fieldsMappingArea.innerHTML = '加载中...';
        try {
            const response = await fetch('/feishu_fields');
            const data = await response.json();

            if (response.ok && data.fields) {
                displayFeishuFields(data.fields);
                showMessage('表头字段获取成功', 'success');
            } else {
                showMessage(data.message || '获取表头字段失败', 'error');
                fieldsMappingArea.innerHTML = '获取失败';
            }
        } catch (error) {
            console.error('获取表头字段失败:', error);
            showMessage('获取表头字段失败，请检查网络连接或服务器状态。', 'error');
            fieldsMappingArea.innerHTML = '获取失败';
        }
    });

    function showMessage(message, type = 'info') {
        messageArea.textContent = message;
        messageArea.className = type; // 'info', 'success', 'error'
    }

    function displayBookInfo(book) {
        let html = `<h3>${book.book_name}</h3>`;
        let fieldsHtml = '';
        
        // 显示书籍信息
        for (const key in book) {
            if (book.hasOwnProperty(key) && key !== 'book_name' && key !== 'image_token') {
                html += `<p><strong>${translateKey(key)}:</strong> ${book[key]}</p>`;
                fieldsHtml += `<div class="field-mapping">
                    <span>${translateKey(key)}</span>
                    <select id="map-${key}" class="field-select">
                        <option value="">不映射</option>
                    </select>
                    <span id="map-status-${key}" class="map-status"></span>
                </div>`;
            }
        }
        
        // 添加映射配置区域
        html += `
            <div class="mapping-section">
                <h4>字段映射配置</h4>
                <p>请为每个需要同步的字段选择对应的飞书字段</p>
                ${fieldsHtml}
                <div class="mapping-actions">
                    <button id="save-mapping-btn" class="mapping-button">保存映射配置</button>
                    <button id="sync-now-btn" class="sync-button">立即同步</button>
                </div>
                <div id="mapping-summary" class="mapping-summary"></div>
            </div>
        `;
        
        bookInfoArea.innerHTML = html;
        
        // 加载飞书字段选项
        loadFeishuFieldOptions().then(() => {
            updateMappingStatus();
        });
        
        // 添加保存映射事件
        document.getElementById('save-mapping-btn').addEventListener('click', () => {
            saveFieldMapping();
            updateMappingStatus();
        });
        
        document.getElementById('sync-now-btn').addEventListener('click', () => {
            if (validateMappings()) {
                syncBookInfo(book);
            }
        });
        
        // 添加字段选择变化事件
        document.querySelectorAll('.field-select').forEach(select => {
            select.addEventListener('change', updateMappingStatus);
        });
    }

    function updateMappingStatus() {
        let mappedCount = 0;
        const selects = document.querySelectorAll('.field-select');
        
        selects.forEach(select => {
            const fieldName = select.id.replace('map-', '');
            const statusElement = document.getElementById(`map-status-${fieldName}`);
            
            if (select.value) {
                statusElement.textContent = '✓';
                statusElement.className = 'map-status mapped';
                mappedCount++;
            } else {
                statusElement.textContent = '×';
                statusElement.className = 'map-status not-mapped';
            }
        });
        
        const summaryElement = document.getElementById('mapping-summary');
        summaryElement.innerHTML = `已配置 ${mappedCount}/${selects.length} 个字段映射`;
        summaryElement.className = mappedCount > 0 ? 'mapping-summary has-mappings' : 'mapping-summary no-mappings';
    }

    function validateMappings() {
        const selects = document.querySelectorAll('.field-select');
        let hasMappings = false;
        
        selects.forEach(select => {
            if (select.value) {
                hasMappings = true;
            }
        });
        
        if (!hasMappings) {
            showMessage('请至少配置一个字段映射', 'error');
            return false;
        }
        return true;
    }

    function translateKey(key) {
        const map = {
            author_name: '作者',
            press: '出版社',
            publish_date: '出版日期',
            pages: '页数',
            price: '定价',
            ISBN: 'ISBN',
            brand: '出品方',
            series: '丛书',
            design: '装帧',
            score: '豆瓣评分',
            url: '豆瓣链接',
            translator: '译者'
        };
        return map[key] || key;
    }

    function loadConfig() {
        const savedConfig = localStorage.getItem('feishuConfig');
        if (savedConfig) {
            try {
                const config = JSON.parse(savedConfig);
                appIdInput.value = config.app_id || '';
                appSecretInput.value = config.app_secret || '';
                appTokenInput.value = config.app_token || '';
                tableIdInput.value = config.table_id || '';
                viewIdInput.value = config.view_id || '';
            } catch (e) {
                console.error('无法解析存储的配置:', e);
                localStorage.removeItem('feishuConfig');
            }
        }
    }

    function displayFeishuFields(fields) {
        if (!fields || fields.length === 0) {
            fieldsMappingArea.innerHTML = '未找到字段信息。';
            return;
        }
        let html = '<h4>可用字段:</h4>';
        fields.forEach(field => {
            html += `<div><strong>${field.name}</strong> (ID: ${field.field_id}, 类型: ${field.type_name})</div>`;
        });
        fieldsMappingArea.innerHTML = html;
    }

    // 加载飞书字段到映射选择器
    async function loadFeishuFieldOptions() {
        try {
            const response = await fetch('/feishu_fields');
            const data = await response.json();
            
            if (response.ok && data.fields) {
                const selects = document.querySelectorAll('.field-select');
                selects.forEach(select => {
                    // 保留"不映射"选项
                    while (select.options.length > 1) {
                        select.remove(1);
                    }
                    
                    // 添加飞书字段选项
                    data.fields.forEach(field => {
                        const option = document.createElement('option');
                        option.value = field.field_id;
                        // 修改此处，显示字段名称和类型
                        option.textContent = `${field.name} (${field.type_name})`;
                        select.appendChild(option);
                    });
                    
                    // 加载已保存的映射
                    const savedMappings = JSON.parse(localStorage.getItem('fieldMappings') || '{}');
                    if (savedMappings[select.id.replace('map-', '')]) {
                        select.value = savedMappings[select.id.replace('map-', '')];
                    }
                });
            }
        } catch (error) {
            console.error('加载飞书字段失败:', error);
            showMessage('加载飞书字段失败，请检查网络连接或服务器状态。', 'error');
        }
    }

    // 保存字段映射配置
    function saveFieldMapping() {
        const mappings = {};
        const selects = document.querySelectorAll('.field-select');
        
        selects.forEach(select => {
            const fieldName = select.id.replace('map-', '');
            mappings[fieldName] = select.value;
        });
        
        localStorage.setItem('fieldMappings', JSON.stringify(mappings));
        showMessage('字段映射配置已保存', 'success');
    }

    // 同步书籍信息到飞书
    async function syncBookInfo(book) {
        showMessage('正在同步到飞书...', 'info');
        
        // 收集映射配置
        const mappings = {};
        const selects = document.querySelectorAll('.field-select');
        selects.forEach(select => {
            const fieldName = select.id.replace('map-', '');
            if (select.value) { // 仅同步已选择映射的字段
                mappings[fieldName] = select.value;
            }
        });
        
        // 准备同步数据
        const syncData = {
            book_info: book,
            field_mappings: mappings
        };
        
        try {
            const response = await fetch('/sync_to_feishu', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(syncData),
            });
            const data = await response.json();
            
            if (response.ok) {
                showMessage(data.message || '同步成功', 'success');
                // 同步成功后重置表单
                isbnInput.style.display = '';
                submitBtn.style.display = '';
                isbnInput.value = '';
                bookInfoArea.innerHTML = '';
            } else {
                showMessage(data.message || '同步失败', 'error');
            }
        } catch (error) {
            console.error('同步失败:', error);
            showMessage('同步失败，请检查网络连接或服务器状态。', 'error');
        }
    }
});


function saveConfigToLocalStorage(config) {
    localStorage.setItem('apiConfig', JSON.stringify(config));
}

function loadConfigFromLocalStorage() {
    const config = localStorage.getItem('apiConfig');
    return config ? JSON.parse(config) : null;
}

// 在保存配置时调用保存到缓存的函数
function saveConfig() {
    const config = {
        appId: document.getElementById('appId').value,
        appSecret: document.getElementById('appSecret').value,
        token: document.getElementById('token').value,
        tableId: document.getElementById('tableId').value
    };
    saveConfigToLocalStorage(config);
    // ... existing code ...
}

// 在页面加载时调用从缓存加载配置的函数
window.onload = function() {
    const config = loadConfigFromLocalStorage();
    if (config) {
        document.getElementById('appId').value = config.appId;
        document.getElementById('appSecret').value = config.appSecret;
        document.getElementById('token').value = config.token;
        document.getElementById('tableId').value = config.tableId;
    }
    // ... existing code ...
}