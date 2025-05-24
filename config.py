# -*- coding: UTF-8 -*-
"""
配置文件
包含应用所需的各种配置参数，如API密钥、URL、超时设置等
"""
import os
import json
from typing import Dict, Any, Optional
from utils.logger import logger

# 注意：AppConfig类已移动到app_config.py

class FeishuConfig:
    """
    飞书API配置
    
    包含与飞书API交互所需的所有配置参数，如应用凭证、API端点等
    支持从配置文件加载和保存配置
    """
    # 配置文件路径
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'feishu_config.json')
    
    # 默认配置
    _DEFAULT_CONFIG = {
        "FEISHU_APP_SECRET": "",  # 飞书后台应用密钥
        "FEISHU_APP_ID": "",      # 飞书后台应用ID
        "FEISHU_APP_TOKEN": "",   # 飞书多维表格应用ID
        "FEISHU_TABLE_ID": "",    # 飞书多维表格书库的表格ID
        "FEISHU_VIEW_ID": "",     # 飞书多维表格视图ID（可选）
    }
    
    # 飞书API基础URL（固定值）
    FEISHU_API_BASE_URL = "https://open.feishu.cn/open-apis"
    
    # 请求超时设置（秒）
    REQUEST_TIMEOUT = 30
    
    # 当前配置
    _config = None
    
    @classmethod
    def load_config(cls) -> None:
        """
        从配置文件加载配置
        如果配置文件不存在，创建默认配置文件
        """
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            
            # 如果配置文件存在，读取配置
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cls._config = json.load(f)
                    logger.info("已从文件加载飞书配置")
            else:
                # 创建默认配置文件
                cls._config = cls._DEFAULT_CONFIG.copy()
                cls.save_config()
                logger.info("已创建默认飞书配置文件")
        except Exception as e:
            logger.error(f"加载飞书配置失败: {e}")
            cls._config = cls._DEFAULT_CONFIG.copy()
    
    @classmethod
    def save_config(cls) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cls._config, f, indent=2, ensure_ascii=False)
            logger.info("已保存飞书配置到文件")
            return True
        except Exception as e:
            logger.error(f"保存飞书配置失败: {e}")
            return False
    
    @classmethod
    def update_config(cls, new_config: Dict[str, Any]) -> bool:
        """
        更新配置
        
        Args:
            new_config: 新的配置字典
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 确保配置已加载
            if cls._config is None:
                cls.load_config()
            
            # 更新配置
            for key, value in new_config.items():
                if key in cls._DEFAULT_CONFIG:
                    cls._config[key] = value
            
            # 保存到文件
            return cls.save_config()
        except Exception as e:
            logger.error(f"更新飞书配置失败: {e}")
            return False
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            Dict[str, Any]: 包含所有飞书配置的字典
        """
        # 确保配置已加载
        if cls._config is None:
            cls.load_config()
        
        return {
            **cls._config,
            "FEISHU_API_BASE_URL": cls.FEISHU_API_BASE_URL,
            "REQUEST_TIMEOUT": cls.REQUEST_TIMEOUT
        }
    
    @classmethod
    def get_config_value(cls, key: str) -> Optional[str]:
        """
        获取指定配置项的值
        
        Args:
            key: 配置项名称
            
        Returns:
            Optional[str]: 配置项的值，如果不存在返回None
        """
        if cls._config is None:
            cls.load_config()
        return cls._config.get(key)


class DoubanConfig:
    """
    豆瓣爬虫配置
    
    包含与豆瓣网站交互所需的配置参数，如User-Agent、API端点等
    """
    # 请求头配置
    USER_AGENT: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    # API端点
    BASE_URL: str = "https://douban.com/isbn/"
    
    # 请求设置
    REQUEST_TIMEOUT: int = 10  # 请求超时时间（秒）
    MAX_RETRIES: int = 3      # 最大重试次数
    RETRY_DELAY: int = 2      # 重试间隔（秒）
