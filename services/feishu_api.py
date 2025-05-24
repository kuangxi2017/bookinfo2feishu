# -*- coding: UTF-8 -*-
"""飞书API服务模块，提供与飞书多维表格交互的功能"""

from typing import Optional, Dict, List, Any
import requests
import time
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from config import FeishuConfig
from utils.logger import logger

class FeishuAPI:
    """飞书API操作类，处理与飞书服务器的所有交互

    属性:
        REQUEST_TIMEOUT: 请求超时时间（秒）
        API_BASE_URL: 飞书API基础URL
        TOKEN_EXPIRE_BUFFER: Token过期安全边界时间（秒）
    """
    
    # 类级别常量
    TOKEN_EXPIRE_BUFFER: int = 6600  # 1小时50分钟，确保在2小时过期前刷新
    
    # 飞书字段类型映射
    FIELD_TYPE_MAP: Dict[int, str] = {
        1: "文本",
        2: "数字",
        3: "单选",
        4: "多选",
        5: "日期",
        7: "复选框",
        11: "创建时间",
        12: "最后更新时间",
        15: "附件",
        17: "人员",
        18: "链接",
    }

    def __init__(self):
        """
        初始化飞书API客户端
        
        从AppConfig读取配置并初始化必要的属性和URL
        """
        # 从FeishuConfig读取配置
        self.app_id: str = FeishuConfig.get_config_value("FEISHU_APP_ID") or ""
        self.app_secret: str = FeishuConfig.get_config_value("FEISHU_APP_SECRET") or ""
        self.table_id: str = FeishuConfig.get_config_value("FEISHU_TABLE_ID") or ""
        self.view_id: str = FeishuConfig.get_config_value("FEISHU_VIEW_ID") or ""
        self.app_token: str = FeishuConfig.get_config_value("FEISHU_APP_TOKEN") or ""
        
        # 获取API基础URL和超时设置
        self.api_base_url: str = FeishuConfig.FEISHU_API_BASE_URL
        self.request_timeout: int = FeishuConfig.REQUEST_TIMEOUT
        
        # 构建API URL
        self.base_url: str = f"{self.api_base_url}/bitable/v1/apps/"
        self.upload_url: str = f"{self.api_base_url}/drive/v1/files/upload_all"
        
        # Token相关属性
        self.tenant_access_token: Optional[str] = None
        self.token_expires: float = 0
        
        # 验证配置
        self._validate_config()
        
        # 初始化时获取token
        self._get_tenant_access_token()
        
    def _validate_config(self) -> None:
        """
        验证配置是否有效
        如果缺少必要的配置项，记录警告日志
        """
        if not self.app_id or not self.app_secret:
            logger.warning("飞书API凭证未配置，API调用可能会失败")
        
        if not self.app_token or not self.table_id:
            logger.warning("飞书多维表格配置未完成，数据操作可能会失败")

    def _get_tenant_access_token(self) -> Optional[str]:
        """
        获取飞书 Tenant Access Token
        
        Returns:
            Optional[str]: 成功返回token字符串，失败返回None
        """
        # 检查配置是否完整
        if not self.app_id or not self.app_secret:
            logger.error("无法获取飞书租户访问令牌：缺少应用凭证")
            return None
            
        # 如果令牌未过期，直接返回
        current_time = time.time()
        if self.tenant_access_token and current_time < self.token_expires:
            return self.tenant_access_token

        url = f"{self.api_base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.request_timeout)
            response.raise_for_status()

            result = response.json()
            if result.get('code') != 0:
                logger.error(f"获取飞书 Tenant Access Token 失败: {result.get('msg')}")
                return None

            self.tenant_access_token = result['tenant_access_token']
            # 令牌有效期通常为2小时，这里设置为安全边界时间
            self.token_expires = current_time + self.TOKEN_EXPIRE_BUFFER

            logger.info("成功获取飞书 Tenant Access Token")
            return self.tenant_access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"获取飞书 Tenant Access Token 请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"获取飞书 Tenant Access Token 异常: {e}")
            return None
    
    def get_token(self) -> Optional[str]:
        """
        获取当前有效的访问令牌，如果过期则重新获取
        
        Returns:
            Optional[str]: 成功返回token字符串，失败返回None
        """
        return self._get_tenant_access_token()
    
    def _get_field_type_name(self, type_id: int) -> str:
        """
        获取字段类型的中文名称
        
        Args:
            type_id: 字段类型ID
            
        Returns:
            str: 字段类型的中文名称，未知类型返回'未知类型'
        """
        return self.FIELD_TYPE_MAP.get(type_id, '未知类型')
            
    def get_table_fields(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取指定多维表格的字段列表
        
        Returns:
            Optional[List[Dict[str, Any]]]: 成功返回字段列表，每个字段包含field_id、name、type和type_name，失败返回None
            示例: [{'field_id': 'fldXXX', 'name': '标题', 'type': 1, 'type_name': '文本'}]
        """
        token = self.get_token()
        if not token:
            logger.error("获取 Token 失败，无法获取表头字段")
            return None

        url = f"{self.base_url}{self.app_token}/tables/{self.table_id}/fields"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            response.raise_for_status()  # 如果请求失败则抛出HTTPError
            
            result = response.json()
            if result.get("code") == 0 and result.get("data") and result["data"].get("items"):
                fields_data = []
                for item in result["data"]["items"]:
                    field_type = item.get("type")
                    fields_data.append({
                        "field_id": item.get("field_id"),
                        "name": item.get("field_name"),
                        "type": field_type,  # 数字，例如 1 是文本
                        "type_name": self._get_field_type_name(field_type)  # 将类型数字转为可读名称
                    })
                logger.info(f"成功获取到 {len(fields_data)} 个表头字段")
                return fields_data
            else:
                logger.error(f"获取表头字段失败: {result.get('msg')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求表头字段API异常: {e}")
            return None
        except Exception as e:
            logger.error(f"处理表头字段响应异常: {e}")
            return None

    
    def get_headers(self) -> Optional[Dict[str, str]]:
        """
        获取带有认证信息的请求头
        
        Returns:
            Optional[Dict[str, str]]: 成功返回包含Authorization和Content-Type的请求头字典，失败返回None
        """
        token = self.get_token()
        if not token:
            logger.error("获取token失败，无法生成请求头")
            return None
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
    
    def upload_image(self, image_url: str) -> Optional[str]:
        """
        从URL下载图片并上传到飞书云空间
        
        Args:
            image_url: 图片的URL地址
            
        Returns:
            Optional[str]: 成功返回文件token，失败返回None
        """
        try:
            # 下载图片
            logger.info(f"开始下载图片: {image_url}")
            image_response = requests.get(image_url, timeout=self.request_timeout)
            image_response.raise_for_status()
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False) as fp:
                fp.write(image_response.content)
                file_size = fp.tell()
                fp.seek(0)  # 重置文件指针到开始位置
                
                # 准备上传
                token = self.get_token()
                if not token:
                    logger.error("获取token失败，无法上传图片")
                    return None
                
                # 提取文件名并处理文件类型
                file_name = image_url.split("/")[-1]
                content_type = image_response.headers.get('content-type', 'image/jpeg')
                
                # 构建表单数据
                form = {
                    "file_name": file_name,
                    "parent_type": "bitable_image",
                    "parent_node": self.app_token,
                    "size": str(file_size),
                    "file": (file_name, open(fp.name, 'rb'), content_type)
                }
                
                # 使用MultipartEncoder处理表单数据
                multi_form = MultipartEncoder(form)
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": multi_form.content_type
                }
                
                # 发送请求
                response = requests.post(
                    self.upload_url,
                    data=multi_form,
                    headers=headers,
                    timeout=self.request_timeout
                )
                response.raise_for_status()
                
                result = response.json()
                if result.get('code') != 0:
                    logger.error(f"上传图片失败: {result.get('msg')}")
                    return None
                
                logger.info(f"成功上传图片: {file_name}")
                return result['data']['file_token']
                
        except requests.exceptions.RequestException as e:
            logger.error(f"图片下载或上传请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"上传图片异常: {e}")
            return None
        finally:
            # 清理临时文件
            try:
                if 'fp' in locals() and hasattr(fp, 'name'):
                    import os
                    os.unlink(fp.name)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

    
    def search_book_by_isbn(self, isbn: str) -> Optional[str]:
        """
        根据ISBN查询图书记录
        
        Args:
            isbn: 图书的ISBN编号
            
        Returns:
            Optional[str]: 成功返回记录ID，未找到或失败返回None
        """
        try:
            headers = self.get_headers()
            if not headers:
                logger.error("获取请求头失败，无法查询图书记录")
                return None
            
            query_url = f"{self.base_url}{self.app_token}/tables/{self.table_id}/records"
            filter_param = f"?filter=CurrentValue.[ISBN] = \"{isbn}\""
            
            response = requests.get(
                query_url + filter_param,
                headers=headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') != 0:
                logger.error(f"查询图书记录失败: {result.get('msg')}")
                return None
             
            if result['data']['total'] > 0:
                record_id = result['data']['items'][0]['record_id']
                logger.info(f"找到ISBN为{isbn}的图书记录: {record_id}")
                return record_id
                
            logger.info(f"未找到ISBN为{isbn}的图书记录")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"查询图书记录请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"查询图书记录异常: {e}")
            return None

    def update_book(self, record_id: str, book_data: Dict[str, Any]) -> bool:
        """
        更新图书记录
        
        Args:
            record_id: 要更新的记录ID
            book_data: 要更新的图书数据，格式为 {"fields": {"字段名": "字段值"}}
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        if not record_id or not book_data:
            logger.error("记录ID和图书数据不能为空")
            return False
            
        try:
            headers = self.get_headers()
            if not headers:
                logger.error("获取请求头失败，无法更新图书记录")
                return False
                
            update_url = f"{self.base_url}{self.app_token}/tables/{self.table_id}/records/{record_id}"
            
            response = requests.put(
                update_url,
                json=book_data,
                headers=headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                logger.info(f"成功更新图书记录: {record_id}")
                return True
            else:
                logger.error(f"更新图书记录失败: {result.get('msg')}")
                return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"更新图书记录请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"更新图书记录异常: {e}")
            return False
    
    def create_book(self, book_data: Dict[str, Any]) -> bool:
        """
        创建图书记录
        
        Args:
            book_data: 要创建的图书数据，格式为 {"fields": {"字段名": "字段值"}}
            
        Returns:
            bool: 创建成功返回True，失败返回False
        """
        if not book_data:
            logger.error("图书数据不能为空")
            return False
            
        try:
            headers = self.get_headers()
            if not headers:
                logger.error("获取请求头失败，无法创建图书记录")
                return False
                
            create_url = f"{self.base_url}{self.app_token}/tables/{self.table_id}/records"
            
            response = requests.post(
                create_url,
                json=book_data,
                headers=headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                logger.info("成功创建图书记录")
                return True
            else:
                logger.error(f"创建图书记录失败: {result.get('msg')}")
                return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"创建图书记录请求异常: {e}")
            return False
        except Exception as e:
            logger.error(f"创建图书记录异常: {e}")
            return False