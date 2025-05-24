# -*- coding: UTF-8 -*-
"""
应用全局配置

包含应用特定的配置项，并提供访问FeishuConfig的方法
"""
import os
from typing import Dict, Any


class AppConfig:
    """
    应用全局配置
    
    包含应用特定的配置项，并提供访问FeishuConfig的方法
    """
    # 服务器配置
    HOST: str = '0.0.0.0'
    PORT: int = 80
    DEBUG: bool = True
    
    # 日志配置
    LOG_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    LOG_FILE: str = os.path.join(LOG_DIR, 'app.log')
    LOG_LEVEL: str = 'INFO'
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'
    
    # 缓存配置
    CACHE_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
    CACHE_TIMEOUT: int = 3600  # 缓存过期时间（秒）
    
    # 配置目录
    CONFIG_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
    
    @classmethod
    def ensure_directories(cls) -> None:
        """
        确保所需的目录存在
        创建日志、缓存和配置目录（如果不存在）
        """
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        os.makedirs(cls.CONFIG_DIR, exist_ok=True)
    
    @classmethod
    def initialize(cls) -> None:
        """
        初始化应用配置
        加载飞书配置并确保目录存在
        """
        cls.ensure_directories()
        from config import FeishuConfig
        FeishuConfig.load_config()
    
    # 飞书配置代理方法
    @classmethod
    def get_feishu_config(cls) -> Dict[str, Any]:
        """
        获取飞书配置
        
        Returns:
            Dict[str, Any]: 飞书配置字典
        """
        from config import FeishuConfig
        return FeishuConfig.get_config()
    
    @classmethod
    def update_feishu_config(cls, new_config: Dict[str, Any]) -> bool:
        """
        更新飞书配置
        
        Args:
            new_config: 新的飞书配置
            
        Returns:
            bool: 更新是否成功
        """
        from config import FeishuConfig
        return FeishuConfig.update_config(new_config)
    
    # 飞书配置属性代理
    @classmethod
    def get_feishu_app_id(cls) -> str:
        """获取飞书应用ID"""
        from config import FeishuConfig
        return FeishuConfig.get_config_value("FEISHU_APP_ID") or ""
    
    @classmethod
    def get_feishu_app_secret(cls) -> str:
        """获取飞书应用密钥"""
        from config import FeishuConfig
        return FeishuConfig.get_config_value("FEISHU_APP_SECRET") or ""
    
    @classmethod
    def get_feishu_app_token(cls) -> str:
        """获取飞书应用Token"""
        from config import FeishuConfig
        return FeishuConfig.get_config_value("FEISHU_APP_TOKEN") or ""
    
    @classmethod
    def get_feishu_table_id(cls) -> str:
        """获取飞书表格ID"""
        from config import FeishuConfig
        return FeishuConfig.get_config_value("FEISHU_TABLE_ID") or ""
    
    @classmethod
    def get_feishu_view_id(cls) -> str:
        """获取飞书视图ID"""
        from config import FeishuConfig
        return FeishuConfig.get_config_value("FEISHU_VIEW_ID") or ""
    
    @classmethod
    def get_feishu_api_base_url(cls) -> str:
        """获取飞书API基础URL"""
        from config import FeishuConfig
        return FeishuConfig.FEISHU_API_BASE_URL
    
    @classmethod
    def get_request_timeout(cls) -> int:
        """获取请求超时设置"""
        from config import FeishuConfig
        return FeishuConfig.REQUEST_TIMEOUT