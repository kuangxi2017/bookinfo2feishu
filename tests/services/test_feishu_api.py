# -*- coding: UTF-8 -*-
import unittest
import time
from unittest.mock import patch, MagicMock, mock_open

# Mock logger and config before importing FeishuAPI
mock_feishu_logger = MagicMock()
patch_logger_feishu = patch('utils.logger.logger', mock_feishu_logger)
patch_logger_feishu.start()

# Mock FeishuConfig values used by FeishuAPI constructor
mock_feishu_config_vals = {
    "FEISHU_APP_ID": "test_app_id",
    "FEISHU_APP_SECRET": "test_app_secret",
    "FEISHU_TABLE_ID": "test_table_id",
    "FEISHU_VIEW_ID": "test_view_id", # Optional, but good to have a mock value
    "FEISHU_APP_TOKEN": "test_app_token_for_bitable" # For bitable specific operations
}
mock_feishu_config_static = {
    "FEISHU_API_BASE_URL": "https://mock.feishu.cn/open-apis",
    "REQUEST_TIMEOUT": 10
}

# Patch FeishuConfig.get_config_value and its static attributes
def mock_get_config_value(key):
    return mock_feishu_config_vals.get(key)

patch_feishu_config_get = patch('config.FeishuConfig.get_config_value', side_effect=mock_get_config_value)
patch_feishu_config_get.start()

# Patch static attributes by patching the class itself or its module if necessary.
# For simplicity, we'll assume these are accessed via an instance or directly if possible.
# If they are class-level and accessed directly, we might need more nuanced patching.
patch_feishu_api_base_url = patch('config.FeishuConfig.FEISHU_API_BASE_URL', mock_feishu_config_static["FEISHU_API_BASE_URL"])
patch_feishu_request_timeout = patch('config.FeishuConfig.REQUEST_TIMEOUT', mock_feishu_config_static["REQUEST_TIMEOUT"])
patch_feishu_api_base_url.start()
patch_feishu_request_timeout.start()

from services.feishu_api import FeishuAPI

class TestFeishuAPI(unittest.TestCase):

    def setUp(self):
        """Setup for each test. Re-initialize FeishuAPI for a clean state."""
        # Reset mocks on FeishuAPI instance if it stores state that needs clearing,
        # or create a new instance for each test.
        # For FeishuAPI, token and expiry are instance variables.
        self.feishu_api_instance = FeishuAPI()
        # Clear any cached token to ensure _get_tenant_access_token is tested properly
        self.feishu_api_instance.tenant_access_token = None
        self.feishu_api_instance.token_expires = 0
        mock_feishu_logger.reset_mock()

    def tearDown(self):
        """Clean up after each test if necessary."""
        pass # No specific cleanup needed for FeishuAPI beyond re-init or mock clearing

    @patch('requests.post')
    def test_get_tenant_access_token_success(self, mock_post):
        """Test successful acquisition of tenant access token."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "msg": "success",
            "tenant_access_token": "test_token_123",
            "expire": 7200
        }
        mock_response.raise_for_status = MagicMock() # Ensure it doesn't raise for 2xx
        mock_post.return_value = mock_response

        token = self.feishu_api_instance._get_tenant_access_token()

        self.assertEqual(token, "test_token_123")
        self.assertIsNotNone(self.feishu_api_instance.tenant_access_token)
        self.assertTrue(self.feishu_api_instance.token_expires > time.time())
        mock_post.assert_called_once()
        mock_feishu_logger.info.assert_any_call("Successfully acquired new Feishu Tenant Access Token.")


    @patch('requests.post')
    def test_get_tenant_access_token_api_error(self, mock_post):
        """Test failed token acquisition due to API error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 9999, "msg": "API error"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        token = self.feishu_api_instance._get_tenant_access_token()

        self.assertIsNone(token)
        mock_feishu_logger.error.assert_any_call("Failed to get Feishu Tenant Access Token. API Error Code: 9999, Message: API error")

    @patch('requests.post')
    def test_get_tenant_access_token_network_error(self, mock_post):
        """Test failed token acquisition due to network error."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        with self.assertRaises(requests.exceptions.RequestException):
             self.feishu_api_instance._get_tenant_access_token()
        
        self.assertIsNone(self.feishu_api_instance.tenant_access_token)
        mock_feishu_logger.error.assert_any_call("Request exception while getting Feishu Tenant Access Token: Network error")


    def test_get_tenant_access_token_caching(self):
        """Test that the token is cached and reused if not expired."""
        # Simulate already having a valid token
        self.feishu_api_instance.tenant_access_token = "cached_token_789"
        # Set expiry to be in the future (e.g., TOKEN_EXPIRE_BUFFER seconds from now, minus a bit)
        self.feishu_api_instance.token_expires = time.time() + self.feishu_api_instance.TOKEN_EXPIRE_BUFFER - 100 

        # We don't need to mock requests.post here, as it shouldn't be called
        with patch('requests.post') as mock_post_never_called:
            token = self.feishu_api_instance._get_tenant_access_token()
            self.assertEqual(token, "cached_token_789")
            mock_post_never_called.assert_not_called()
            mock_feishu_logger.debug.assert_any_call("Using existing, valid tenant access token.")

        # Now, simulate token expiry
        self.feishu_api_instance.token_expires = time.time() - 1 # Token has expired
        
        # Setup mock for requests.post again for the new call
        mock_response_new = MagicMock()
        mock_response_new.json.return_value = {
            "code": 0, "msg": "success", "tenant_access_token": "new_token_after_expiry", "expire": 7200
        }
        mock_response_new.raise_for_status = MagicMock()

        with patch('requests.post', return_value=mock_response_new) as mock_post_called_on_expiry:
            new_token = self.feishu_api_instance._get_tenant_access_token()
            self.assertEqual(new_token, "new_token_after_expiry")
            mock_post_called_on_expiry.assert_called_once()


    @patch('requests.get')
    @patch.object(FeishuAPI, 'get_headers') # Mock get_headers as it depends on a valid token
    def test_search_book_by_isbn_found(self, mock_get_headers, mock_get):
        """Test searching for a book by ISBN when the book is found."""
        mock_get_headers.return_value = {"Authorization": "Bearer fake_token"}
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "total": 1,
                "items": [{"record_id": "rec_123abc"}]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        isbn_to_search = "9781234567890"
        record_id = self.feishu_api_instance.search_book_by_isbn(isbn_to_search)

        self.assertEqual(record_id, "rec_123abc")
        mock_get.assert_called_once()
        # Check that the URL and params are correct (simplified check)
        args, kwargs = mock_get.call_args
        self.assertTrue(self.feishu_api_instance.table_id in args[0]) # URL contains table_id
        self.assertEqual(kwargs['params']['filter'], f'CurrentValue.[ISBN] = "{isbn_to_search}"')
        mock_feishu_logger.info.assert_any_call(f"Found book with ISBN {isbn_to_search}, record_id: rec_123abc")


    @patch('requests.get')
    @patch.object(FeishuAPI, 'get_headers')
    def test_search_book_by_isbn_not_found(self, mock_get_headers, mock_get):
        """Test searching for a book by ISBN when the book is not found."""
        mock_get_headers.return_value = {"Authorization": "Bearer fake_token"}
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"total": 0, "items": []}
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        isbn_to_search = "0000000000000"
        record_id = self.feishu_api_instance.search_book_by_isbn(isbn_to_search)

        self.assertIsNone(record_id)
        mock_feishu_logger.info.assert_any_call(f"No book found with ISBN: {isbn_to_search} in table: {self.feishu_api_instance.table_id}")

    @patch('requests.get')
    @patch.object(FeishuAPI, 'get_headers')
    def test_search_book_by_isbn_api_error(self, mock_get_headers, mock_get):
        """Test searching for a book by ISBN with an API error response."""
        mock_get_headers.return_value = {"Authorization": "Bearer fake_token"}
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 5000, "msg": "Internal server error"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        isbn_to_search = "1111111111111"
        record_id = self.feishu_api_instance.search_book_by_isbn(isbn_to_search)

        self.assertIsNone(record_id)
        mock_feishu_logger.error.assert_any_call(f"Failed to search book by ISBN {isbn_to_search}. API Error Code: 5000, Message: Internal server error")

    @patch('requests.get')
    @patch.object(FeishuAPI, 'get_headers')
    def test_search_book_by_isbn_request_exception(self, mock_get_headers, mock_get):
        """Test searching for a book by ISBN with a request exception."""
        mock_get_headers.return_value = {"Authorization": "Bearer fake_token"}
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        isbn_to_search = "2222222222222"
        with self.assertRaises(requests.exceptions.Timeout):
            self.feishu_api_instance.search_book_by_isbn(isbn_to_search)
        
        mock_feishu_logger.error.assert_any_call(f"Request exception while searching for book with ISBN {isbn_to_search}: Request timed out")


# This is to properly stop the patchers if the test is run as a script.
# In a real test suite (e.g., run by `python -m unittest discover`), this isn't necessary
# as patchers are typically managed per test class or module using setUpModule/tearDownModule.
def tearDownModule():
    patch_logger_feishu.stop()
    patch_feishu_config_get.stop()
    patch_feishu_api_base_url.stop()
    patch_feishu_request_timeout.stop()

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    # Manually call tearDownModule if script execution finishes this way
    tearDownModule()
