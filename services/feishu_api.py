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

    def __init__(self) -> None:
        """
        Initializes the FeishuAPI client.
        
        This constructor loads necessary configurations from `FeishuConfig` (App ID, App Secret, Table ID, etc.),
        constructs essential API URLs, and initializes token-related attributes.
        It also performs an initial configuration validation and attempts to fetch the tenant access token.
        """
        # Load configuration from FeishuConfig
        self.app_id: str = FeishuConfig.get_config_value("FEISHU_APP_ID") or ""
        self.app_secret: str = FeishuConfig.get_config_value("FEISHU_APP_SECRET") or ""
        self.table_id: str = FeishuConfig.get_config_value("FEISHU_TABLE_ID") or ""
        self.view_id: str = FeishuConfig.get_config_value("FEISHU_VIEW_ID") or "" # Optional for some operations
        self.app_token: str = FeishuConfig.get_config_value("FEISHU_APP_TOKEN") or "" # Specific to the bitable app
        
        # API base URL and request timeout from FeishuConfig
        self.api_base_url: str = FeishuConfig.FEISHU_API_BASE_URL
        self.request_timeout: int = FeishuConfig.REQUEST_TIMEOUT
        
        # Construct specific API endpoints
        self.base_table_url: str = f"{self.api_base_url}/bitable/v1/apps" # Corrected base for bitable operations
        self.upload_url: str = f"{self.api_base_url}/drive/v1/files/upload_all"
        
        # Token related attributes
        self.tenant_access_token: Optional[str] = None
        self.token_expires: float = 0.0 # Using float for time.time() comparison
        
        # Validate configuration on initialization
        self._validate_config()
        
        # Attempt to get token during initialization (optional, can be lazy loaded)
        self._get_tenant_access_token()
        
    def _validate_config(self) -> None:
        """
        Validates essential configurations.
        Logs warnings if necessary configurations are missing, detailing potential impact.
        """
        if not self.app_id or not self.app_secret:
            logger.warning(
                "Feishu App ID (FEISHU_APP_ID) or App Secret (FEISHU_APP_SECRET) is not configured. "
                "Token acquisition and most API calls will fail."
            )
        
        if not self.app_token:
            logger.warning(
                "Feishu App Token (FEISHU_APP_TOKEN) for the multi-dimensional table is not configured. "
                "Operations on table records (create, update, search, get_fields, upload_image to bitable) will fail."
            )

        if not self.table_id:
            logger.warning(
                "Feishu Table ID (FEISHU_TABLE_ID) is not configured. "
                "Operations on table records (create, update, search, get_fields) will fail."
            )

    def _get_tenant_access_token(self) -> Optional[str]:
        """
        Retrieves the Feishu Tenant Access Token.
        If a valid token exists and hasn't expired (considering a buffer), it's returned.
        Otherwise, a new token is requested from the Feishu API.

        Returns:
            Optional[str]: The tenant access token string if successful, otherwise None.
        
        Raises:
            requests.exceptions.RequestException: For network issues or HTTP errors during token request.
        """
        # Check if App ID and App Secret are configured
        if not self.app_id or not self.app_secret:
            logger.error("Cannot acquire Feishu tenant access token: App ID or App Secret is missing.")
            return None
            
        # If token exists and is not about to expire, return it
        current_time: float = time.time()
        if self.tenant_access_token and current_time < self.token_expires:
            logger.debug("Using existing, valid tenant access token.")
            return self.tenant_access_token

        logger.info("Tenant access token is missing or expired, requesting a new one.")
        token_url = f"{self.api_base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(token_url, json=payload, headers=headers, timeout=self.request_timeout)
            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)

            result = response.json()
            if result.get('code') != 0: # Feishu API specific error code
                logger.error(f"Failed to get Feishu Tenant Access Token. API Error Code: {result.get('code')}, Message: {result.get('msg')}")
                return None

            self.tenant_access_token = result.get('tenant_access_token')
            # Feishu token typically expires in 2 hours (7200 seconds).
            # TOKEN_EXPIRE_BUFFER provides a safety margin.
            self.token_expires = current_time + self.TOKEN_EXPIRE_BUFFER 
            # self.token_expires = current_time + result.get('expire', 7200) - 600 # Alternative: use 'expire' from response if available, minus a buffer

            logger.info("Successfully acquired new Feishu Tenant Access Token.")
            return self.tenant_access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception while getting Feishu Tenant Access Token: {e}")
            raise  # Re-raise the exception for the caller to handle or be aware of network issues
        except Exception as e: # Catch other potential errors like JSONDecodeError
            logger.error(f"An unexpected error occurred while getting Feishu Tenant Access Token: {e}")
            return None # Or re-raise depending on desired error handling
    
    def get_token(self) -> Optional[str]:
        """
        Public method to get the current valid tenant access token.
        If the token is expired or not yet fetched, this method handles its acquisition.

        Returns:
            Optional[str]: The tenant access token string if successful, otherwise None.
                           May raise requests.exceptions.RequestException if token acquisition fails due to network issues.
        """
        return self._get_tenant_access_token()
    
    def _get_field_type_name(self, type_id: int) -> str:
        """
        Converts a Feishu field type ID to its human-readable string representation.

        Args:
            type_id: The numeric type ID of the field from Feishu API.

        Returns:
            str: The string name of the field type (e.g., "文本", "数字"), or '未知类型' if the type_id is not mapped.
        """
        return self.FIELD_TYPE_MAP.get(type_id, '未知类型')
            
    def get_table_fields(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves the list of fields (columns) for the configured Feishu multi-dimensional table.

        Returns:
            Optional[List[Dict[str, Any]]]: A list of dictionaries, where each dictionary represents a field
            and contains 'field_id' (str), 'name' (str, field name), 'type' (int, field type ID),
            and 'type_name' (str, human-readable field type). Returns None if the operation fails
            (e.g., token acquisition failure, API error, misconfiguration).
        
        Example of a returned field dictionary:
            {'field_id': 'fldXXX', 'name': '标题', 'type': 1, 'type_name': '文本'}

        Raises:
            requests.exceptions.RequestException: For network issues or HTTP errors during the API call.
        """
        token = self.get_token()
        if not token:
            logger.error("Cannot get table fields: Failed to acquire access token.")
            return None
        if not self.app_token or not self.table_id:
            logger.error("Cannot get table fields: Feishu App Token or Table ID is not configured.")
            return None

        fields_url = f"{self.base_table_url}/{self.app_token}/tables/{self.table_id}/fields"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.info(f"Requesting table fields for table_id: {self.table_id}")
            response = requests.get(fields_url, headers=headers, timeout=self.request_timeout)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0 and result.get("data") and result["data"].get("items"):
                fields_data = []
                for item in result["data"]["items"]:
                    field_type = item.get("type")
                    fields_data.append({
                        "field_id": item.get("field_id"),
                        "name": item.get("field_name"),
                        "type": field_type,
                        "type_name": self._get_field_type_name(field_type or 0) # Ensure field_type is not None
                    })
                logger.info(f"Successfully retrieved {len(fields_data)} table fields.")
                return fields_data
            else:
                logger.error(f"Failed to get table fields. API Error Code: {result.get('code')}, Message: {result.get('msg')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception while getting table fields: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing table fields response: {e}")
            return None
    
    def get_headers(self) -> Optional[Dict[str, str]]:
        """
        Constructs and returns standard request headers including Authorization with the current token.

        Returns:
            Optional[Dict[str, str]]: A dictionary containing 'Authorization' and 'Content-Type' headers
            if a token is successfully obtained. Returns None if token acquisition fails.
        
        Raises:
            requests.exceptions.RequestException: Propagated from `get_token` if token acquisition fails.
        """
        token = self.get_token()
        if not token:
            logger.error("Cannot generate request headers: Failed to acquire access token.")
            return None
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
    
    def upload_image(self, image_url: str) -> Optional[str]:
        """
        Downloads an image from a given URL, uploads it to Feishu Drive (specifically for bitable use),
        and returns the file token.

        Args:
            image_url (str): The URL of the image to download and upload.

        Returns:
            Optional[str]: The file token for the uploaded image if successful, otherwise None.
        
        Raises:
            requests.exceptions.RequestException: For network issues during image download or upload.
        """
        if not self.app_token:
            logger.error("Cannot upload image: Feishu App Token (for bitable) is not configured.")
            return None

        fp_name: Optional[str] = None # To store temp file path for cleanup
        try:
            logger.info(f"Starting image download from: {image_url}")
            image_response = requests.get(image_url, timeout=self.request_timeout, stream=True)
            image_response.raise_for_status()
            
            # Using NamedTemporaryFile with delete=False to ensure it can be opened by path later
            with tempfile.NamedTemporaryFile(delete=False) as fp:
                fp_name = fp.name # Store the name for cleanup
                for chunk in image_response.iter_content(chunk_size=8192):
                    fp.write(chunk)
                file_size = fp.tell()
            
            logger.info(f"Image downloaded to temporary file: {fp_name}, size: {file_size} bytes.")

            token = self.get_token()
            if not token:
                logger.error("Cannot upload image: Failed to acquire access token.")
                return None
            
            file_name = image_url.split("/")[-1] or "untitled_image"
            # Ensure content_type is reasonable, default to jpeg if not available
            content_type = image_response.headers.get('Content-Type', 'image/jpeg')
            
            form_data = {
                "file_name": file_name,
                "parent_type": "bitable_image", # Critical for use in bitable attachments
                "parent_node": self.app_token,  # app_token of the bitable
                "size": str(file_size),
                # file field: (filename, file_object, content_type)
                "file": (file_name, open(fp_name, 'rb'), content_type) 
            }
            
            multi_form = MultipartEncoder(fields=form_data)
            upload_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": multi_form.content_type
            }
            
            logger.info(f"Uploading image '{file_name}' to Feishu Drive.")
            response = requests.post(
                self.upload_url,
                data=multi_form,
                headers=upload_headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            # Close the file explicitly after requests.post is done with it
            form_data['file'][1].close()

            if result.get('code') == 0 and result.get('data') and result['data'].get('file_token'):
                file_token = result['data']['file_token']
                logger.info(f"Successfully uploaded image '{file_name}', file_token: {file_token}")
                return file_token
            else:
                logger.error(f"Failed to upload image. API Error Code: {result.get('code')}, Message: {result.get('msg')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception during image download or upload for {image_url}: {e}")
            if 'form_data' in locals() and form_data['file'][1] and not form_data['file'][1].closed:
                form_data['file'][1].close() # Ensure file is closed on error
            raise
        except IOError as e: # Catch file operation errors
            logger.error(f"IOError during image processing for {image_url}: {e}")
            if 'form_data' in locals() and form_data['file'][1] and not form_data['file'][1].closed:
                form_data['file'][1].close()
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during image upload for {image_url}: {e}")
            if 'form_data' in locals() and form_data['file'][1] and not form_data['file'][1].closed:
                form_data['file'][1].close()
            return None # Or re-raise
        finally:
            if fp_name:
                try:
                    import os
                    if os.path.exists(fp_name):
                        os.unlink(fp_name)
                        logger.debug(f"Successfully cleaned up temporary file: {fp_name}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {fp_name}: {e}")
    
    def search_book_by_isbn(self, isbn: str) -> Optional[str]:
        """
        Searches for a book record in the Feishu table by its ISBN.

        Args:
            isbn (str): The ISBN of the book to search for.

        Returns:
            Optional[str]: The `record_id` of the book if found, otherwise None.
                           Returns None if the operation fails due to API errors, misconfiguration, or network issues.
        
        Raises:
            requests.exceptions.RequestException: For network issues or HTTP errors during the API call.
        """
        if not self.app_token or not self.table_id:
            logger.error("Cannot search book by ISBN: Feishu App Token or Table ID is not configured.")
            return None
        try:
            req_headers = self.get_headers()
            if not req_headers:
                logger.error("Cannot search book by ISBN: Failed to get request headers (token issue).")
                return None
            
            # Ensure self.base_table_url is correctly defined in __init__
            query_url = f"{self.base_table_url}/{self.app_token}/tables/{self.table_id}/records"
            # Feishu API requires filter parameters to be URL encoded if they contain special characters,
            # but for simple strings like ISBN, direct inclusion is often fine.
            # However, using params argument of requests.get is safer.
            params = {'filter': f'CurrentValue.[ISBN] = "{isbn}"'}
            if self.view_id: # Optionally filter by view_id if configured
                params['view_id'] = self.view_id

            logger.info(f"Searching for book with ISBN: {isbn} in table: {self.table_id}")
            response = requests.get(
                query_url,
                params=params,
                headers=req_headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') != 0:
                logger.error(f"Failed to search book by ISBN {isbn}. API Error Code: {result.get('code')}, Message: {result.get('msg')}")
                return None
             
            if result.get('data') and result['data'].get('total', 0) > 0 and result['data'].get('items'):
                record_id = result['data']['items'][0]['record_id']
                logger.info(f"Found book with ISBN {isbn}, record_id: {record_id}")
                return record_id
                
            logger.info(f"No book found with ISBN: {isbn} in table: {self.table_id}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception while searching for book with ISBN {isbn}: {e}")
            raise
        except Exception as e: # Catch other potential errors like JSONDecodeError
            logger.error(f"An unexpected error occurred while searching for book with ISBN {isbn}: {e}")
            return None

    def update_book(self, record_id: str, book_data: Dict[str, Any]) -> bool:
        """
        Updates an existing book record in the Feishu table.

        Args:
            record_id (str): The ID of the record to update.
            book_data (Dict[str, Any]): A dictionary containing the data to update.
                                       Expected format: `{"fields": {"FieldName1": "NewValue1", ...}}`.

        Returns:
            bool: True if the update was successful, False otherwise.
        
        Raises:
            requests.exceptions.RequestException: For network issues or HTTP errors during the API call.
        """
        if not record_id:
            logger.error("Cannot update book: Record ID is missing.")
            return False
        if not book_data or "fields" not in book_data:
            logger.error("Cannot update book: Book data is missing or not in the correct format {'fields': {...}}.")
            return False
        if not self.app_token or not self.table_id:
            logger.error("Cannot update book: Feishu App Token or Table ID is not configured.")
            return False
            
        try:
            req_headers = self.get_headers()
            if not req_headers:
                logger.error("Cannot update book: Failed to get request headers (token issue).")
                return False
                
            update_url = f"{self.base_table_url}/{self.app_token}/tables/{self.table_id}/records/{record_id}"
            
            logger.info(f"Updating book record_id: {record_id} in table: {self.table_id}")
            response = requests.put(
                update_url,
                json=book_data,
                headers=req_headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                logger.info(f"Successfully updated book record_id: {record_id}")
                return True
            else:
                logger.error(f"Failed to update book record_id {record_id}. API Error Code: {result.get('code')}, Message: {result.get('msg')}")
                return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception while updating book record_id {record_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while updating book record_id {record_id}: {e}")
            return False
    
    def create_book(self, book_data: Dict[str, Any]) -> bool:
        """
        Creates a new book record in the Feishu table.

        Args:
            book_data (Dict[str, Any]): A dictionary containing the data for the new record.
                                       Expected format: `{"fields": {"FieldName1": "Value1", ...}}`.

        Returns:
            bool: True if the creation was successful, False otherwise.
        
        Raises:
            requests.exceptions.RequestException: For network issues or HTTP errors during the API call.
        """
        if not book_data or "fields" not in book_data:
            logger.error("Cannot create book: Book data is missing or not in the correct format {'fields': {...}}.")
            return False
        if not self.app_token or not self.table_id:
            logger.error("Cannot create book: Feishu App Token or Table ID is not configured.")
            return False
            
        try:
            req_headers = self.get_headers()
            if not req_headers:
                logger.error("Cannot create book: Failed to get request headers (token issue).")
                return False
                
            create_url = f"{self.base_table_url}/{self.app_token}/tables/{self.table_id}/records"
            
            logger.info(f"Creating new book record in table: {self.table_id}")
            response = requests.post(
                create_url,
                json=book_data,
                headers=req_headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                # Optionally, log the new record_id if available in response: result.get('data', {}).get('record', {}).get('record_id')
                logger.info(f"Successfully created new book record. Response: {result.get('data', {})}")
                return True
            else:
                logger.error(f"Failed to create book record. API Error Code: {result.get('code')}, Message: {result.get('msg')}")
                return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception while creating book record: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while creating book record: {e}")
            return False