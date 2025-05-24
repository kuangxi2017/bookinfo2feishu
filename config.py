# -*- coding: UTF-8 -*-
# 配置文件
import os

class FeishuConfig:
    """飞书API配置"""
    # 飞书API凭证
    APP_SECRET = 'xK98NNReR2YqwO7V62jRidlt41qzqGz0'  # 飞书后台应用token
    APP_ID = 'cli_a246770639f8900c'                  # 飞书后台应用的id
    APP_TOKEN = 'NzmMbjG8Ga9W76spBrzc6DfKnhb'         # 飞书多维表格的id
    TABLE_ID = 'tblQp2OQgxamLR3x'                    # 飞书多维表格书库的表格id
    
    # 飞书API URL
    TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"    # 飞书获取token的url
    UPLOAD_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"    # 飞书上传图片的url
    BASE_URL = "https://open.feishu.cn/open-apis/bitable/v1/apps/"     # 飞书多维表格应用的url

class DoubanConfig:
    """豆瓣爬虫配置"""
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    BASE_URL = "https://douban.com/isbn/"
    REQUEST_TIMEOUT = 10  # 请求超时时间（秒）

class AppConfig:
    """应用配置"""
    HOST = '0.0.0.0'
    PORT = 80
    DEBUG = False
    THREADED = True
    
    # 日志配置
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'app.log')