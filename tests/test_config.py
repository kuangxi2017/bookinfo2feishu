# -*- coding: UTF-8 -*-
import unittest
import os
import json
from unittest.mock import patch, mock_open, MagicMock

# Ensure the logger is mocked early to prevent it from trying to create log files
# during test discovery or initial import, especially if AppConfig.initialize() is called by modules.
# We need to mock the logger instance that is actually used by the config module.
# Assuming 'utils.logger.logger' is the global logger instance.
mock_logger = MagicMock()
patcher = patch('utils.logger.logger', mock_logger)
patcher.start() # Start patch before any imports that might use the logger

# It's important to stop the patcher after tests, though for a script run once it might not matter.
# For a test suite, use addCleanup or setUpModule/tearDownModule.
# For now, we'll just ensure it's started. If this were a test class, patcher.stop() would go in tearDown.

from config import FeishuConfig, AppConfig

# Stop patcher after all tests if running as a script, or manage in test class/suite
# For now, this is a simplified approach. A proper test suite would manage this better.
# patcher.stop() # This would ideally be in a tearDownClass or similar


class TestFeishuConfig(unittest.TestCase):

    def setUp(self):
        """Setup for each test. Ensures a clean config state."""
        # Reset FeishuConfig._config to force reload or use defaults
        FeishuConfig._config = None
        # Define a test-specific config file path
        self.test_config_dir = os.path.join(os.path.dirname(__file__), 'test_config_data')
        self.test_config_file = os.path.join(self.test_config_dir, 'test_feishu_config.json')
        FeishuConfig.CONFIG_FILE = self.test_config_file

        # Ensure test config directory exists
        os.makedirs(self.test_config_dir, exist_ok=True)
        
        # Clean up any existing test config file before each test
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        
        # Reset logger mocks for each test if needed, though global mock is often fine
        mock_logger.reset_mock()

    def tearDown(self):
        """Clean up after each test."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists(self.test_config_dir):
            # Only remove if empty, or use shutil.rmtree if sure
            if not os.listdir(self.test_config_dir):
                 os.rmdir(self.test_config_dir)
            elif self.test_config_dir.endswith('test_config_data'): # Safety check
                import shutil
                shutil.rmtree(self.test_config_dir)


    def test_load_default_config_if_file_not_exists(self):
        """Test that default configuration is loaded if config file doesn't exist."""
        self.assertIsNone(FeishuConfig._config, "Config should be None initially")
        
        # Mock os.path.exists to simulate config file not existing for the load_config call
        # This is an alternative to ensuring the file is deleted if FeishuConfig.load_config() is called implicitly
        with patch('os.path.exists') as mock_path_exists:
            mock_path_exists.return_value = False # Simulate config file does not exist
            
            # We also need to mock save_config because load_config calls it when creating a default
            with patch.object(FeishuConfig, 'save_config', return_value=True) as mock_save:
                FeishuConfig.load_config() # Explicitly call load
                mock_save.assert_called_once() # Ensure it tried to save the default

        self.assertIsNotNone(FeishuConfig._config, "Config should be loaded")
        self.assertEqual(FeishuConfig._config.get("FEISHU_APP_ID"), FeishuConfig._DEFAULT_CONFIG["FEISHU_APP_ID"])
        self.assertEqual(FeishuConfig._config.get("FEISHU_APP_SECRET"), FeishuConfig._DEFAULT_CONFIG["FEISHU_APP_SECRET"])
        mock_logger.info.assert_any_call("已创建默认飞书配置文件")


    def test_update_config_and_save(self):
        """Test updating and saving configuration values."""
        initial_app_id = FeishuConfig._DEFAULT_CONFIG["FEISHU_APP_ID"]
        new_app_id = "test_app_id_123"
        new_secret = "test_secret_456"

        # Ensure config is loaded (it will load defaults and try to save)
        with patch.object(FeishuConfig, 'save_config', return_value=True) as mock_initial_save:
            FeishuConfig.load_config() 
        
        self.assertEqual(FeishuConfig.get_config_value("FEISHU_APP_ID"), initial_app_id)

        update_data = {
            "FEISHU_APP_ID": new_app_id,
            "FEISHU_APP_SECRET": new_secret,
            "NON_EXISTENT_KEY": "should_not_be_added"
        }

        # Mock json.dump for saving
        # When FeishuConfig.update_config calls save_config, it will write to the test file.
        # We can let it write, or mock the save_config method.
        # Let's mock save_config to check it's called.
        with patch.object(FeishuConfig, 'save_config', return_value=True) as mock_save:
            success = FeishuConfig.update_config(update_data)
            self.assertTrue(success)
            mock_save.assert_called_once()

        self.assertEqual(FeishuConfig.get_config_value("FEISHU_APP_ID"), new_app_id)
        self.assertEqual(FeishuConfig.get_config_value("FEISHU_APP_SECRET"), new_secret)
        self.assertIsNone(FeishuConfig.get_config_value("NON_EXISTENT_KEY"))


    def test_save_and_reload_config(self):
        """Test saving configuration to a file and reloading it."""
        test_data = {
            "FEISHU_APP_ID": "reloaded_app_id",
            "FEISHU_APP_SECRET": "reloaded_secret",
            "FEISHU_APP_TOKEN": "reloaded_app_token",
            "FEISHU_TABLE_ID": "reloaded_table_id",
            "FEISHU_VIEW_ID": "reloaded_view_id"
        }
        
        # 1. Set and save the config
        FeishuConfig._config = test_data.copy() # Directly set for saving
        self.assertTrue(FeishuConfig.save_config(), "Save should be successful")
        mock_logger.info.assert_any_call("已保存飞书配置到文件")

        # Ensure file was actually written (optional check)
        self.assertTrue(os.path.exists(self.test_config_file))
        with open(self.test_config_file, 'r', encoding='utf-8') as f:
            written_data = json.load(f)
        self.assertEqual(written_data, test_data)

        # 2. Reset and reload
        FeishuConfig._config = None 
        FeishuConfig.load_config() # This will load from self.test_config_file

        self.assertIsNotNone(FeishuConfig._config)
        self.assertEqual(FeishuConfig.get_config_value("FEISHU_APP_ID"), test_data["FEISHU_APP_ID"])
        self.assertEqual(FeishuConfig.get_config_value("FEISHU_APP_SECRET"), test_data["FEISHU_APP_SECRET"])
        mock_logger.info.assert_any_call("已从文件加载飞书配置")


    def test_get_config_value(self):
        """Test fetching specific configuration values."""
        # Load defaults
        with patch.object(FeishuConfig, 'save_config', return_value=True): # Mock save during default load
            FeishuConfig.load_config()

        self.assertEqual(FeishuConfig.get_config_value("FEISHU_APP_ID"), FeishuConfig._DEFAULT_CONFIG["FEISHU_APP_ID"])
        self.assertIsNone(FeishuConfig.get_config_value("NON_EXISTENT_KEY_TO_GET"))
        
        # Test after setting a value
        FeishuConfig._config["FEISHU_APP_ID"] = "specific_test_id"
        self.assertEqual(FeishuConfig.get_config_value("FEISHU_APP_ID"), "specific_test_id")

    def test_load_config_exception_handling(self):
        """Test that load_config handles exceptions and loads defaults."""
        # Simulate an error during json.load
        with patch('builtins.open', mock_open(read_data="invalid json data")) as mock_file_open:
            # And ensure os.path.exists returns True for this path
            with patch('os.path.exists', return_value=True):
                # And mock save_config because it will try to save defaults upon failure
                with patch.object(FeishuConfig, 'save_config', return_value=True) as mock_save_default:
                    FeishuConfig.load_config()
                    mock_file_open.side_effect = json.JSONDecodeError("Simulated error", "doc", 0)
                    FeishuConfig.load_config() # Call again to trigger exception path

        mock_logger.error.assert_any_call(unittest.mock.ANY) # Check that an error was logged
        self.assertIsNotNone(FeishuConfig._config, "Config should still be initialized to defaults after error.")
        self.assertEqual(FeishuConfig._config.get("FEISHU_APP_ID"), FeishuConfig._DEFAULT_CONFIG["FEISHU_APP_ID"])


    def test_app_config_initialization_calls_feishu_load(self):
        """Test that AppConfig.initialize calls FeishuConfig.load_config."""
        # We need to ensure FeishuConfig is in a state where load_config can be tracked
        FeishuConfig._config = None
        with patch.object(FeishuConfig, 'load_config') as mock_feishu_load:
            with patch.object(AppConfig, 'ensure_directories') as mock_ensure_dirs: # Mock dir creation
                AppConfig.initialize()
                mock_feishu_load.assert_called_once()
                mock_ensure_dirs.assert_called_once()

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    patcher.stop() # Stop the global logger patcher
