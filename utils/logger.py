# -*- coding: UTF-8 -*-
# 日志工具模块

import logging
import os

# 配置日志
def setup_logger():
    """设置并返回日志记录器"""
    from app_config import AppConfig  # 从新的app_config模块导入
    
    # 创建日志记录器
    logger = logging.getLogger('bookinfo2feishu')
    logger.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 确保日志目录存在
    log_dir = os.path.dirname(AppConfig.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(AppConfig.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# 创建全局日志记录器实例
logger = setup_logger()