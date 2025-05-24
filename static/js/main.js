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
    const tableIdInput = document.getElementById('table-id');
    const viewIdInput = document.getElementById('view-id');

    // 加载已保存的配置
    loadConfig();

    // 处理ISBN提交
    submitBtn.addEventListener('click', async () => {
        const isbn = isbnInput.value.trim();
        if (!isbn) {
            showMessage('请输入 ISBN', 'error');
            return;
        }
        showMessage('正在处理...', 'info');
        bookInfoArea.innerHTML = '';

        try {
            const response = await fetch(`/isbn?isbn=${encodeURIComponent(isbn)}`);
            const data = await response.json();

            if (response.ok) {
                showMessage(data.message, 'success');
                if (data.book_info) {
                    displayBookInfo(data.book_info);
                }
            } else {
                showMessage(data.message || '处理失败', 'error');
            }
        } catch (error) {
            console.error('请求失败:', error);
            showMessage('请求失败，请检查网络连接或服务器状态。', 'error');
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
            table_id: tableIdInput.value.trim(),
            view_id: viewIdInput.value.trim(),
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
        for (const key in book) {
            if (book.hasOwnProperty(key) && key !== 'book_name' && key !== 'image_token') {
                html += `<p><strong>${translateKey(key)}:</strong> ${book[key]}</p>`;
            }
        }
        bookInfoArea.innerHTML = html;
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
});