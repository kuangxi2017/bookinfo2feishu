# -*- coding: UTF-8 -*-
# 飞书API服务

import requests
import time
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from config import FeishuConfig
from utils.logger import logger

class FeishuAPI:
    """飞书API操作类"""
    def __init__(self):
        self.config = FeishuConfig()
        self.token = None
        self.token_expires = 0
    
    def get_token(self):
        """获取飞书API访问令牌"""
        # 如果令牌未过期，直接返回
        current_time = time.time()
        if self.token and current_time < self.token_expires:
            return self.token
            
        try:
            headers = {"Content-Type": "application/json; charset=utf-8"}
            payload = {
                "app_id": self.config.APP_ID,
                "app_secret": self.config.APP_SECRET
            }
            
            response = requests.post(self.config.TOKEN_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') != 0:
                logger.error(f"获取飞书令牌失败: {result.get('msg')}")
                return None
                
            self.token = result['tenant_access_token']
            # 令牌有效期通常为2小时，这里设置为1小时50分钟以确保安全
            self.token_expires = current_time + 6600  # 1小时50分钟 = 6600秒
            
            return self.token
        except Exception as e:
            logger.error(f"获取飞书令牌异常: {e}")
            return None
    
    def get_headers(self):
        """获取带有认证信息的请求头"""
        token = self.get_token()
        if not token:
            return None
            
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
    
    def upload_image(self, image_url):
        """上传图片到飞书云空间"""
        try:
            # 下载图片
            image_response = requests.get(image_url, timeout=10)
            image_response.raise_for_status()
            
            # 创建临时文件
            with tempfile.TemporaryFile() as fp:
                fp.write(image_response.content)
                file_size = fp.tell()
                fp.seek(0)  # 重置文件指针到开始位置
                
                # 准备上传
                token = self.get_token()
                if not token:
                    return None
                    
                # 提取文件名
                file_name = image_url.split("/")[-1]
                
                # 构建表单数据
                form = {
                    "file_name": file_name,
                    "parent_type": "bitable_image",
                    "parent_node": self.config.APP_TOKEN,
                    "size": str(file_size),
                    "file": (fp.read())
                }
                
                # 使用MultipartEncoder处理表单数据
                multi_form = MultipartEncoder(form)
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": multi_form.content_type
                }
                
                # 发送请求
                response = requests.post(self.config.UPLOAD_URL, data=multi_form, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                if result.get('code') != 0:
                    logger.error(f"上传图片失败: {result.get('msg')}")
                    return None
                    
                return result['data']['file_token']
                
        except Exception as e:
            logger.error(f"上传图片异常: {e}")
            return None
    
    def search_book_by_isbn(self, isbn):
        """根据ISBN查询图书记录"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            query_url = f"{self.config.BASE_URL}{self.config.APP_TOKEN}/tables/{self.config.TABLE_ID}/records"
            filter_param = f"?filter=CurrentValue.[ISBN] = \"{isbn}\""
            
            response = requests.get(query_url + filter_param, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') != 0:
                logger.error(f"查询图书记录失败: {result.get('msg')}")
                return None
                
            if result['data']['total'] > 0:
                return result['data']['items'][0]['record_id']
            return None
            
        except Exception as e:
            logger.error(f"查询图书记录异常: {e}")
            return None
    
    def update_book(self, record_id, book_data):
        """更新图书记录"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
                
            update_url = f"{self.config.BASE_URL}{self.config.APP_TOKEN}/tables/{self.config.TABLE_ID}/records/{record_id}"
            
            response = requests.put(update_url, json=book_data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result.get('code') == 0
            
        except Exception as e:
            logger.error(f"更新图书记录异常: {e}")
            return False
    
    def create_book(self, book_data):
        """创建图书记录"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
                
            create_url = f"{self.config.BASE_URL}{self.config.APP_TOKEN}/tables/{self.config.TABLE_ID}/records"
            
            response = requests.post(create_url, json=book_data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result.get('code') == 0
            
        except Exception as e:
            logger.error(f"创建图书记录异常: {e}")
            return False