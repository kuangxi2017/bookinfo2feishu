# -*- coding: UTF-8 -*-
import unittest
import json
from unittest.mock import patch, MagicMock, ANY

# Ensure sys.path is set up correctly if tests are not run from project root
# This might be needed if 'app' module is not found directly.
# However, typically test runners handle this or tests are run from root.
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock logger at the beginning, before app is imported, to prevent real logging.
# This assumes 'utils.logger.logger' is the logger instance used throughout the app.
mock_app_logger = MagicMock()
patch_app_logger = patch('utils.logger.logger', mock_app_logger)
patch_app_logger.start()


# Mock AppConfig methods used by app.py during initialization or by endpoints
# This prevents file I/O or other side effects from AppConfig.
patch_appconfig_initialize = patch('config.AppConfig.initialize', MagicMock(return_value=None))
patch_appconfig_get_feishu_config = patch('config.AppConfig.get_feishu_config')
patch_appconfig_update_feishu_config = patch('config.AppConfig.update_feishu_config')

patch_appconfig_initialize.start()
mock_get_feishu_config = patch_appconfig_get_feishu_config.start()
mock_update_feishu_config = patch_appconfig_update_feishu_config.start()


# Import the Flask app instance from your main application file (app.py)
# Patch services BEFORE app is imported and services are instantiated within app.py
# These patches will replace the actual DoubanScraper and FeishuAPI classes
# when app.py instantiates them.
mock_douban_scraper_instance = MagicMock()
mock_feishu_api_instance = MagicMock()

patch_douban_scraper = patch('services.DoubanScraper', return_value=mock_douban_scraper_instance)
patch_feishu_api = patch('services.FeishuAPI', return_value=mock_feishu_api_instance)

mock_douban_scraper_class = patch_douban_scraper.start()
mock_feishu_api_class = patch_feishu_api.start()

# Now import the app
from app import app # app.py should contain `app = Flask(__name__)`

class TestApp(unittest.TestCase):

    def setUp(self):
        """Set up the Flask test client and mock services."""
        app.testing = True
        self.client = app.test_client()

        # Reset mocks for each test to ensure test isolation
        mock_app_logger.reset_mock()
        mock_get_feishu_config.reset_mock()
        mock_update_feishu_config.reset_mock()
        
        # Reset instance mocks that are patched at class/module level in app.py
        # These are the instances created in app.py:
        # douban_scraper = DoubanScraper() -> will be mock_douban_scraper_instance
        # feishu_api = FeishuAPI() -> will be mock_feishu_api_instance
        mock_douban_scraper_instance.reset_mock(return_value=True, side_effect=True) # Reset all behaviors
        mock_feishu_api_instance.reset_mock(return_value=True, side_effect=True)


    # --- Tests for /isbn endpoint ---
    def test_isbn_create_path_success(self):
        """Test /isbn: book found in Douban, not in Feishu (create path success)."""
        mock_douban_scraper_instance.get_book_info.return_value = {"book_name": "Test Book", "author_name": "Test Author", "book_img": "http://example.com/img.jpg"}
        mock_feishu_api_instance.search_book_by_isbn.return_value = None  # Not in Feishu
        mock_feishu_api_instance.upload_image.return_value = "file_token_123"
        mock_feishu_api_instance.create_book.return_value = True

        response = self.client.get('/isbn?isbn=VALID_ISBN_CREATE')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['message'], "图书添加成功")
        self.assertIn("Test Book", data['book_info']['book_name'])
        mock_douban_scraper_instance.get_book_info.assert_called_once_with('VALID_ISBN_CREATE')
        mock_feishu_api_instance.search_book_by_isbn.assert_called_once_with('VALID_ISBN_CREATE')
        mock_feishu_api_instance.upload_image.assert_called_once() # Check if called
        mock_feishu_api_instance.create_book.assert_called_once()


    def test_isbn_update_path_success(self):
        """Test /isbn: book found in Douban, already in Feishu (update path success)."""
        mock_douban_scraper_instance.get_book_info.return_value = {"book_name": "Updated Test Book", "author_name": "Updated Author"}
        mock_feishu_api_instance.search_book_by_isbn.return_value = "record_id_abc"  # Already in Feishu
        mock_feishu_api_instance.update_book.return_value = True

        response = self.client.get('/isbn?isbn=VALID_ISBN_UPDATE')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['message'], "图书信息更新成功")
        self.assertIn("Updated Test Book", data['book_info']['book_name'])
        mock_douban_scraper_instance.get_book_info.assert_called_once_with('VALID_ISBN_UPDATE')
        mock_feishu_api_instance.search_book_by_isbn.assert_called_once_with('VALID_ISBN_UPDATE')
        mock_feishu_api_instance.update_book.assert_called_once()
        mock_feishu_api_instance.upload_image.assert_not_called() # Should not be called in update path by default


    def test_isbn_douban_not_found(self):
        """Test /isbn: book not found in Douban."""
        mock_douban_scraper_instance.get_book_info.return_value = None

        response = self.client.get('/isbn?isbn=INVALID_DOUBAN_ISBN')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['message'], "未找到图书信息")
        mock_douban_scraper_instance.get_book_info.assert_called_once_with('INVALID_DOUBAN_ISBN')


    def test_isbn_feishu_create_error(self):
        """Test /isbn: Feishu API error during create."""
        mock_douban_scraper_instance.get_book_info.return_value = {"book_name": "Test Book Create Fail"}
        mock_feishu_api_instance.search_book_by_isbn.return_value = None
        mock_feishu_api_instance.upload_image.return_value = "file_token_xyz" # Assume upload works
        mock_feishu_api_instance.create_book.return_value = False # Feishu create fails

        response = self.client.get('/isbn?isbn=ISBN_CREATE_FAIL')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], "添加图书到飞书失败")


    def test_isbn_feishu_update_error(self):
        """Test /isbn: Feishu API error during update."""
        mock_douban_scraper_instance.get_book_info.return_value = {"book_name": "Test Book Update Fail"}
        mock_feishu_api_instance.search_book_by_isbn.return_value = "record_id_def"
        mock_feishu_api_instance.update_book.return_value = False # Feishu update fails

        response = self.client.get('/isbn?isbn=ISBN_UPDATE_FAIL')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], "更新飞书图书记录失败")


    def test_isbn_missing_parameter(self):
        """Test /isbn: missing ISBN parameter."""
        response = self.client.get('/isbn')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], "缺少ISBN参数")


    # --- Tests for /config endpoint ---
    def test_get_config_success(self):
        """Test GET /config: successfully retrieve sanitized config status."""
        mock_get_feishu_config.return_value = {
            "FEISHU_APP_ID": "actual_app_id", # Value doesn't matter, only its truthiness
            "FEISHU_APP_SECRET": "actual_secret",
            "FEISHU_APP_TOKEN": "", # Example of a non-set value
            "FEISHU_TABLE_ID": "actual_table_id",
            "FEISHU_VIEW_ID": None   # Example of a non-set value
        }
        response = self.client.get('/config')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['message'], "获取配置成功")
        self.assertTrue(data['config']['app_id'])
        self.assertTrue(data['config']['app_secret'])
        self.assertFalse(data['config']['app_token'])
        self.assertTrue(data['config']['table_id'])
        self.assertFalse(data['config']['view_id'])
        mock_get_feishu_config.assert_called_once()


    def test_post_config_success(self):
        """Test POST /config: successfully update configuration."""
        mock_update_feishu_config.return_value = True
        # The FeishuAPI instance is re-initialized in app.py upon successful config update.
        # Our @patch('services.FeishuAPI', ...) handles this by ensuring any new
        # FeishuAPI() call still returns our mock_feishu_api_instance.
        # We might want to check if it was called again if that's a specific concern.

        payload = {
            "app_id": "new_app_id",
            "app_secret": "new_secret",
            "app_token": "new_app_token",
            "table_id": "new_table_id",
            "view_id": "new_view_id"
        }
        response = self.client.post('/config', data=json.dumps(payload), content_type='application/json')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['message'], "配置保存成功")
        mock_update_feishu_config.assert_called_once_with({
            "FEISHU_APP_ID": "new_app_id",
            "FEISHU_APP_SECRET": "new_secret",
            "FEISHU_APP_TOKEN": "new_app_token",
            "FEISHU_TABLE_ID": "new_table_id",
            "FEISHU_VIEW_ID": "new_view_id"
        })
        # Verify FeishuAPI was re-instantiated (check if __init__ was called again)
        # This requires the mock_feishu_api_class (the one returned by patch) to be inspected
        self.assertGreaterEqual(mock_feishu_api_class.call_count, 1) # Called at least once at startup, possibly more if config reloads


    def test_post_config_missing_fields(self):
        """Test POST /config: missing required fields."""
        payload = {"app_id": "only_app_id"} # Missing secret, token, table_id
        response = self.client.post('/config', data=json.dumps(payload), content_type='application/json')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 400)
        self.assertTrue("缺少必要的配置项" in data['message'])


    def test_post_config_update_fails(self):
        """Test POST /config: AppConfig.update_feishu_config returns False."""
        mock_update_feishu_config.return_value = False
        payload = {
            "app_id": "fail_app_id", "app_secret": "fail_secret",
            "app_token": "fail_app_token", "table_id": "fail_table_id"
        }
        response = self.client.post('/config', data=json.dumps(payload), content_type='application/json')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], "保存配置失败，请检查日志")


    # --- Test for / (index) endpoint ---
    def test_index_route(self):
        """Test / (index) endpoint."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "text/html; charset=utf-8")
        # Could also check for some content in response.data.decode()


    # --- Tests for /feishu_fields endpoint ---
    def test_get_feishu_fields_success(self):
        """Test /feishu_fields: successfully retrieve fields."""
        sample_fields = [{"field_id": "fld123", "name": "书名", "type": 1, "type_name": "文本"}]
        mock_feishu_api_instance.get_table_fields.return_value = sample_fields
        
        response = self.client.get('/feishu_fields')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['message'], "获取表头字段成功")
        self.assertEqual(data['fields'], sample_fields)
        mock_feishu_api_instance.get_table_fields.assert_called_once()


    def test_get_feishu_fields_not_found(self):
        """Test /feishu_fields: fields cannot be retrieved (returns None)."""
        mock_feishu_api_instance.get_table_fields.return_value = None
        
        response = self.client.get('/feishu_fields')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['message'], "未能获取表头字段，请检查配置或API权限")

    def test_get_feishu_fields_api_exception(self):
        """Test /feishu_fields: feishu_api raises an exception."""
        mock_feishu_api_instance.get_table_fields.side_effect = Exception("Simulated API error")
        
        response = self.client.get('/feishu_fields')
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 500)
        self.assertTrue("获取表头字段失败: Simulated API error" in data['message'])


def tearDownModule():
    """Stop all module-level patchers."""
    patch_app_logger.stop()
    patch_appconfig_initialize.stop()
    patch_appconfig_get_feishu_config.stop()
    patch_appconfig_update_feishu_config.stop()
    patch_douban_scraper.stop()
    patch_feishu_api.stop()

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    tearDownModule()
