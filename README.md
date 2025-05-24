# 豆瓣图书信息同步到飞书

这是一个将豆瓣图书信息同步到飞书多维表格的应用程序。

## 项目结构

```
.
├── README.md                 # 项目说明文档
├── requirements.txt          # 项目依赖
├── config.py                # 配置文件
├── utils/                   # 工具类
│   ├── __init__.py
│   └── logger.py            # 日志工具
├── services/                # 服务层
│   ├── __init__.py
│   ├── douban_scraper.py    # 豆瓣爬虫服务
│   └── feishu_api.py        # 飞书API服务
└── app.py                   # 主应用入口
```

## 功能

- 通过ISBN获取豆瓣图书信息
- 将图书信息同步到飞书多维表格
- 支持图书信息的创建和更新
- 支持图书封面的上传

## 使用方法

1. 安装依赖：`pip install -r requirements.txt`
2. 运行应用：`python app.py`
3. 访问API：`http://localhost:80/isbn?isbn=<ISBN号码>`